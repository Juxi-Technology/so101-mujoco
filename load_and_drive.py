#!/usr/bin/env python3
"""Load a SO-ARM101 MuJoCo model, dump its structure, and drive all joints.

Layer-1 verification for the SO-ARM101 MuJoCo reproduction: loads an MJCF
scene, prints a structural summary (joints / actuators / sites / cameras),
then runs a scripted motion -- a per-joint sweep ("rig check") followed by a
coordinated sine motion and a return to rest -- while rendering an mp4 video
and two stills. Rendering goes through ``mujoco.Renderer`` (WGL on Windows,
``MUJOCO_GL=egl`` on headless Linux).

Usage (from the repo root):

    uv run --no-project --with mujoco --with imageio --with imageio-ffmpeg \
        python examples/so101_mujoco/load_and_drive.py \
        --model path/to/scene.xml --out-dir out/

The model may be a bare robot MJCF (no floor/light) or a scene file that
includes one; both compile fine.
"""

from __future__ import annotations

import argparse
import itertools
import math
import os
import sys

import numpy as np
import mujoco

# ---------------------------------------------------------------- timeline (s)
T_SETTLE = 2.0  # hold the rest pose while actuators settle
T_SOLO = 2.2  # per-joint sweep duration
T_COORD = 6.0  # coordinated sinusoidal motion
T_BLEND = 1.5  # smooth return to rest
T_HOLD = 1.2  # final hold at rest

SOLO_AMP_CAP = 1.15  # rad; keeps the full sweep clear of the floor
FLOOR_CLEAR = 0.08  # m; minimum gripperframe height at sweep extremes


def build_targets(model: mujoco.MjModel) -> list[dict]:
    """One entry per actuator: safe drive range, rest center, amplitudes."""
    targets = []
    for a in range(model.nu):
        jid = int(model.actuator_trnid[a, 0])
        if model.jnt_limited[jid]:
            lo, hi = (float(v) for v in model.jnt_range[jid])
        else:
            lo, hi = -math.pi, math.pi
        margin = 0.05 * (hi - lo)
        targets.append(
            dict(
                act=a,
                jid=jid,
                lo=lo + margin,
                hi=hi - margin,
                center=0.5 * (lo + hi),
                amp_solo=min(0.42 * (hi - lo), SOLO_AMP_CAP),
                amp_coord=0.16 * (hi - lo),
                freq=0.10 + 0.02 * a,
            )
        )
    return targets


def ctrl_at(t: float, targets: list[dict], order: list[int], settle: float = T_SETTLE) -> np.ndarray:
    """Reference ctrl at sim time t: settle -> per-joint sweep -> sine -> rest."""
    n = len(targets)
    t1 = settle + T_SOLO * n
    t2 = t1 + T_COORD
    t3 = t2 + T_BLEND
    out = np.empty(n)
    for i, s in enumerate(targets):
        if t < settle:
            v = s["center"]
        elif t < t1:
            k = int((t - settle) // T_SOLO)  # which joint is sweeping now
            u = (t - settle) - k * T_SOLO
            if order[k] == i:
                v = s["center"] + s["amp_solo"] * math.sin(2 * math.pi * u / T_SOLO)
            else:
                v = s["center"]
        elif t < t2:
            v = s["center"] + s["amp_coord"] * math.sin(2 * math.pi * s["freq"] * (t - t1))
        elif t < t3:
            u = (t - t2) / T_BLEND
            ease = u * u * (3 - 2 * u)  # smoothstep
            v_end = s["center"] + s["amp_coord"] * math.sin(2 * math.pi * s["freq"] * T_COORD)
            v = s["center"] + (v_end - s["center"]) * (1 - ease)
        else:
            v = s["center"]
        out[i] = min(max(v, s["lo"]), s["hi"])
    return out


def summarize(model: mujoco.MjModel, model_path: str, model_name: str) -> list[str]:
    """Structural dump of the compiled model, as a list of text lines."""
    lines: list[str] = []
    add = lines.append

    def jname(jid: int) -> str:
        return mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, jid) or f"<{jid}>"

    add(f"model         : {model_path}")
    add(
        f"sizes         : nq={model.nq} nv={model.nv} nu={model.nu} "
        f"nbody={model.nbody} ngeom={model.ngeom} nmesh={model.nmesh} "
        f"ncam={model.ncam} nkey={model.nkey}"
    )
    add(
        f"options       : timestep={model.opt.timestep:.4f}s "
        f"gravity=({model.opt.gravity[0]:.1f},{model.opt.gravity[1]:.1f},{model.opt.gravity[2]:.1f}) "
        f"integrator={mujoco.mjtIntegrator(model.opt.integrator).name} "
        f"cone={mujoco.mjtCone(model.opt.cone).name}"
    )
    add(f"total mass    : {float(np.sum(model.body_mass)):.3f} kg")

    add("joints:")
    for j in range(model.njnt):
        r = model.jnt_range[j]
        lim = "limited" if model.jnt_limited[j] else "unlimited"
        dof = int(model.jnt_dofadr[j])
        add(
            f"  [{j}] {jname(j):<24s} type={mujoco.mjtJoint(model.jnt_type[j]).name:<7s} "
            f"qposadr={model.jnt_qposadr[j]} {lim} "
            f"range=({r[0]:+.4f},{r[1]:+.4f}) "
            f"damping={model.dof_damping[dof]:.3f} armature={model.dof_armature[dof]:.4f}"
        )

    add("actuators:")
    for a in range(model.nu):
        nm = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, a) or f"<{a}>"
        jid = int(model.actuator_trnid[a, 0])
        c = model.actuator_ctrlrange[a]
        f = model.actuator_forcerange[a]
        add(
            f"  [{a}] {nm:<24s} -> {jname(jid):<24s} "
            f"ctrl=({c[0]:+.4f},{c[1]:+.4f}) "
            f"kp={model.actuator_gainprm[a, 0]:.2f} kv={-model.actuator_biasprm[a, 2]:.2f} "
            f"forcerange=({f[0]:+.2f},{f[1]:+.2f})"
        )

    add("sites:")
    for s in range(model.nsite):
        nm = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_SITE, s) or f"<{s}>"
        body = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, model.site_bodyid[s])
        add(f"  [{s}] {nm:<16s} body={body}")

    add("cameras:")
    if model.ncam == 0:
        add("  (none)")
    for c in range(model.ncam):
        nm = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_CAMERA, c) or f"<{c}>"
        body = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, model.cam_bodyid[c])
        add(f"  [{c}] {nm:<16s} body={body}")
    return lines


def run(args: argparse.Namespace) -> int:
    import imageio

    if not os.path.isfile(args.model):
        print(f"model file not found: {args.model}", file=sys.stderr)
        return 2
    os.makedirs(args.out_dir, exist_ok=True)

    model = mujoco.MjModel.from_xml_path(args.model)
    # Grow the offscreen framebuffer if the model's default (640x480) is smaller
    # than the requested render size.
    model.vis.global_.offwidth = max(model.vis.global_.offwidth, args.width)
    model.vis.global_.offheight = max(model.vis.global_.offheight, args.height)
    data = mujoco.MjData(model)
    tag = args.tag or os.path.splitext(os.path.basename(args.model))[0]

    summary = summarize(model, args.model, tag)
    text = "\n".join(summary)
    print(text)
    summary_path = os.path.join(args.out_dir, f"{tag}_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")

    targets = build_targets(model)
    order = list(range(model.nu))

    # One end-effector site to watch: "gripperframe" in the new-calib models,
    # plain "gripper" in the old-calib model; last site as a fallback.
    gripper_sid = -1
    for want in ("gripperframe", "gripper"):
        sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, want)
        if sid >= 0:
            gripper_sid = sid
            break
    if gripper_sid < 0 and model.nsite > 0:
        gripper_sid = model.nsite - 1

    # Shrink solo amplitudes so the finger tip stays clear of the floor at the
    # sweep extremes: probe the model forward-kinematics at center +/- amp and
    # back off until the gripper site is at least FLOOR_CLEAR above z=0.
    if gripper_sid >= 0:
        probe = mujoco.MjData(model)
        q_rest = np.zeros(model.nq)
        for s in targets:
            q_rest[model.jnt_qposadr[s["jid"]]] = s["center"]
        for s in targets:
            qa = int(model.jnt_qposadr[s["jid"]])
            for sign in (1.0, -1.0):
                while s["amp_solo"] > 0.08:
                    q = q_rest.copy()
                    q[qa] = s["center"] + sign * s["amp_solo"]
                    probe.qpos[:] = q
                    mujoco.mj_forward(model, probe)
                    if float(probe.site_xpos[gripper_sid, 2]) >= FLOOR_CLEAR:
                        break
                    s["amp_solo"] *= 0.75

        # Same guard for the coordinated phase, checking every +/- combination
        # of the per-joint amplitudes so simultaneous extremes stay clear too.
        combos = list(itertools.product((1.0, -1.0), repeat=len(targets)))
        while max(s["amp_coord"] for s in targets) > 0.05:
            worst = float("inf")
            for combo in combos:
                q = q_rest.copy()
                for s, c in zip(targets, combo):
                    q[model.jnt_qposadr[s["jid"]]] = s["center"] + c * s["amp_coord"]
                probe.qpos[:] = q
                mujoco.mj_forward(model, probe)
                worst = min(worst, float(probe.site_xpos[gripper_sid, 2]))
            if worst >= FLOOR_CLEAR:
                break
            for s in targets:
                s["amp_coord"] *= 0.8

        def _amp(s: dict, key: str) -> str:
            nm = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, s["act"])
            return f"{nm}={s[key]:.3f}"

        print("solo amplitudes  (rad): " + ", ".join(_amp(s, "amp_solo") for s in targets))
        print("coord amplitudes (rad): " + ", ".join(_amp(s, "amp_coord") for s in targets))

    total_t = args.settle + T_SOLO * model.nu + T_COORD + T_BLEND + T_HOLD
    dt = model.opt.timestep
    spf = max(1, round(1.0 / (args.fps * dt)))  # physics steps per video frame
    video_fps = 1.0 / (spf * dt)
    n_frames = int(total_t * args.fps)
    print(f"\nrendering: {n_frames} frames @ {video_fps:.2f} fps "
          f"({spf} physics steps/frame, dt={dt:.4f}s), {args.width}x{args.height}")

    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultFreeCamera(model, cam)
    cam.lookat[:] = args.lookat
    cam.distance = args.distance
    cam.azimuth = args.azimuth
    cam.elevation = args.elevation

    renderer = mujoco.Renderer(model, args.height, args.width)

    fk_rest: np.ndarray | None = None
    fk_end: np.ndarray | None = None
    t_solo_end = args.settle + T_SOLO * model.nu
    t_coord_end = t_solo_end + T_COORD
    t_hold = t_coord_end + T_BLEND
    max_err_solo = 0.0  # tracking error, per-joint sweep phase
    max_err_coord = 0.0  # tracking error, coordinated phase
    max_err_hold = 0.0  # tracking error, final rest hold

    video_path = os.path.join(args.out_dir, f"{tag}.mp4")
    still_rest_path = os.path.join(args.out_dir, f"{tag}_rest.png")
    still_solo_path = os.path.join(args.out_dir, f"{tag}_solo.png")
    frame_rest = int(args.settle * args.fps)
    frame_solo = int((args.settle + 1.25 * T_SOLO) * args.fps)  # peak of 2nd joint

    writer = imageio.get_writer(
        video_path, fps=round(video_fps, 3), codec="libx264", quality=7,
        macro_block_size=None,
    )
    try:
        for fi in range(n_frames):
            for _ in range(spf):
                data.ctrl[:] = ctrl_at(float(data.time), targets, order, args.settle)
                mujoco.mj_step(model, data)
            err = 0.0
            for s in targets:
                q = float(data.qpos[model.jnt_qposadr[s["jid"]]])
                err = max(err, abs(q - float(data.ctrl[s["act"]])))
            now = float(data.time)
            if args.settle <= now < t_solo_end:
                max_err_solo = max(max_err_solo, err)
            elif t_solo_end <= now < t_coord_end:
                max_err_coord = max(max_err_coord, err)
            elif now >= t_hold:
                max_err_hold = max(max_err_hold, err)
            renderer.update_scene(data, camera=cam)
            frame = renderer.render()
            writer.append_data(frame)
            if fi == frame_rest:
                imageio.imwrite(still_rest_path, frame)
                if gripper_sid >= 0:
                    fk_rest = data.site_xpos[gripper_sid].copy()
            if fi == frame_solo:
                imageio.imwrite(still_solo_path, frame)
                if gripper_sid >= 0:
                    fk_end = data.site_xpos[gripper_sid].copy()
    finally:
        writer.close()
        renderer.close()

    print(f"\nvideo : {video_path}")
    print(f"stills: {still_rest_path} , {still_solo_path}")
    if fk_rest is not None and fk_end is not None:
        print(f"tip site xpos at rest : ({fk_rest[0]:+.3f},{fk_rest[1]:+.3f},{fk_rest[2]:+.3f})")
        print(f"tip site xpos at sweep: ({fk_end[0]:+.3f},{fk_end[1]:+.3f},{fk_end[2]:+.3f})")
    print(f"tracking |qpos-ctrl| solo phase : {max_err_solo:.4f} rad")
    print(f"tracking |qpos-ctrl| coord phase: {max_err_coord:.4f} rad")
    print(f"tracking |qpos-ctrl| rest hold  : {max_err_hold:.4f} rad")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", required=True, help="path to the MJCF scene/model")
    p.add_argument("--out-dir", default="out", help="directory for video/stills/summary")
    p.add_argument("--tag", default=None, help="output basename (default: model filename)")
    p.add_argument("--settle", type=float, default=T_SETTLE,
                   help="seconds to hold the rest pose before the sweep (soft models need more)")
    p.add_argument("--fps", type=int, default=25, help="video frame rate")
    p.add_argument("--width", type=int, default=960)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--lookat", type=float, nargs=3, default=[0.05, -0.01, 0.13])
    p.add_argument("--distance", type=float, default=0.68)
    p.add_argument("--azimuth", type=float, default=160.0)
    p.add_argument("--elevation", type=float, default=-18.0)
    return run(p.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
