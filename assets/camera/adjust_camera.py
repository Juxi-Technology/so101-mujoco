"""Interactive camera-module adjuster (keyboard, live preview + on-demand photos).

Same interaction style as ``adjust_mount.py``, but for the camera module on the
bracket's camera plate. Opens the SO-ARM101 (rest pose) with the bracket and
the camera (built from the HBVCAM-F2170HD datasheet dimensions), then nudges
the camera with the keyboard.

Controls (hold; the global listener works while THIS terminal has focus -- keep
the mouse clicks on the MuJoCo window only when moving the view):

    arrow left / right    move  y- / y+          (camera-local, mm/s)
    arrow down / up       move  z- / z+          (z = along the lens axis)
    n / m                 move  x- / x+          (x = lens direction)
    q / e                 roll  (x-axis) - / +
    w / s                 pitch (y-axis) + / -
    a / d                 yaw   (z-axis) - / +
    , / .                 fovy  - / +            (1 deg; shift = 0.2 deg)
    p                     save a photo FROM the simulated camera to renders/
    shift (hold)          fine mode (10x smaller steps)
    Esc                   quit and print the result

Camera-local frame: +z = lens/view direction, +x = board width (25 mm side),
+y = board height (30 mm side); the lens sits 2.5 mm off-center toward +y.

A second window shows the simulated camera's LIVE view (this is what the robot
would record). A rerun resumes from `renders/last_camera.txt`, so quitting does
not lose the session's tuning; on exit the values are also printed, ready to
paste into preview_mount.py.

Note: the lens tip (+z) IS the view direction -- the camera element is rotated
180 deg about Y because MuJoCo cameras look along their local -Z.

Usage (from the repo root):

    uv run --frozen --with mujoco --with imageio python \
        examples/so101_mujoco/assets/camera/adjust_camera.py
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import sys
import time

import mujoco
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # examples/so101_mujoco
import preview_mount as pm  # noqa: E402
from so101_assets import default_scene  # noqa: E402

from lerobot.utils.keyboard_input import pynput_can_capture  # noqa: E402
from lerobot.utils.import_utils import _pynput_available  # noqa: E402

if _pynput_available:
    from pynput import keyboard
else:
    keyboard = None

TRANSLATE_RATE = 0.020  # m/s while a translation key is held
ROTATE_RATE = 20.0  # deg/s while a rotation key is held
FOVY_RATE = 2.0  # deg/s while , / . is held

KEY_HELP = (
    "arrows: y/z move | n/m: x move (lens axis) | q/e roll | w/s pitch | a/d yaw | "
    ",/. fovy | p: save camera photo | shift: fine | Esc: quit"
)
KEY_HELP_NOTES = (
    "Tip: keep keyboard focus on THIS terminal while nudging (keys work globally).\n"
    "     THREE windows are open: this terminal (keys), the assembly view (mouse\n"
    "     orbit only), and 'sim_cam live view' -- tune until THAT view looks right.\n"
    "     If a view glitches (e.g. wireframe), press the same key again."
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
    qr = quat_from_rpy_deg([roll_deg, 0, 0])
    qp = quat_from_rpy_deg([0, pitch_deg, 0])
    qy = quat_from_rpy_deg([0, 0, yaw_deg])
    return quat_mul(qy, quat_mul(qp, qr))


def build_model():
    pm.ensure_metric_stl()
    spec = mujoco.MjSpec.from_file(str(default_scene()))
    mesh = spec.add_mesh(); mesh.name = "cam_bracket"; mesh.file = pm.METRIC_STL.as_posix()
    bracket = spec.body("gripper").add_body(name="cam_bracket")
    bracket.pos = pm.MOUNT_POS
    bracket.quat = pm.quat_from_rpy_deg(pm.MOUNT_RPY_DEG)
    bg = bracket.add_geom(name="cam_bracket")
    bg.type = mujoco.mjtGeom.mjGEOM_MESH
    bg.meshname = "cam_bracket"
    bg.rgba = [0.93, 0.91, 0.87, 1]

    cam = bracket.add_body(name="camera")
    cam.pos = pm.CAMERA_POS
    cam.quat = pm.quat_from_rpy_deg(pm.CAMERA_RPY_DEG)
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
    # Y so the live view comes out of the lens (+z of this body).
    view.quat = quat_from_rpy_deg([0.0, 180.0, 0.0])
    view.fovy = pm.CAMERA_FOVY

    model = spec.compile()
    data = mujoco.MjData(model)
    for j in range(model.njnt):
        if model.jnt_limited[j]:
            lo, hi = model.jnt_range[j]
            data.qpos[model.jnt_qposadr[j]] = 0.5 * (lo + hi)
    mujoco.mj_forward(model, data)
    return model, data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-test", type=float, default=0.0)
    args = ap.parse_args()

    model, data = build_model()
    bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "camera")
    cid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, "sim_cam")
    pos = np.array(pm.CAMERA_POS, dtype=float)
    quat = quat_from_rpy_deg(pm.CAMERA_RPY_DEG)
    fovy = float(pm.CAMERA_FOVY)

    # Continue from the previous session's autosaved state (renders/last_camera.txt)
    # so quitting and rerunning does not lose tuned values.
    resume_path = HERE / "renders" / "last_camera.txt"
    if resume_path.exists():
        try:
            vals: dict = {}
            for line in resume_path.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    vals[k.strip()] = ast.literal_eval(v.strip())
            pos = np.array(vals["CAMERA_POS"], dtype=float)
            quat = quat_from_rpy_deg(vals["CAMERA_RPY_DEG"])
            fovy = float(vals["CAMERA_FOVY"])
            print("resumed from", resume_path.name)
        except Exception as exc:  # noqa: BLE001
            print("could not parse", resume_path.name, "-", exc)
    model.body_pos[bid] = pos
    model.body_quat[bid] = quat
    model.cam_fovy[cid] = fovy
    mujoco.mj_forward(model, data)

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
        print("WARNING: keyboard capture unavailable; nothing can be adjusted.")

    def held(*keys):
        return any(pressed.get(k) for k in keys if k is not None)

    print(KEY_HELP)
    print(KEY_HELP_NOTES)
    print("initial CAMERA_POS:", np.round(pos * 1000, 2).tolist(),
          "RPY:", [round(v, 2) for v in rpy_deg_from_quat(quat)], "fovy:", fovy)

    out_txt = HERE / "renders" / "last_camera.txt"
    out_txt.parent.mkdir(exist_ok=True)

    def snippet() -> str:
        rpy = rpy_deg_from_quat(quat)
        return (
            f"CAMERA_POS = [{pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.4f}]\n"
            f"CAMERA_RPY_DEG = [{rpy[0]:.2f}, {rpy[1]:.2f}, {rpy[2]:.2f}]\n"
            f"CAMERA_FOVY = {fovy:.1f}\n"
        )

    from mujoco import viewer as mujoco_viewer

    still_renderer = mujoco.Renderer(model, 480, 640)
    t_end = time.monotonic() + args.self_test if args.self_test > 0 else None
    with mujoco_viewer.launch_passive(model, data) as viewer, \
            mujoco_viewer.launch_passive(model, data, show_left_ui=False, show_right_ui=False) as pov:
        viewer.cam.lookat[:] = [0.30, -0.01, 0.24]
        viewer.cam.distance = 0.30
        viewer.cam.azimuth, viewer.cam.elevation = 225, -18
        if hasattr(viewer, "set_texts"):
            viewer.set_texts([(mujoco.mjtFontScale.mjFONTSCALE_100, mujoco.mjtGridPos.mjGRID_BOTTOMLEFT, KEY_HELP, None)])
        # Second window = what the simulated camera itself sees (live).
        pov.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
        pov.cam.fixedcamid = cid
        if hasattr(pov, "set_texts"):
            pov.set_texts([(mujoco.mjtFontScale.mjFONTSCALE_100, mujoco.mjtGridPos.mjGRID_TOPLEFT,
                            "sim_cam live view -- aim until THIS looks right", None)])
        last_t = time.monotonic()
        last_save = 0.0
        try:
            while viewer.is_running() or pov.is_running():
                now = time.monotonic()
                dt = min(now - last_t, 0.1)
                last_t = now
                if t_end is not None and now >= t_end:
                    break
                if keyboard is not None and pressed.get(keyboard.Key.esc):
                    break

                shift = bool(pressed.get(keyboard.Key.shift, False) or pressed.get(keyboard.Key.shift_r, False))
                tr = TRANSLATE_RATE * (0.1 if shift else 1.0) * dt
                ro = ROTATE_RATE * (0.1 if shift else 1.0) * dt
                fo = FOVY_RATE * (0.1 if shift else 1.0) * dt

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

                d_rot = [0.0, 0.0, 0.0]
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

                changed = False
                if np.any(d_pos) or any(d_rot):
                    pos = pos + d_pos
                    quat = quat_mul(quat, delta_quat_local(d_rot[1], d_rot[0], d_rot[2]))
                    quat = quat / np.linalg.norm(quat)
                    model.body_pos[bid] = pos
                    model.body_quat[bid] = quat
                    changed = True
                if held(","):
                    fovy = max(10.0, fovy - fo)
                    model.cam_fovy[cid] = fovy
                    changed = True
                if held("."):
                    fovy = min(120.0, fovy + fo)
                    model.cam_fovy[cid] = fovy
                    changed = True
                if changed:
                    mujoco.mj_forward(model, data)
                    if now - last_save > 1.0:
                        last_save = now
                        out_txt.write_text(snippet(), encoding="utf-8")

                if pressed.pop("p", False):
                    try:
                        import imageio

                        still_renderer.update_scene(data, camera="sim_cam")
                        shot = HERE / "renders" / f"camera_view_{time.strftime('%H%M%S')}.png"
                        imageio.imwrite(shot, still_renderer.render())
                        print("photo saved:", shot.name)
                    except ImportError:
                        print("photo needs imageio: rerun with --with imageio")

                if not pov.is_running():
                    # The live view window was closed: bring it straight back.
                    print("live view window closed -- reopening")
                    pov = mujoco_viewer.launch_passive(model, data, show_left_ui=False, show_right_ui=False)
                    pov.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
                    pov.cam.fixedcamid = cid
                    if hasattr(pov, "set_texts"):
                        pov.set_texts([(mujoco.mjtFontScale.mjFONTSCALE_100, mujoco.mjtGridPos.mjGRID_TOPLEFT,
                                        "sim_cam live view -- aim until THIS looks right", None)])
                if viewer.is_running():
                    viewer.sync()
                if pov.is_running():
                    pov.sync()
                time.sleep(1 / 60)
        except KeyboardInterrupt:
            pass

    if listener is not None:
        listener.stop()
    still_renderer.close()

    print("\n=== paste into preview_mount.py ===")
    print(snippet(), end="")
    out_txt.write_text(snippet(), encoding="utf-8")
    print(f"(also saved to {out_txt})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
