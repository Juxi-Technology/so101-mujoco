# 03 · Hardware Connection and Calibration

## Identifying the Serial Port

Plugging in the driver board with the CH343 chip makes a COM port appear; **the number changes when you unplug/replug or switch USB ports**, so confirm it before every connection:

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen python -c "import serial.tools.list_ports as lp; [print(p.device, '|', p.description, '|', p.hwid) for p in lp.comports()]"
```

## Step 1: Read-Only Initial Check (wiring/power/servo health check)

**Without writing anything**, ping each of the six servos in turn and then read voltage and temperature (torque state is left untouched):

```bash
uv run --frozen python examples/so101_mujoco/hardware_check.py --port COM163
```

Normal output looks like: six joint lines, temperatures of 20~30°C, torque 0 (arm free). **Voltage depends on the power supply**: about 11 V when the follower arm is on an external
power supply, and about 5 V when the leader arm is powered only from the driver board—if all six servos can be read, the wiring is fine. Missing servos or a model mismatch
cause an immediate error.

## Step 2: Calibration

Calibration writes "each joint's stroke range + mid-position reference" into the servo EEPROM and saves it to a local file; **the follower arm and the leader arm must each be calibrated once**.
The two arms' calibration files are stored separately and do not affect each other:

| Device | Command | Calibration file location |
| --- | --- | --- |
| Follower arm | `uv run --frozen lerobot-calibrate --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101` | `~/.cache/huggingface/lerobot/calibration/robots/so_follower/juxi_so101.json` |
| Leader arm | `uv run --frozen lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM163 --teleop.id=juxi_leader` | `.../calibration/teleoperators/so_leader/juxi_leader.json` |

The `id` can be any name, but **teleoperation/recording must use the same id afterwards**, otherwise you will be prompted to calibrate again.

### Physical Steps (the terminal prints a diagram)

1. **Pose the arm at the mid-position, then press Enter**: place the base flat at the edge of the desk, upper arm pointing straight up, forearm horizontal and forward, shoulder rotation and wrist centered
   (the leader arm's "gripper" is the handle/trigger). The position at this moment is recorded as that arm's "mid-position reference".
2. After pressing Enter, **slowly sweep each joint through its full range of motion** (`wrist_roll` does not need sweeping; it is automatically treated as a full turn), then press Enter to save.

Notes:

- During follower-arm calibration the torque is 0 (the arm is limp), so support it by hand; the leader arm has no torque anyway.
- Calibration writes to the servo EEPROM (this is part of calibration and is normal).
- Calibration results from this session (for reference): the follower arm's joint strokes span 1474~2688 counts, `wrist_roll` 4095;
  the leader arm 2208~2681 counts. Noticeably asymmetric strokes are normal (see [05 Zero-point Trimming](05-leader-digital-twin.md) for why this matters).
