"""Interactive mount-pose adjuster for the camera bracket (keyboard, live preview).

Opens the robot (rest pose) with the bracket attached at the pose stored in
`preview_mount.py` (tutorial model) or `so101_assets.py` (menagerie model, the
default since the 2026-10-16 migration), then lets you nudge the bracket with
the keyboard while the MuJoCo window updates live. On exit it prints the tuned
values (ready to paste back) and also writes them to `renders/last_adjust.txt`.

Controls (hold; global listener -- don't type elsewhere while adjusting):

    arrow left / right    move  y- / y+          (parent-body-local, mm/s)
    arrow down / up       move  z- / z+
    n / m                 move  x- / x+
    q / e                 roll  (x-axis) - / +
    w / s                 pitch (y-axis) + / -
    a / d                 yaw   (z-axis) - / +
    shift (hold)          fine mode (10x smaller steps)
    Esc                   quit and print the result

The bracket frames: tutorial model -- attached to the `gripper` body, +x toward
the jaw tips; menagerie model -- attached to `Fixed_Jaw` (gripper servo), with
that body's own axes (servo housing spans x -30..+15, y -37..-12, z +-20 mm,
mechanism plane z=0).

Usage (from the repo root):

    uv run --frozen --with mujoco python \
        examples/so101_mujoco/assets/camera/adjust_mount.py
    # legacy tutorial model: append --model tutorial
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

import mujoco
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # examples/so101_mujoco
import preview_mount as pm  # noqa: E402
from so101_assets import (  # noqa: E402
    MENAGERIE_MOUNT_PARENT,
    MENAGERIE_MOUNT_POS,
    MENAGERIE_MOUNT_RPY_DEG,
    default_scene,
    menagerie_spec,
)

from lerobot.utils.keyboard_input import pynput_can_capture  # noqa: E402
from lerobot.utils.import_utils import _pynput_available  # noqa: E402

if _pynput_available:
    from pynput import keyboard
else:
    keyboard = None

TRANSLATE_RATE = 0.020  # m/s while a translation key is held
ROTATE_RATE = 20.0  # deg/s while a rotation key is held

KEY_HELP = (
    "arrows: y/z move | n/m: x move | q/e roll | w/s pitch | a/d yaw | "
    "shift: fine | Esc: quit & print values"
)

# The MuJoCo viewer window has its own single-letter shortcuts (e.g. W toggles
# wireframe), which fire whenever the window has keyboard focus. Keys are
# captured globally (pynput), so the collision-free workflow is: keep the
# keyboard focus on the TERMINAL while nudging with keys, and click the viewer
# only for mouse camera moves.
KEY_HELP_NOTES = (
    "Tip: keep keyboard focus on THIS terminal while nudging (keys work globally);\n"
    "     click the MuJoCo window only when you need the mouse for the camera.\n"
    "     If the view glitches (e.g. wireframe) after pressing keys with the window\n"
    "     focused: press the same key again to toggle back, or fix the checkboxes\n"
    "     in the viewer's right-hand panel."
)


def quat_from_rpy_deg(rpy):
    r, p, y = (np.radians(v) for v in rpy)
    cr, sr, cp, sp, cy, sy = (np.cos(r / 2), np.sin(r / 2), np.cos(p / 2), np.sin(p / 2), np.cos(y / 2), np.sin(y / 2))
    return np.array([cr * cp * cy + sr * sp * sy, sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy])


def rpy_deg_from_quat(q):
    w, x, y, z = q
    return [
        float(np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))),
        float(np.degrees(np.arcsin(np.clip(2 * (w * y - z * x), -1, 1)))),
        float(np.degrees(np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))),
    ]


def quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ])


def delta_quat_local(pitch_deg, roll_deg, yaw_deg):
    """Rotation expressed in the body's own (post-multiplied) frame."""
    qr = quat_from_rpy_deg([roll_deg, 0, 0])
    qp = quat_from_rpy_deg([0, pitch_deg, 0])
    qy = quat_from_rpy_deg([0, 0, yaw_deg])
    return quat_mul(qy, quat_mul(qp, qr))


def _snippet(pos, rpy, prefix: str = "MENAGERIE_MOUNT") -> str:
    return (
        f"{prefix}_POS = [{pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.4f}]\n"
        f"{prefix}_RPY_DEG = [{rpy[0]:.2f}, {rpy[1]:.2f}, {rpy[2]:.2f}]\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", choices=("menagerie", "tutorial"), default="menagerie",
                    help="which robot model the bracket is adjusted on")
    ap.add_argument("--self-test", type=float, default=0.0, help="auto-exit after N seconds (for smoke-testing)")
    args = ap.parse_args()

    pm.ensure_metric_stl()
    if args.model == "menagerie":
        spec = menagerie_spec()
        parent_name = MENAGERIE_MOUNT_PARENT
        init_pos = list(MENAGERIE_MOUNT_POS)
        init_rpy = list(MENAGERIE_MOUNT_RPY_DEG)
        prefix = "MENAGERIE_MOUNT"
    else:
        spec = mujoco.MjSpec.from_file(str(default_scene()))
        parent_name = "gripper"
        init_pos = list(pm.MOUNT_POS)
        init_rpy = list(pm.MOUNT_RPY_DEG)
        prefix = "MOUNT"
    mesh = spec.add_mesh(); mesh.name = "mbrk"; mesh.file = pm.METRIC_STL.as_posix()
    body = spec.body(parent_name).add_body(name="cam_bracket")
    body.pos = init_pos
    body.quat = quat_from_rpy_deg(init_rpy)
    geom = body.add_geom(name="cam_bracket")
    geom.type = mujoco.mjtGeom.mjGEOM_MESH
    geom.meshname = "mbrk"
    geom.rgba = [0.93, 0.91, 0.87, 1]
    model = spec.compile()
    data = mujoco.MjData(model)
    for j in range(model.njnt):
        if model.jnt_limited[j]:
            lo, hi = model.jnt_range[j]
            data.qpos[model.jnt_qposadr[j]] = 0.5 * (lo + hi)
    mujoco.mj_forward(model, data)

    bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "cam_bracket")
    pos = np.array(init_pos, dtype=float)
    quat = quat_from_rpy_deg(init_rpy)
    parent_bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, parent_name)
    lookat = data.xpos[parent_bid].copy() + [0.0, 0.0, -0.01]

    pressed: dict = {}
    if keyboard is not None and pynput_can_capture():
        def on_press(key):
            pressed[getattr(key, "char", None) or key] = True

        def on_release(key):
            pressed[getattr(key, "char", None) or key] = False

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
    else:
        listener = None
        print("WARNING: keyboard capture unavailable; nothing can be adjusted here.")

    print(KEY_HELP)
    print(KEY_HELP_NOTES)
    print(f"model: {args.model} (parent body: {parent_name})")
    print("initial:", np.round(pos * 1000, 2).tolist(), [round(v, 2) for v in rpy_deg_from_quat(quat)])

    from mujoco import viewer as mujoco_viewer

    t_end = time.monotonic() + args.self_test if args.self_test > 0 else None
    with mujoco_viewer.launch_passive(model, data) as viewer:
        cam = viewer.cam
        cam.lookat[:] = lookat
        cam.distance = 0.30
        cam.azimuth, cam.elevation = 225, -18
        if hasattr(viewer, "set_texts"):
            viewer.set_texts([(mujoco.mjtFontScale.mjFONTSCALE_100, mujoco.mjtGridPos.mjGRID_BOTTOMLEFT, KEY_HELP, None)])
        last_t = time.monotonic()
        last_save = 0.0
        out_path = HERE / "renders" / "last_adjust.txt"
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_text(_snippet(pos, rpy_deg_from_quat(quat), prefix), encoding="utf-8")
        try:
            while viewer.is_running():
                now = time.monotonic()
                dt = min(now - last_t, 0.1)
                last_t = now
                if t_end is not None and now >= t_end:
                    break
                if keyboard is not None and pressed.get(keyboard.Key.esc):
                    break

                shift = bool(pressed.get(keyboard.Key.shift, False) or pressed.get(keyboard.Key.shift_r, False)) if keyboard else False
                tr = TRANSLATE_RATE * (0.1 if shift else 1.0) * dt
                ro = ROTATE_RATE * (0.1 if shift else 1.0) * dt

                def held(*keys):
                    for k in keys:
                        if k is None:
                            continue
                        if pressed.get(k) or (isinstance(k, str) and pressed.get(k)):
                            return True
                    return False

                d_pos = np.zeros(3)
                if held(keyboard.Key.left):
                    d_pos[1] -= tr
                if held(keyboard.Key.right):
                    d_pos[1] += tr
                if held(keyboard.Key.down):
                    d_pos[2] -= tr
                if held(keyboard.Key.up):
                    d_pos[2] += tr
                if held("n"):
                    d_pos[0] -= tr
                if held("m"):
                    d_pos[0] += tr

                d_rot = [0.0, 0.0, 0.0]  # roll, pitch, yaw
                if held("q"):
                    d_rot[0] -= ro
                if held("e"):
                    d_rot[0] += ro
                if held("w"):
                    d_rot[1] += ro
                if held("s"):
                    d_rot[1] -= ro
                if held("a"):
                    d_rot[2] -= ro
                if held("d"):
                    d_rot[2] += ro

                if np.any(d_pos) or any(d_rot):
                    pos = pos + d_pos
                    quat = quat_mul(quat, delta_quat_local(d_rot[1], d_rot[0], d_rot[2]))
                    quat = quat / np.linalg.norm(quat)
                    model.body_pos[bid] = pos
                    model.body_quat[bid] = quat
                    mujoco.mj_forward(model, data)
                    if now - last_save > 1.0:  # periodic autosave: survive a hard kill
                        last_save = now
                        out_path.write_text(_snippet(pos, rpy_deg_from_quat(quat), prefix), encoding="utf-8")

                viewer.sync()
                time.sleep(1 / 60)
        except KeyboardInterrupt:
            pass

    if listener is not None:
        listener.stop()

    rpy = rpy_deg_from_quat(quat)
    print(f"\n=== paste into so101_assets.py ({prefix}_*) ===")
    print(_snippet(pos, rpy, prefix), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
