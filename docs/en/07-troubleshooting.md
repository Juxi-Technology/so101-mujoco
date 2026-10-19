# 07 · Troubleshooting and Lessons Learned

Pitfalls actually encountered in this workflow, organized by symptom for quick lookup.

## Environment

| Symptom | Cause and solution |
| --- | --- |
| `uv sync` reports `failed to persist temporary file ... os error 17（跨盘）` | A Windows-specific quirk of this machine's uv cache directory being on another drive. Prefix every uv command with `export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'` |
| Console floods with dozens of `libtorchcodec_core*.dll` load failures | Noise warnings: after torchcodec fails to load, it automatically falls back to **pyav**. Measured (smoke [5]): pyav **encodes and decodes video datasets correctly**, and neither state nor video datasets are affected |
| `python` opens the Microsoft Store | Use the uv-managed Python; do not use the Store version |

## Teleoperation

| Symptom | Cause and solution |
| --- | --- |
| Keyboard control feels "very slow" | `--teleop.rate` defaults to a conservative 60 units/second; raise it to **150** for a normal feel (full stroke in about 1.3 s) |
| Startup log floods with `clamped to be safe` WARNINGs | Normal output while the rate limiter catches up; it stops once the target is reached |
| Simulated arm is off by a few degrees when the leader arm is centered | A fixed offset caused by asymmetric calibration ranges—use `so101_leader_trim` for automatic trimming ([05](05-leader-digital-twin.md)) |
| The arm suddenly moves on connection | By design: real hardware engages torque and moves toward the midpoint/leader-arm pose; keep space around it |
| The arm goes limp and drops after exiting with Ctrl-C | Normal: torque is disabled on disconnect; support it by hand |
| Typing during teleoperation/recording drives the arm | The keyboard listener is **global and does not swallow keystrokes**: mapped keys pressed in any window (including pinyin letters) enter the key queue. Do not type during keyboard-mode teleoperation/recording; leader-arm mode does not have this issue |

## Recording

| Symptom | Cause and solution |
| --- | --- |
| After exiting with `q`, the letters pressed during the session "all spill into the command line at once" | Backlogged echo from the Windows console input buffer; the launcher has built-in `drain_pending_keys()` cleanup (only older sessions show this symptom) |
| An episode has action span all zero | Empty recording (nobody moved)—move a bit before recording, or delete that episode afterwards |
| Large error in the first second of an episode | Convergence segment: at the moment recording starts, the follower arm is still at its initial pose while the leader arm is parked elsewhere; putting the leader arm near the midpoint beforehand avoids it |
| The dataset "disappears" after setting `--dataset.root` to a parent directory | **root is the dataset directory itself**; use a fresh root for every recording session |
| Difference between `Esc` and `q` | `q` only stops recording; `Esc` also disconnects keyboard teleoperation. Both now exit cleanly (fixed); make a habit of using `q` |
| On save, `ValueError: You must add one or several frames...` and the process exits with the error | Extra `→`/`n` presses during the **gap** between episodes (most commonly: saving + dual-stream video encoding pauses for tens of seconds, the console looks stuck, and you press it a few more times), leaving a flag that gets consumed at the start of the next episode → **0-frame empty episode**, and upstream crashes when saving an empty episode (a known lerobot edge case). **Already-saved episodes are unaffected and the data is intact**; just restart the session and continue. **Protection added** (2026-10-16): at the start of each episode `record.py` clears `→`/`←` flags left over from the gap (keys still work normally during recording), and before saving it prints the hint `saving the episode + encoding videos now...`; regression test `smoke_test.py` [7] |
| `KeyError: 'wrist'` at the instant recording starts (image datasets) | The recording loop read observations before the camera's first frame had rendered; **fixed** (2026-10-16): the robot plugin's `connect()` now waits for the first frame to be ready before returning |
| Video-enabled scripts report `BrokenProcessPool` / `Invalid argument: '<stdin>'` | Video encoding uses a **multiprocessing pool**, and child processes must re-import the entry module by file path—running the recording script via `python - <<EOF` (stdin) crashes. Save the script as a real `.py` file and run that (the real entry point `record.py` is unaffected) |
| On saving an episode, `SvtMalloc[fatal]: allocate memory failed ... av.error.MemoryError: [Errno 12] ... 'avcodec_open2(libsvtav1)'` and the whole session exits | The upstream default encoder **libsvtav1** fails a large one-shot memory allocation when the two camera streams (wrist+top) open concurrently (more likely under simulation + preview window load; hit in practice on 2026-10-16). **Fixed**: `record.py` injects `--dataset.rgb_encoder.vcodec=h264` by default (dual-stream h264 encoding verified; explicitly passing vcodec overrides it). Saved episodes are intact; a crash may leave `tmp*/` and orphan parquet files in the dataset directory (clean up as done for run2) |
| Video stutters during recording (especially after pressing `→`), but control itself has no latency | What stutters is the **save/encode window**: encoder processes use all CPU by default (two concurrent video streams) while the simulation thread is still rendering 5 views (more noticeable on integrated graphics). The control loop itself is unaffected—trust the cadence numbers (29.97 Hz throughout, 0 ticks over budget, measured). **Mitigated** (2026-10-16): `record.py` defaults to `--dataset.encoder_threads=2` (2 threads per encode stream); camera preview windows drop to 15 Hz (`--robot.preview_fps`). The shorter the episodes, the larger the share of time spent saving and the more stutter you feel; to eliminate pauses entirely, use `--dataset.streaming_encoding=true` (encode while recording; upstream-recommended, pending verification) |
| On saving an episode the encoder reports **memory allocation failure** and the whole session exits (includes svtav1's `SvtMalloc`, x264's `malloc ... failed`, and `avcodec_open2` errors) | This machine's system commit charge has long been close to its limit (measured 2026-10-16: **105.9 GB / 119.7 GB**, with 29 days of continuous uptime). Each save starts 2 new encoder processes (each loading torch/av, causing large commit spikes), and starting them concurrently at the cliff edge tips it over. **Mitigated**: `record.py` now adds **one automatic retry on encode failure** (transient failures no longer lose an episode), and save-time log flooding is muted (`av.logging.set_libav_level` + HF progress bars). **The real fix is restarting the machine** (clears commit accumulated from long uptime / kernel leaks; user-space processes account for only 27 GB, the rest is in the kernel/driver layer and cannot be killed); check with: `Get-Counter '\Memory\Committed Bytes'` vs `'\Memory\Commit Limit'` |

## Hardware

| Symptom | Cause and solution |
| --- | --- |
| COM port number differs from last time | Port numbers change with replugging/port switches; list the ports first every time ([03](03-hardware-calibration.md)) |
| Read-only check reports missing servos | A wiring/power problem; check the driver board and wire order first, do not rush into calibration |
| `shoulder_lift` direction is counterintuitive (simulation) | The model's positive direction points down; verify the sign before mapping ([02](02-sim-model-verification.md)) |

## Design Notes (Why It Is Done This Way)

- **MuJoCo rewrites mesh vertex data**: after `<mesh>` is loaded, `mjModel.mesh_vert` stores vertices in the **mesh's own coordinate frame**
  (the origin is recentered on the vertex centroid and the axes are reordered), no longer in the file's original coordinates—using it directly to compute bounding boxes or fit CAD dimensions
  gives wrong results (rendering is unaffected). To get the true CAD geometry, parse the original file (as done in `preview_mount.py` /
  `step_to_stl.py`). Hit once: the mount's true dimensions are 54.3 × 35.0 × 75.0 mm.
- **A MuJoCo camera looks along its frame's −Z**: a `<camera>` element does not look along its own +Z (the direction the lens protrudes). The first version
  of the camera module built the lens on +Z with the element oriented identity → the image was effectively "looking backward" from the back of the PCB,
  **the lens direction and image direction were exactly opposite** (the root cause of "the direction it turns does not match the image" during tuning; located on 2026-10-16 with red/blue board comparison render tests).
  Fix: rotate the camera element 180° about Y (`view.quat = RPY(0,180,0)`, unified in preview_mount / adjust_camera / the robot plugin);
  `adjust_camera.py` gained a "sim_cam live view" real-time window so what you see is what you get while tuning the lens.
- **The official tutorial MJCF's gripper is a "beak-style" point-contact gripper**: the two tooth tips close to a ~2.3 mm point contact with almost no usable gripping surface.
  Systematic physics experiments (2026-10-16, hundreds of trials) concluded: wherever a cube is placed near the jaw opening, it is scooped/wedged out during the ~100° closing sweep and
  cannot be grasped (true for 16–34 mm cubes; the mechanical stroke and torque themselves are normal). **Note: do not fix this by "adding collision pads"**—adding tooth plates
  to the jaws was tried (it significantly improved gripping), but that is **geometry that does not exist on the real robot**; a trained policy would depend on it and cause sim2real distortion, so it was removed. The correct fix is to
  **replace the official model's gripper with the real robot's gripper geometry** (e.g. mujoco_menagerie's SO-ARM101 or a CAD reconstruction of your own), while physical parameters should stay consistent with the real robot.
- **The official default contact parameters are too "soft" and cause physical tunneling**: the `solref` time constant defaults to 20 ms, so fast/thin contacts
  (a cube landing on a thin gripper surface, the closing sweep) pass through each other "before a force can develop"—the symptom being "the cube falls straight through the gripper surface".
  Fix (2026-10-16): harden the contact parameters—`harden_mesh_contacts` hardens the `solref` of all mesh colliders after compilation to the same value used by the menagerie tooth surfaces (0.01 s), and cube contacts are treated the same way.
  A pure physics-fidelity fix that adds no geometry.
- **The simulated robot has migrated to the mujoco_menagerie SO-ARM100 model** (2026-10-16): the original tutorial zip's MJCF is
  a kinematics demo piece whose gripper cannot grasp; the menagerie model is processed from the real robot's CAD—the gripper has dedicated collision tooth surfaces and hard contact parameters,
  and across the four tooth positions (shallow→deep) it was measured to stop against, grip, and lift a 34 mm cube. Migration key points: the model is vendored at
  `assets/menagerie_so_arm100/` (Apache-2.0, LICENSE included); joint mapping and unit signs are in `MODEL_JOINT`
  (determined joint by joint against the old model's world motion; the wrist_roll sign awaits verification via real-hardware teleoperation); the model's base is rotated +90° about Z so its
  working front faces +x; the mount is attached to the side of the Fixed_Jaw (servo #6) instead (initially located by parsing search, then manually fine-tuned and finalized on 2026-10-16 by the user against real-machine
  photos using `adjust_mount.py --model menagerie`: `[0.1, -0.7, 24.7]mm`, `RPY [0.34, -27.20, 89.51]°`). The old tutorial model and tools are left untouched for reference at any time.
- **Why use a uv project environment instead of conda**: `.venv` lives alongside the project, versions are pinned by `uv.lock`, and deleting the directory reclaims it,
  fully isolated from the machine's conda environments; `uv run` never installs anything into an activated conda environment. This machine's `lerobot` conda environment
  points at **another copy of the repository** (`lerobot-main`), and the two do not interfere.
- **Why all plugins live in `examples/so101_mujoco/`**: they integrate through the official registration mechanism (`register_subclass`)
  with **zero modifications to the lerobot source**; upgrading upstream only requires a re-sync.
