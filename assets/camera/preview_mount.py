"""Prototype: mount the camera bracket onto the simulated SO-ARM101 and render.

Iterative tool for the "camera into the scene" step (docs/08-roadmap.md phase 2).
The bracket mesh is attached under the `wrist` link -- the piece BEFORE the
wrist_roll joint -- so the camera does NOT roll with the gripper (a wrist-cam
must keep a stable view while the gripper rotates). The mount pose was
transferred from the reviewed jaw-root placement and verified: the bracket's
world pose is identical at wrist_roll = center and center - 90 deg.

Adjust MOUNT_POS / MOUNT_RPY_DEG below, rerun, and compare the renders in
`renders/` against photos of the real assembly until they match.

Usage (from the repo root):

    uv run --frozen --with mujoco --with imageio python \
        examples/so101_mujoco/assets/camera/preview_mount.py
"""

from __future__ import annotations

import pathlib
import sys

import mujoco
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # examples/so101_mujoco
from so101_assets import default_scene  # noqa: E402

SRC_STL = HERE / "mesh" / "arm_mount_bracket_v3.stl"
METRIC_STL = HERE / "mesh" / "arm_mount_bracket_v3_m.stl"
RENDERS = HERE / "renders"

# ---- mount pose, in the `gripper` body frame (gripper servo side) ----------
# meters / degrees; solved hole-to-hole and refined by hand in adjust_mount.py.
MOUNT_POS = [0.0021, 0.0275, 0.0015]
MOUNT_RPY_DEG = [-176.72, -58.51, 86.08]

# ---- camera module (HBVCAM-F2170HD V22: 25 x 30 x 5.2 mm board + lens) ----
# Pose in the *camera bracket's* local frame. Camera body origin = back face
# center; +z = lens/view direction; lens sits +2.5 mm off-center (datasheet).
# First guess: mounted behind the plate so the lens looks through the window.
CAMERA_POS = [0.0282, 0.0, 0.0579]
# tuned 2026-10-16 with adjust_camera.py; un-rolled +90 deg about the view axis on
# 2026-10-16 so image-up = world-up (the earlier tune ended up 90 deg on its side).
CAMERA_RPY_DEG = [-16.48, -88.06, 15.86]
CAMERA_FOVY = 46.6  # deg vertical (HBVCAM-F2170HD V22; refined by eye 2026-10-16)


def ensure_metric_stl() -> pathlib.Path:
    """The CAD STL is in millimeters; write a meter-scaled copy with the bbox
    bottom-center re-originated to (0, 0, 0) so mount poses are intuitive."""
    import struct

    with open(SRC_STL, "rb") as f:
        header = f.read(80)
        (n,) = struct.unpack("<I", f.read(4))
        tris = np.frombuffer(f.read(n * 50), dtype=np.uint8).reshape(n, 50)
    verts = np.frombuffer(tris[:, 12:48].copy().tobytes(), dtype="<f4").reshape(n, 3, 3) * 0.001
    lo = verts.reshape(-1, 3).min(0)
    hi = verts.reshape(-1, 3).max(0)
    offset = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])  # bottom-center -> origin
    verts = verts - offset
    out = np.zeros(n, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    out["v"] = verts
    with open(METRIC_STL, "wb") as f:
        f.write(b"so101 bracket v3, meters, bottom-center origin".ljust(80, b"\0"))
        f.write(struct.pack("<I", n))
        f.write(out.tobytes())
    print(f"metric STL: {METRIC_STL.name}  size(mm)={np.round((hi - lo) * 1000, 1)}")
    return METRIC_STL


def quat_from_rpy_deg(rpy_deg: list[float]) -> np.ndarray:
    r, p, y = (np.radians(v) for v in rpy_deg)
    cr, sr, cp, sp, cy, sy = np.cos(r / 2), np.sin(r / 2), np.cos(p / 2), np.sin(p / 2), np.cos(y / 2), np.sin(y / 2)
    return np.array(
        [cr * cp * cy + sr * sp * sy, sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy]
    )  # [w, x, y, z]


def main() -> None:
    import imageio  # lazy: importers of this module (e.g. adjust_mount) don't need it

    metric_stl = ensure_metric_stl()
    spec = mujoco.MjSpec.from_file(str(default_scene()))

    mesh = spec.add_mesh()
    mesh.name = "cam_bracket"
    mesh.file = metric_stl.as_posix()  # absolute path: meshdir is not used

    parent = spec.body("gripper")
    body = parent.add_body(name="cam_bracket")
    body.pos = MOUNT_POS
    body.quat = quat_from_rpy_deg(MOUNT_RPY_DEG)
    geom = body.add_geom(name="cam_bracket")
    geom.type = mujoco.mjtGeom.mjGEOM_MESH
    geom.meshname = "cam_bracket"
    geom.rgba = [0.93, 0.91, 0.87, 1]

    # camera module (primitive build from the datasheet dimensions)
    cam_body = body.add_body(name="camera")
    cam_body.pos = CAMERA_POS
    cam_body.quat = quat_from_rpy_deg(CAMERA_RPY_DEG)
    pcb = cam_body.add_geom(name="cam_pcb")
    pcb.type = mujoco.mjtGeom.mjGEOM_BOX
    pcb.size = [0.0125, 0.015, 0.000775]  # 25 x 30 x 1.55 mm
    pcb.pos = [0.0, 0.0, 0.000775]
    pcb.rgba = [0.12, 0.12, 0.14, 1]
    lens = cam_body.add_geom(name="cam_lens")
    lens.type = mujoco.mjtGeom.mjGEOM_CYLINDER
    lens.size = [0.0032, 0.001825, 0.0]  # r 3.2 mm, h 3.65 mm (axis = local z)
    lens.pos = [0.0, 0.0025, 0.003375]
    lens.rgba = [0.06, 0.06, 0.07, 1]
    view = cam_body.add_camera(name="sim_cam")
    view.pos = [0.0, 0.0025, 0.0052]
    # MuJoCo cameras look along their local -Z; rotate the element 180 deg about
    # Y so the recorded view actually comes out of the lens (+z of this body).
    view.quat = quat_from_rpy_deg([0.0, 180.0, 0.0])
    view.fovy = CAMERA_FOVY

    model = spec.compile()
    data = mujoco.MjData(model)
    for j in range(model.njnt):
        if model.jnt_limited[j]:
            lo, hi = model.jnt_range[j]
            data.qpos[model.jnt_qposadr[j]] = 0.5 * (lo + hi)
    mujoco.mj_forward(model, data)

    model.vis.global_.offwidth, model.vis.global_.offheight = 960, 720
    renderer = mujoco.Renderer(model, 720, 960)
    sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "gripperframe")
    target = data.site_xpos[sid].copy()

    RENDERS.mkdir(exist_ok=True)
    for name, az, el, dist in [
        ("mount_side", 200, -8, 0.32),
        ("mount_iso", 135, -25, 0.34),
        ("mount_front", 250, -5, 0.30),
    ]:
        cam = mujoco.MjvCamera()
        mujoco.mjv_defaultFreeCamera(model, cam)
        cam.lookat[:] = target
        cam.distance = dist
        cam.azimuth, cam.elevation = az, el
        renderer.update_scene(data, camera=cam)
        imageio.imwrite(RENDERS / f"{name}.png", renderer.render())

    # what the simulated camera itself sees
    renderer.update_scene(data, camera="sim_cam")
    imageio.imwrite(RENDERS / "camera_view.png", renderer.render())
    print("renders:", ", ".join(sorted(p.name for p in RENDERS.glob("mount_*.png"))) + ", camera_view.png")


if __name__ == "__main__":
    main()
