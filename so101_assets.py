"""Locate the SO-ARM101 MuJoCo model used by the sim robot/teleop plugins.

The canonical copy of the model ships inside the tutorial zip
``Tutorial/lerobot tutorials/en/images/SO-ARM101_ROS2.zip`` (official SO-ARM100
``Simulation/SO101`` subtree: ``so101_new_calib.xml`` + ``joints_properties.xml``
+ ``assets/*.stl``). On first use we extract that subtree into a local cache and
write a small scene wrapper (floor, light, skybox) next to it, mirroring the
official ``scene.xml`` -- which is *not* part of the zip, so it is generated here
instead of downloaded.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import mujoco

REPO_ROOT = Path(__file__).resolve().parents[2]
ZIP_PATH = REPO_ROOT / "Tutorial" / "lerobot tutorials" / "en" / "images" / "SO-ARM101_ROS2.zip"
SUBTREE_PREFIX = "SO-ARM101_ROS2/Simulation/SO101/"
CACHE_DIR = Path.home() / ".cache" / "so101_mujoco"
MODEL_DIR = CACHE_DIR / "Simulation" / "SO101"
SCENE_PATH = MODEL_DIR / "scene_local.xml"
_MARKER = CACHE_DIR / ".zip_marker"

# The robot plugin now runs on the vendored mujoco_menagerie SO-ARM100 model
# (Apache-2.0, vendored under assets/menagerie_so_arm100 with its LICENSE):
# unlike the tutorial-zip MJCF, its gripper has real collision geometry, so
# objects can actually be grasped. The tutorial model above is kept for the
# legacy tools (load_and_drive etc.) and comparison renders.
MENAGERIE_DIR = Path(__file__).resolve().parent / "assets" / "menagerie_so_arm100"

# The menagerie model's base frame faces -y at the homed pose; rotate the whole
# robot +90 deg about Z so its working front faces +x like the previous model,
# the real-arm mounting and all authored workspace positions (measured
# 2026-10-16: grip point at (0, -380) mm at the all-mid pose).
MENAGERIE_BASE_QUAT = [0.70710678, 0.0, 0.0, 0.70710678]  # yaw +90 deg


def menagerie_scene() -> Path:
    """Scene of the vendored menagerie SO-ARM100 model (used by the robot)."""
    return MENAGERIE_DIR / "scene.xml"


def menagerie_spec() -> "mujoco.MjSpec":
    """Spec of the menagerie scene with the base yawed to face +x (see below)."""
    spec = mujoco.MjSpec.from_file(str(menagerie_scene()))
    spec.body("Base").quat = MENAGERIE_BASE_QUAT
    return spec


# Camera bracket mount on the menagerie model: the bracket bolts to the side
# face of the gripper (jaw) servo housing, which in this model lives on the
# Fixed_Jaw body; pose expressed in the Fixed_Jaw body frame. Hand-tuned by
# the user with adjust_mount.py --model menagerie (2026-10-16) against the
# real-arm photos.
MENAGERIE_MOUNT_PARENT = "Fixed_Jaw"
MENAGERIE_MOUNT_POS = [0.0001, -0.0007, 0.0247]
MENAGERIE_MOUNT_RPY_DEG = [0.34, -27.20, 89.51]
MENAGERIE_CAMERA_POS = [0.0282, 0.0, 0.0579]  # bracket-frame; kept from the tuned rig
MENAGERIE_CAMERA_RPY_DEG = [-16.48, -88.06, 15.86]
MENAGERIE_CAMERA_FOVY = 46.6

_SCENE_XML = """\
<mujoco model="so101 scene">
  <include file="so101_new_calib.xml"/>
  <statistic center="0.1 -0.01 0.05" extent="0.5"/>
  <visual>
    <headlight diffuse="0.6 0.6 0.6" ambient="0.3 0.3 0.3" specular="0 0 0"/>
    <rgba haze="0.15 0.25 0.35 1"/>
    <global azimuth="160" elevation="-20"/>
  </visual>
  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="3072"/>
    <texture type="2d" name="groundplane" builtin="checker" mark="edge" rgb1="0.2 0.3 0.4"
             rgb2="0.1 0.2 0.3" markrgb="0.8 0.8 0.8" width="300" height="300"/>
    <material name="groundplane" texture="groundplane" texuniform="true" texrepeat="5 5" reflectance="0.2"/>
  </asset>
  <worldbody>
    <light pos="0 0 1.5" dir="0 0 -1" directional="true"/>
    <geom name="floor" type="plane" size="0 0 0.05" material="groundplane"/>
  </worldbody>
</mujoco>
"""


def _zip_stamp() -> str:
    stat = ZIP_PATH.stat()
    return f"{stat.st_size}-{int(stat.st_mtime)}"


def default_scene() -> Path:
    """Return the path of the SO-ARM101 scene, extracting it from the zip if needed."""
    if SCENE_PATH.is_file():
        if _MARKER.is_file() and _MARKER.read_text().strip() == _zip_stamp():
            return SCENE_PATH
        # The zip changed since the last extraction: refresh the model files.
        _extract()
        return SCENE_PATH
    _extract()
    return SCENE_PATH


def _extract() -> None:
    if not ZIP_PATH.is_file():
        raise FileNotFoundError(
            f"Tutorial zip with the SO-ARM101 model not found at {ZIP_PATH}. "
            "Run from a checkout that contains Tutorial/, or set --robot.model to an MJCF path."
        )
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH) as zf:
        for info in zf.infolist():
            if info.filename.startswith(SUBTREE_PREFIX) and not info.is_dir():
                relative = info.filename[len(SUBTREE_PREFIX):]
                target = MODEL_DIR / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as dst:
                    dst.write(src.read())
    SCENE_PATH.write_text(_SCENE_XML, encoding="utf-8")
    _MARKER.write_text(_zip_stamp(), encoding="utf-8")


# ---------------------------------------------------------------------------
# Task workspace (added to a scene spec by ``add_workspace``): a light mat marks
# the work area on the floor in front (+x) of the arm, three coloured cubes sit
# on it, an open-top container waits beyond them, and a fixed camera
# ("top_cam") looks straight down at the whole area.
# Metres, world frame (arm base = origin). Tweak the constants and rerun
# ``preview_workspace.py`` to re-render.

MAT_POS = [0.30, 0.0, 0.0035]  # 440 x 370 x 7 mm board; top face at z = 0.007
MAT_HALF = [0.22, 0.185, 0.0035]
MAT_TOP = MAT_POS[2] + MAT_HALF[2]
MAT_RGBA = [0.88, 0.87, 0.84, 1]

CUBE_HALF = 0.017  # 34 mm cubes
CUBE_DENSITY = 500  # ~16 g each
CUBE_Z = MAT_TOP + CUBE_HALF + 0.0002  # start just above the mat; settles on contact
CUBES = [  # (name, centre x, centre y, colour)
    ("red", 0.29, -0.080, [0.80, 0.15, 0.15, 1]),
    ("green", 0.29, 0.000, [0.20, 0.65, 0.25, 1]),
    ("yellow", 0.29, 0.080, [0.90, 0.72, 0.15, 1]),
]

BOX_POS = [0.19, 0.095, 0.0]  # container in the near-left corner of the mat (top view: bottom-left)
BOX_HALF = 0.058  # 116 mm outer
BOX_WALL = 0.0022  # 4.4 mm walls
BOX_WALL_H = 0.017  # 34 mm walls
BOX_RGBA = [0.25, 0.38, 0.62, 1]

TOP_CAM_POS = [0.30, 0.0, 0.62]
TOP_CAM_FOVY = 45.0
# Identity would look straight down with image-up = +y; yaw -90 turns image-up
# to +x (away from the arm) -- the natural way to read a top-down workspace.
TOP_CAM_QUAT = [0.70710678, 0.0, 0.0, -0.70710678]

# ---- gripper contact hardening (no geometry is changed) --------------------
# The vendor models' default contact parameters (solref timeconst 20 ms) are
# too soft for the thin mesh walls: fast or thin contacts pass through each
# other ("tunneling"). Hardening every mesh collision geom to the parameters
# menagerie itself uses on its pad boxes (solref 0.01, solimp 2 1 0.01) makes
# them solid. Applied on the *compiled* model (the spec-level iteration does
# not reach the included bodies). Purely a physics-accuracy fix: no geometry
# is added, so nothing here can leak into sim2real training.
MESH_CONTACT_SOLREF = [0.01, 1.0]
MESH_CONTACT_SOLIMP = [2.0, 1.0, 0.01, 0.5, 2.0]


def harden_mesh_contacts(model: "mujoco.MjModel") -> int:
    """Harden all mesh collision contacts of a compiled model; returns count."""
    n = 0
    for g in range(model.ngeom):
        if model.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and model.geom_contype[g] != 0:
            model.geom_solref[g] = MESH_CONTACT_SOLREF
            model.geom_solimp[g] = MESH_CONTACT_SOLIMP
            n += 1
    return n


def add_workspace(spec: mujoco.MjSpec) -> None:
    """Add the task workspace to a scene: mat, three cubes, container, top camera."""
    wb = spec.worldbody
    wb.add_geom(name="workspace_mat", type=mujoco.mjtGeom.mjGEOM_BOX, size=MAT_HALF, pos=MAT_POS, rgba=MAT_RGBA)

    for name, cx, cy, rgba in CUBES:
        body = wb.add_body(name=f"cube_{name}")
        body.pos = [cx, cy, CUBE_Z]
        body.add_freejoint()
        cg = body.add_geom(name=f"cube_{name}", type=mujoco.mjtGeom.mjGEOM_BOX, size=[CUBE_HALF] * 3,
                           rgba=rgba, density=CUBE_DENSITY)
        cg.solref = [0.01, 1.0]  # matches the menagerie gripper's own contact tuning

    o, t, h = BOX_HALF, BOX_WALL, BOX_WALL_H
    box = wb.add_body(name="cube_box")  # welded to the world: a fixed fixture
    box.pos = BOX_POS
    box.add_geom(name="cube_box_floor", type=mujoco.mjtGeom.mjGEOM_BOX,
                 size=[o, o, t], pos=[0.0, 0.0, MAT_TOP + t], rgba=BOX_RGBA)
    wall_z = MAT_TOP + 2 * t + h
    for sign, tag in ((-1.0, "-"), (1.0, "+")):
        box.add_geom(name=f"cube_box_wall_y{tag}", type=mujoco.mjtGeom.mjGEOM_BOX,
                     size=[o, t, h], pos=[0.0, sign * (o - t), wall_z], rgba=BOX_RGBA)
        box.add_geom(name=f"cube_box_wall_x{tag}", type=mujoco.mjtGeom.mjGEOM_BOX,
                     size=[t, o - 2 * t, h], pos=[sign * (o - t), 0.0, wall_z], rgba=BOX_RGBA)

    wb.add_camera(name="top_cam", pos=TOP_CAM_POS, quat=TOP_CAM_QUAT, fovy=TOP_CAM_FOVY)
