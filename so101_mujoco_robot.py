"""LeRobot robot plugin: SO-ARM101 in MuJoCo.

Implements the standard :class:`~lerobot.robots.robot.Robot` interface on top of
a MuJoCo simulation of the SO-ARM101 follower, running on the vendored
mujoco_menagerie SO-ARM100 model (real CAD gripper with working collision, so
objects can be grasped). It can be used with ``lerobot-teleoperate`` /
``lerobot-record`` through a launcher that imports this module (the config is
registered under the ``so101_mujoco`` robot type).

Unit conventions follow the SO-101 hardware calibration in LeRobot:
body joints are expressed in [-100, 100] linearly across their whole joint range
(0 = middle of the range, matching the "new calibration" convention), and the
gripper in [0, 100] (0 = closed). The dataset written from this robot is
therefore directly comparable with real SO-101 recordings.

The simulation runs on its own thread, paced to real time, so the robot behaves
like hardware from the caller's point of view: ``send_action`` sets the target,
``get_observation`` reads the latest state, and the arm keeps moving in between.
With ``onscreen=True`` (default) an interactive MuJoCo viewer window is opened.
"""

from __future__ import annotations

import logging
import pathlib
import sys
import threading
import time
from dataclasses import dataclass

import mujoco
import numpy as np

from lerobot.robots.config import RobotConfig
from lerobot.robots.robot import Robot
from lerobot.robots.utils import ensure_safe_goal_position
from lerobot.utils.decorators import check_if_already_connected, check_if_not_connected

from so101_assets import (
    MENAGERIE_CAMERA_FOVY,
    MENAGERIE_CAMERA_POS,
    MENAGERIE_CAMERA_RPY_DEG,
    MENAGERIE_MOUNT_PARENT,
    MENAGERIE_MOUNT_POS,
    MENAGERIE_MOUNT_RPY_DEG,
    add_workspace,
    harden_mesh_contacts,
    menagerie_scene,
    menagerie_spec,
)

logger = logging.getLogger(__name__)

# Joint order used by the SO-101 hardware and by the official MJCF.
JOINT_NAMES = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")
GRIPPER = "gripper"

# Mapping from the LeRobot joint names to the menagerie model's joints and the
# sign of the unit direction (determined empirically 2026-10-16 by comparing
# world-space tool motion against the previous tutorial model, whose directions
# had been verified against the real arm; wrist_roll's sign is provisional --
# confirm in the first live leader-arm session, flip if the sim rolls the wrong
# way). The gripper's low range end is 'closed' on both conventions.
MODEL_JOINT: dict[str, tuple[str, int]] = {
    "shoulder_pan": ("Rotation", -1),
    "shoulder_lift": ("Pitch", +1),
    "elbow_flex": ("Elbow", +1),
    "wrist_flex": ("Wrist_Pitch", +1),
    "wrist_roll": ("Wrist_Roll", +1),
    "gripper": ("Jaw", +1),
}

# Viewer camera tuned for the new-calibration rest pose (see layer-1 report).
VIEWER_LOOKAT = (0.05, -0.01, 0.13)
VIEWER_DISTANCE = 0.68
VIEWER_AZIMUTH = 160.0
VIEWER_ELEVATION = -18.0

VIEWER_TITLE = "SO-ARM101 MuJoCo teleop"
VIEWER_KEYS = "w/s lift  a/z pan  e/d elbow  t/g wrist_flex  y/h wrist_roll  u/j gripper"


class _SimCameraInfo:
    """Attribute holder exposed via ``Robot.cameras`` so the record pipeline
    sees one camera; the frames themselves are rendered on the simulation
    thread and read in ``get_observation``."""

    def __init__(self, width: int, height: int, fps: int):
        self.width = width
        self.height = height
        self.fps = fps


_RIG_MODULE = None


def _camera_rig():
    """The camera-rig assembly module (bracket mount pose, camera pose, camera
    element) built and tuned with the tools under ``assets/camera/``. Imported
    lazily so plain (camera-less) robot use doesn't touch it."""
    global _RIG_MODULE
    if _RIG_MODULE is None:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "assets" / "camera"))
        import preview_mount as _pm  # noqa: PLC0415

        _RIG_MODULE = _pm
    return _RIG_MODULE


def _add_camera_module(spec: mujoco.MjSpec) -> None:
    """Attach the bracket + camera module (visuals and the ``sim_cam`` camera
    element) exactly as shown by the camera-rig tools."""
    rig = _camera_rig()
    stl = rig.ensure_metric_stl()
    mesh = spec.add_mesh()
    mesh.name = "cam_bracket"
    mesh.file = stl.as_posix()
    bracket = spec.body(MENAGERIE_MOUNT_PARENT).add_body(name="cam_bracket")
    bracket.pos = MENAGERIE_MOUNT_POS
    bracket.quat = rig.quat_from_rpy_deg(MENAGERIE_MOUNT_RPY_DEG)
    bg = bracket.add_geom(name="cam_bracket")
    bg.type = mujoco.mjtGeom.mjGEOM_MESH
    bg.meshname = "cam_bracket"
    bg.rgba = [0.93, 0.91, 0.87, 1]

    cam = bracket.add_body(name="camera")
    cam.pos = MENAGERIE_CAMERA_POS
    cam.quat = rig.quat_from_rpy_deg(MENAGERIE_CAMERA_RPY_DEG)
    pcb = cam.add_geom(name="cam_pcb")
    pcb.type = mujoco.mjtGeom.mjGEOM_BOX
    pcb.size = [0.0125, 0.015, 0.000775]
    pcb.pos = [0.0, 0.0, 0.000775]
    pcb.rgba = [0.12, 0.12, 0.14, 1]
    lens = cam.add_geom(name="cam_lens")
    lens.type = mujoco.mjtGeom.mjGEOM_CYLINDER
    lens.size = [0.0032, 0.001825, 0.0]
    lens.pos = [0.0, 0.0025, 0.003375]
    lens.rgba = [0.06, 0.06, 0.07, 1]
    view = cam.add_camera(name="sim_cam")
    view.pos = [0.0, 0.0025, 0.0052]
    # MuJoCo cameras look along their local -Z; rotate the element 180 deg about
    # Y so the recorded view actually comes out of the lens (+z of this body).
    view.quat = rig.quat_from_rpy_deg([0.0, 180.0, 0.0])
    view.fovy = MENAGERIE_CAMERA_FOVY


def _build_scene(model_path: str, config: SO101MujocoRobotConfig) -> mujoco.MjModel:
    """Menagerie SO-ARM100 scene + the task workspace (mat, cubes, container,
    ``top_cam``) + the wrist camera module (the bracket is physically part of
    the arm, so it is always present; ``image_camera`` only controls whether
    frames are rendered from it). Mesh contacts are hardened after compile
    (see ``harden_mesh_contacts``)."""
    spec = menagerie_spec()
    add_workspace(spec)
    _add_camera_module(spec)
    model = spec.compile()
    harden_mesh_contacts(model)
    return model


@RobotConfig.register_subclass("so101_mujoco")
@dataclass
class SO101MujocoRobotConfig(RobotConfig):
    """Config for the SO-ARM101 MuJoCo simulation robot.

    Args:
        model: Path to the MJCF scene. Defaults to the official new-calibration
            scene extracted from the tutorial zip (see ``so101_assets.py``).
        onscreen: Open the interactive viewer window (press Esc inside it to close;
            the simulation keeps running headless afterwards).
        max_relative_target: Cap (in normalized units) on how far a single
            ``send_action`` may move each joint away from its present position.
            ``None`` disables the cap; the keyboard teleoperator is already
            rate-limited, so this is a second safety layer.
        sync_fps: How often the simulation thread advances/renders (viewer refresh).
        image_camera: Name of an MJCF camera in the scene (e.g. "sim_cam", the
            wrist camera on the bracket) to publish as an image observation under
            the key ``wrist``. ``None`` disables image observations.
        top_camera: Name of a second MJCF camera (e.g. "top_cam", the fixed
            overhead view of the workspace) published under the key ``top``.
        image_width / image_height / image_fps: Offscreen render size and rate of
            those cameras (rendered on the simulation thread).
        preview_cameras: With ``onscreen``, open one live preview window per
            image camera (fixed to that camera), so the camera streams can be
            watched while teleoperating/recording.
        preview_fps: Refresh rate of those preview windows. They are status
            displays, not the main view, so they default well below
            ``sync_fps``: three full-speed GL renders per tick are a real load
            on integrated graphics while episode videos encode in the background.
    """

    model: str = ""
    onscreen: bool = True
    max_relative_target: float | None = None
    sync_fps: int = 50
    image_camera: str | None = None
    top_camera: str | None = None
    image_width: int = 640
    image_height: int = 480
    image_fps: int = 30
    preview_cameras: bool = True
    preview_fps: int = 15


class SO101MujocoRobot(Robot):
    config_class = SO101MujocoRobotConfig
    name = "so101_mujoco"

    def __init__(self, config: SO101MujocoRobotConfig):
        super().__init__(config)
        self.config = config
        # The record path reads `len(robot.cameras)` unconditionally. When image
        # observations are enabled we expose one camera entry (an attribute holder;
        # frames are produced on the sim thread and read in get_observation).
        self.cameras: dict = {}
        if config.image_camera:
            self.cameras["wrist"] = _SimCameraInfo(config.image_width, config.image_height, config.image_fps)
        if config.top_camera:
            self.cameras["top"] = _SimCameraInfo(config.image_width, config.image_height, config.image_fps)

        self.model: mujoco.MjModel | None = None
        self.data: mujoco.MjData | None = None
        self._viewer = None
        self._camera_viewers: list = []
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._thread_error: BaseException | None = None
        self._latest_images: dict[str, np.ndarray] = {}

        # name -> (qpos address, unit conversion), filled in connect().
        self._qposadr: dict[str, int] = {}
        self._unit_range: dict[str, tuple[float, float]] = {}
        self._sign: dict[str, int] = {}
        self._ctrl_joint: np.ndarray | None = None  # actuator index -> qpos address
        self._target_qpos: np.ndarray | None = None

        # Scene objects: free joints (the task cubes) and their spawn poses,
        # used by reset_scene_objects() during the record pipeline's reset phase.
        self._free_joint_qpos0: dict[int, np.ndarray] = {}
        self._reset_objects_requested = False

    # ------------------------------------------------------------------ units
    def _to_units(self, name: str, q: float) -> float:
        lo, hi = self._unit_range[name]
        if name == GRIPPER:
            return 100.0 * (q - lo) / (hi - lo)
        mid = 0.5 * (lo + hi)
        return self._sign[name] * 200.0 * (q - mid) / (hi - lo)

    def _to_rad(self, name: str, value: float) -> float:
        lo, hi = self._unit_range[name]
        if name == GRIPPER:
            return lo + (hi - lo) * value / 100.0
        mid = 0.5 * (lo + hi)
        return mid + self._sign[name] * (hi - lo) * value / 200.0

    # ----------------------------------------------------------------- basics
    @property
    def is_connected(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def is_calibrated(self) -> bool:
        # The MJCF defines the geometry and limits; there is nothing to calibrate.
        return True

    def calibrate(self) -> None:
        pass

    def configure(self) -> None:
        pass

    # ---------------------------------------------------------- scene objects
    def reset_scene_objects(self) -> None:
        """Put the scene's free bodies (the task cubes) back at their spawn poses.

        Called by the recording launcher when the record loop enters its
        unrecorded "reset the environment" phase between episodes, so every
        episode starts from the same cube arrangement. The teleport itself runs
        on the simulation thread (next tick after this returns), which keeps
        mjData access single-threaded. No-op when not connected.
        """
        if self.data is not None:
            self._reset_objects_requested = True

    def _perform_scene_reset(self) -> None:
        """Runs on the sim thread: teleport free bodies to spawn, zero speeds."""
        for jid, qpos0 in self._free_joint_qpos0.items():
            adr = int(self.model.jnt_qposadr[jid])
            self.data.qpos[adr : adr + 7] = qpos0
            vadr = int(self.model.jnt_dofadr[jid])
            self.data.qvel[vadr : vadr + 6] = 0.0
        mujoco.mj_forward(self.model, self.data)

    @property
    def observation_features(self) -> dict:
        features: dict = {f"{name}.pos": float for name in JOINT_NAMES}
        for key, cam_name in (("wrist", self.config.image_camera), ("top", self.config.top_camera)):
            if cam_name:
                features[key] = (self.config.image_height, self.config.image_width, 3)
        return features

    @property
    def action_features(self) -> dict:
        return {f"{name}.pos": float for name in JOINT_NAMES}

    # ---------------------------------------------------------------- connect
    @check_if_already_connected
    def connect(self, calibrate: bool = True) -> None:
        model_path = self.config.model or str(menagerie_scene())
        self.model = _build_scene(model_path, self.config)
        self.data = mujoco.MjData(self.model)

        # Free bodies (the task cubes): their spawn poses live in model.qpos0.
        self._free_joint_qpos0 = {
            j: self.model.qpos0[self.model.jnt_qposadr[j] : self.model.jnt_qposadr[j] + 7].copy()
            for j in range(self.model.njnt)
            if self.model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE
        }

        for cam_name in (self.config.image_camera, self.config.top_camera):
            if not cam_name:
                continue
            if mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_CAMERA, cam_name) < 0:
                raise ValueError(f"Camera '{cam_name}' not found in model {model_path}")
        if self.config.image_camera or self.config.top_camera:
            self.model.vis.global_.offwidth = max(self.model.vis.global_.offwidth, self.config.image_width)
            self.model.vis.global_.offheight = max(self.model.vis.global_.offheight, self.config.image_height)

        for name in JOINT_NAMES:
            mj_name, sign = MODEL_JOINT[name]
            jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, mj_name)
            if jid < 0:
                raise ValueError(f"Model joint '{mj_name}' (for '{name}') not found in {model_path}")
            self._qposadr[name] = int(self.model.jnt_qposadr[jid])
            lo, hi = (float(v) for v in self.model.jnt_range[jid])
            self._unit_range[name] = (lo, hi)
            self._sign[name] = sign

        # actuator index -> qpos address (position actuators on the arm joints)
        adr_by_model_joint = {mj: self._qposadr[n] for n, (mj, _s) in MODEL_JOINT.items()}
        self._ctrl_joint = np.array(
            [adr_by_model_joint[mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_JOINT, int(self.model.actuator_trnid[a, 0]))]
             for a in range(self.model.nu)]
        )

        # Start at the middle of every joint range (= teleop start pose = 0 units).
        for name in JOINT_NAMES:
            lo, hi = self._unit_range[name]
            self.data.qpos[self._qposadr[name]] = 0.5 * (lo + hi)
        mujoco.mj_forward(self.model, self.data)
        self._target_qpos = self.data.qpos.copy()

        self._stop.clear()
        self._ready.clear()
        self._thread_error = None
        self._thread = threading.Thread(target=self._run_sim, name="so101-mujoco-sim", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=15.0):
            raise RuntimeError("SO-ARM101 MuJoCo sim thread failed to start within 15 s")
        if self._thread_error is not None:
            error, self._thread_error = self._thread_error, None
            self._thread = None
            raise RuntimeError(f"SO-ARM101 MuJoCo sim failed to start: {error!r}") from error
        expected_cams = set(self.cameras)
        if expected_cams:
            # The record loop reads the first observation immediately after
            # connecting; wait until the sim thread has produced a frame for every
            # configured camera (otherwise build_dataset_frame raises).
            deadline = time.perf_counter() + 5.0
            while not expected_cams.issubset(self._latest_images) and time.perf_counter() < deadline:
                if self._thread is None or not self._thread.is_alive() or self._thread_error is not None:
                    break
                time.sleep(0.01)
            if not expected_cams.issubset(self._latest_images):
                missing = sorted(expected_cams - set(self._latest_images))
                raise RuntimeError(f"SO-ARM101 MuJoCo sim produced no frame for {missing} within 5 s")
        logger.info("SO-ARM101 MuJoCo robot connected (model: %s, onscreen: %s)", model_path, self.config.onscreen)

    # ------------------------------------------------------------- sim thread
    def _run_sim(self) -> None:
        image_renderer = None
        try:
            model, data = self.model, self.data
            if self.config.onscreen:
                # `from mujoco import viewer` (rather than `import mujoco.viewer`)
                # keeps `mujoco` resolved from the module scope inside this function.
                from mujoco import viewer as mujoco_viewer

                self._viewer = mujoco_viewer.launch_passive(model, data)
                cam = self._viewer.cam
                cam.lookat[:] = VIEWER_LOOKAT
                cam.distance = VIEWER_DISTANCE
                cam.azimuth = VIEWER_AZIMUTH
                cam.elevation = VIEWER_ELEVATION
                if hasattr(self._viewer, "set_texts"):
                    # Overlay texts are (font, grid position, left column, right column).
                    self._viewer.set_texts([
                        (mujoco.mjtFontScale.mjFONTSCALE_150, mujoco.mjtGridPos.mjGRID_TOPLEFT, VIEWER_TITLE, None),
                        (mujoco.mjtFontScale.mjFONTSCALE_100, mujoco.mjtGridPos.mjGRID_BOTTOMLEFT, VIEWER_KEYS, None),
                    ])

                # Live preview window per image camera, fixed to that camera, so
                # the operator can see each stream's state while recording.
                if self.config.preview_cameras:
                    for key, cam_name in (("wrist", self.config.image_camera), ("top", self.config.top_camera)):
                        if not cam_name:
                            continue
                        cam_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, cam_name)
                        if cam_id < 0:
                            continue
                        preview = mujoco_viewer.launch_passive(model, data)
                        preview.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
                        preview.cam.fixedcamid = cam_id
                        if hasattr(preview, "set_texts"):
                            preview.set_texts([
                                (mujoco.mjtFontScale.mjFONTSCALE_100, mujoco.mjtGridPos.mjGRID_TOPLEFT,
                                 f"{key} camera ({cam_name}) - live", None),
                            ])
                        self._camera_viewers.append(preview)

            dt = model.opt.timestep
            substeps = max(1, round(1.0 / (self.config.sync_fps * dt)))
            tick_wall = substeps * dt

            # Offscreen camera renderer: created and used on THIS thread (GL
            # contexts are thread-bound), like the viewer above.
            image_renderer = None
            image_cams: list[tuple[str, int]] = []
            image_ticks = 1
            tick_count = 0
            if self.cameras:
                image_renderer = mujoco.Renderer(model, self.config.image_height, self.config.image_width)
                for key, cam_name in (("wrist", self.config.image_camera), ("top", self.config.top_camera)):
                    if cam_name:
                        cam_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, cam_name)
                        image_cams.append((key, cam_id))
                image_ticks = max(1, round(self.config.sync_fps / max(1, self.config.image_fps)))

            # Preview windows refresh well below sync_fps (status displays, not the
            # main view); at 50 Hz they cost two extra GL renders per tick.
            preview_ticks = max(1, round(self.config.sync_fps / max(1, self.config.preview_fps)))

            self._ready.set()

            wall_start = time.perf_counter()
            sim_time = 0.0
            while not self._stop.is_set():
                if self._reset_objects_requested:
                    self._reset_objects_requested = False
                    self._perform_scene_reset()
                with self._lock:
                    target = self._target_qpos.copy()
                for _ in range(substeps):
                    data.ctrl[:] = target[self._ctrl_joint]
                    mujoco.mj_step(model, data)
                if image_renderer is not None and tick_count % image_ticks == 0:
                    frames = {}
                    for key, cam_id in image_cams:
                        image_renderer.update_scene(data, camera=cam_id)
                        frames[key] = image_renderer.render().copy()
                    with self._lock:
                        self._latest_images.update(frames)
                tick_count += 1
                sim_time += tick_wall
                if self._viewer is not None:
                    if self._viewer.is_running():
                        self._viewer.sync()
                    else:
                        self._viewer = None  # window closed: keep simulating headless
                if self._camera_viewers and tick_count % preview_ticks == 0:
                    alive = []
                    for preview in self._camera_viewers:
                        if preview.is_running():
                            preview.sync()
                            alive.append(preview)
                    self._camera_viewers = alive
                sleep = sim_time - (time.perf_counter() - wall_start)
                if sleep > 0:
                    time.sleep(sleep)
                elif sleep < -0.25:
                    # Fell too far behind (e.g. debugger pause): re-anchor instead of bursting.
                    wall_start = time.perf_counter() - sim_time
        except BaseException as exc:  # noqa: BLE001 -- forwarded to connect()/disconnect()
            self._thread_error = exc
            logger.exception("SO-ARM101 MuJoCo sim thread crashed")
        finally:
            if image_renderer is not None:
                try:
                    image_renderer.close()
                except Exception:  # noqa: BLE001
                    pass
            if self._viewer is not None:
                try:
                    self._viewer.close()
                except Exception:  # noqa: BLE001
                    pass
                self._viewer = None
            for preview in self._camera_viewers:
                try:
                    preview.close()
                except Exception:  # noqa: BLE001
                    pass
            self._camera_viewers = []
            self._ready.set()

    # -------------------------------------------------------------------- I/O
    @check_if_not_connected
    def get_observation(self) -> dict:
        with self._lock:
            qpos = self.data.qpos.copy()
            images = {key: img.copy() for key, img in self._latest_images.items()}
        obs = {f"{name}.pos": self._to_units(name, float(qpos[self._qposadr[name]])) for name in JOINT_NAMES}
        obs.update(images)
        return obs

    @check_if_not_connected
    def send_action(self, action: dict) -> dict:
        goal_units = {key.removesuffix(".pos"): float(val) for key, val in action.items() if key.endswith(".pos")}

        if self.config.max_relative_target is not None:
            present = self.get_observation()
            present_units = {key.removesuffix(".pos"): val for key, val in present.items()}
            goal_units = ensure_safe_goal_position(
                {name: (val, present_units[name]) for name, val in goal_units.items()},
                self.config.max_relative_target,
            )

        with self._lock:
            for name, value in goal_units.items():
                if name not in self._qposadr:
                    continue
                lo_u, hi_u = (0.0, 100.0) if name == GRIPPER else (-100.0, 100.0)
                value = min(max(value, lo_u), hi_u)
                goal_units[name] = value
                self._target_qpos[self._qposadr[name]] = self._to_rad(name, value)

        return {f"{name}.pos": value for name, value in goal_units.items()}

    @check_if_not_connected
    def disconnect(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("SO-ARM101 MuJoCo sim thread did not stop within 5 s")
            self._thread = None
        self.model = None
        self.data = None
        logger.info("SO-ARM101 MuJoCo robot disconnected.")
