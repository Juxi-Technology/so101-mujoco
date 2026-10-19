# 05 · Leader-Arm Digital Twin (Physical Arm Driving the Simulated Arm)

Drag the **physical leader arm** by hand and let the **simulated follower arm in the MuJoCo window** mirror it in real time—the right way to run digital-twin demos
and simulated data collection.

## Prerequisites

The leader arm is calibrated (see [03](03-hardware-calibration.md)); the serial port used here is `COM163` as an example.

## Command

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM163 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

- `--robot.type=so101_mujoco`: the controlled target is the simulated arm, and the window opens automatically;
- `--teleop.*`: the controlling device is the physical leader arm (read-only, never applies torque, zero risk to the leader arm);
- `--teleop.use_degrees=false`: **required**. Makes the units output by the leader arm (stroke-ratio convention) match those of the simulated arm.

Swapping `--robot.type` for `so101_follower --robot.port=COM172 --robot.id=juxi_so101 --robot.max_relative_target=5`
gives the standard kit setup of "physical leader arm → real follower arm"; the same leader-arm calibration applies.

## What If the Zero Point Is Off: Automatic Center Trimming (`so101_leader_trim`)

**Symptom**: the leader arm is posed at the "visually centered" position, but the simulated arm is off by a few degrees.

**Principle**: lerobot's normalized zero point is the **midpoint of the range recorded during calibration**, `(min+max)/2`; the
"mid-position pose" captured when Enter is pressed during calibration is recorded as the raw value 2048. Whenever a joint's mechanical stroke is itself asymmetric, the two "midpoints" are permanently offset by a fixed amount
(measured on servo #1: recorded range 776~3457, midpoint 2116, which differs from 2048 by 68 counts ≈ **5.6°**).
**Recalibration cannot remove this offset** (stroke asymmetry is determined by the mechanical structure); it must be compensated in software.

**Solution**: the `so101_leader_trim` plugin automatically computes each joint's compensation from the calibration file using the formula below and subtracts it in real time;
it follows recalibration automatically, with no manual tuning:

```
补偿ᵢ = (2048 − minᵢ) / (maxᵢ − minᵢ) × 200 − 100
```

Values measured as effective on this machine (printed in the startup log):

| Joint | Compensation (units) |
| --- | --- |
| shoulder_pan | −5.11 |
| shoulder_lift | −0.92 |
| elbow_flex | +2.54 |
| wrist_flex | +0.69 |

The remaining joints deviate by <0.05 and need no compensation; the gripper (0~100) and degree mode do not take part in trimming.

> Developer note: this plugin's `name` must stay `"so_leader"`—`name` is the lookup directory key for calibration files;
> a custom type name would make the calibration file unfindable and mistakenly trigger the recalibration flow.
