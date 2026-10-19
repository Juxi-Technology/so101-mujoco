"""Render the task workspace and probe the arm's reachable floor area.

Builds the official scene + the workspace contents (mat, cubes, container,
``top_cam``), then:

  * renders the overhead camera view -> ``outputs/renders/workspace_top.png``
  * renders a 3/4 overview           -> ``outputs/renders/workspace_iso.png``
  * brute-forces arm joint poses and prints the floor-level reachable area,
    so object positions can be sanity-checked against it.

Usage (from the repo root):

    uv run --frozen --with mujoco --with imageio python \
        examples/so101_mujoco/preview_workspace.py
"""

from __future__ import annotations

import pathlib
import sys

import mujoco
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from so101_assets import CUBES, BOX_POS, add_workspace, menagerie_spec  # noqa: E402
from so101_mujoco_robot import SO101MujocoRobotConfig, _add_camera_module  # noqa: E402

RENDERS = HERE / "outputs" / "renders"


def main() -> None:
    import imageio.v2 as iio

    spec = menagerie_spec()
    add_workspace(spec)
    _add_camera_module(spec)  # bracket + camera module, as in real robot sessions
    model = spec.compile()
    data = mujoco.MjData(model)
    for j in range(model.njnt):
        if model.jnt_limited[j]:
            lo, hi = model.jnt_range[j]
            data.qpos[model.jnt_qposadr[j]] = 0.5 * (lo + hi)
    mujoco.mj_forward(model, data)

    model.vis.global_.offwidth, model.vis.global_.offheight = 1280, 960
    renderer = mujoco.Renderer(model, 480, 640)

    renderer.update_scene(data, camera="top_cam")
    RENDERS.mkdir(parents=True, exist_ok=True)
    iio.imwrite(RENDERS / "workspace_top.png", renderer.render())

    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultFreeCamera(model, cam)
    cam.lookat[:] = [0.24, 0.0, 0.06]
    cam.distance = 0.85
    cam.azimuth, cam.elevation = 145, -32
    renderer.update_scene(data, camera=cam)
    iio.imwrite(RENDERS / "workspace_iso.png", renderer.render())

    renderer.update_scene(data, camera="sim_cam")
    iio.imwrite(RENDERS / "workspace_wrist.png", renderer.render())
    renderer.close()
    print("renders:", RENDERS / "workspace_top.png", "|", RENDERS / "workspace_iso.png", "|", RENDERS / "workspace_wrist.png")

    # ---- reach probe: where can the grip point descend near the floor? ----
    joints = ["Pitch", "Elbow", "Wrist_Pitch"]
    pad_f = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "fixed_jaw_pad_2")
    pad_m = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "moving_jaw_pad_2")
    jaw_jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "Jaw")
    data.qpos[int(model.jnt_qposadr[jaw_jid])] = float(model.jnt_range[jaw_jid][0])  # jaws closed
    adr = {
        n: int(model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n)]) for n in joints
    }

    def frac(n, f):
        r = model.jnt_range[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n)]
        return float(r[0] + (r[1] - r[0]) * f)

    fr = np.linspace(0.05, 0.95, 13)
    lows = []
    for a in fr:
        for b in fr:
            for c in fr:
                for n, f in zip(joints, (a, b, c)):
                    data.qpos[adr[n]] = frac(n, f)
                mujoco.mj_forward(model, data)
                p = 0.5 * (data.geom_xpos[pad_f] + data.geom_xpos[pad_m])
                if p[2] < 0.055:  # grip point near the floor: usable for picking/placing
                    lows.append(p.copy())
    lows = np.asarray(lows)
    print(f"gripper-tip poses below 55 mm: {len(lows)}")
    if len(lows):
        print(f"  x reach: {lows[:, 0].min():.3f} .. {lows[:, 0].max():.3f} m")
        print(f"  y reach: {lows[:, 1].min():.3f} .. {lows[:, 1].max():.3f} m")
    print("cubes at x=%.2f y=%s | box at %s" % (CUBES[0][1], [c[2] for c in CUBES], BOX_POS[:2]))


if __name__ == "__main__":
    main()
