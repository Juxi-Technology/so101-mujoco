# 02 · Simulation Model Verification (MJCF Loading and Driving)

## Model Sources

All three public MJCF models for the SO-ARM101 have been verified to work in this project:

| Short name | File | Source |
| --- | --- | --- |
| Official – new calibration | `SO101/so101_new_calib.xml` | TheRobotStudio/SO-ARM100 official repository; **the tutorial zip in this repository contains an identical copy** (byte-for-byte identical) |
| Official – old calibration | `SO101/so101_old_calib.xml` | Same repository (not included in the zip; download required) |
| ROS2 description package | `so_arm101_description/mjcf/so_arm101.xml` | Tutorial attachment `SO-ARM101_ROS2.zip` in this repository |

Note: the zip extraction procedure was provided by an early version of `so101_assets.py` and is kept for reference; since 2026-10-16 the simulated robot has migrated to the
**mujoco_menagerie SO-ARM100 model** (vendored at `assets/menagerie_so_arm100/`; see the design notes in [07](07-troubleshooting.md) for the rationale and key points).

## Drive and Render Verification

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/load_and_drive.py \
    --model "<模型路径>" --out-dir out
```

The script prints a structural summary (joints/actuators/gains/ranges) and renders a verification video and still frames of "six joints swept one by one + coordinated sine motion".
A sample structural summary is available in `reports/` (shipped with the repository); the comparison videos (`media/`) are large and not distributed with the repository—they can be regenerated at any time with the command above.

## Key Differences Between the Three Models (measured)

| Item | Official – new calibration | Official – old calibration | ROS2 description package |
| --- | --- | --- | --- |
| Zero-position semantics | Joint **mid-stroke** | Fully **extended horizontal** position | Mid-stroke |
| Joint names | `shoulder_pan` | Same as left | `shoulder_pan_joint` (suffix) |
| Position gains | kp=998.22, kv=2.731 | **kp=17.8, kv=0** | kp=998.22 |
| Gripper units | Radian hinge | Radian hinge | **0~1 normalized** |
| Self-collision exclusion | None | None | Yes (6 pairs) |

**Measured tracking error**: the new-calibration model and the description package hold a static pose with 0.0005 rad error, while the old calibration shows 0.03 rad (about 1.7° of sag; kp is 56× weaker).
Evaluating the same policy in simulation with a different model yields different dynamics—note which one was used for recording.

## Model Behaviors to Remember

1. **The positive `shoulder_lift` direction points downward**: in the drive torque, a "downward swing" uses a positive angle; verify the sign before doing teleoperation mapping or data conversion.
2. **Hitting the ground blocks motion**: at the downward-swing limit, the fingertips contact the ground and are stopped (the script has a built-in 8 cm ground-clearance guard that automatically clips the amplitude).
3. The official model has no camera and no keyframe; a camera-equipped variant, `so101_new_calib_camera.xml`, exists and can be used for recording visual data later.
