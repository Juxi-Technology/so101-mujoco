# 08 · Roadmap

## Completed (runnable directly from this repository)

| Capability | Status |
| --- | --- |
| Simulation model loading/driving/rendering verification (3 MJCF models) | ✅ |
| Keyboard teleoperation (simulation / real hardware) | ✅ Verified on hardware |
| Leader-arm digital twin (physical arm → simulated arm, with zero-point trimming) | ✅ Verified on hardware |
| Data recording (hardware / simulation) + episode control + inspection script | ✅ Verified on hardware |
| Data replay (hardware / simulation, official mechanism) | ✅ Verified on hardware |
| Automated smoke tests (hardware-free `smoke_test.py`) | ✅ 26 passed |
| Dual-camera visual dataset `so101_sim_vision` (5 episodes / 10610 frames / 353.8s) | ✅ |
| Training (ACT) and simulated policy deployment (`lerobot-train` / `lerobot-rollout`) | ✅ Smoke-tested (see [09](09-usage-tutorial.md)) |

## Next Steps (ordered by value)

### Phase 2 · Cameras in the Scene (in progress)

**Completed**:
- The mount (STEP→STL) and camera (a placeholder body built from the HBVCAM-F2170HD V22 datasheet, 25×30×5.2mm) are assembled into the simulation,
  with poses adjusted against the real machine using `adjust_mount.py` / `adjust_camera.py`;
- The `<camera>` element is integrated (`sim_cam`, initial fovy 49°), and **the simulation visual-recording pipeline is working end to end**:
  `--robot.image_camera=sim_cam` produces a video dataset with `observation.images.wrist` (smoke test [5] fully passes).

**2026-10-16 update**: camera aiming/fovy has been tuned to satisfaction (`adjust_camera.py` gained a **live view real-time window**,
with resumable tuning and automatic reopening if the window is accidentally closed; also fixed the bug where MuJoCo's camera view direction = **element −Z** caused
"lens direction opposite to the image", see [07](07-troubleshooting.md)). A visual dataset has been officially recorded with the newly calibrated leader arm (with wrist video, tracking error ≤2 units) ✅;
the old experimental recordings were cleaned up on 2026-10-16, and the official dataset is now unified as `so101_sim_vision` (dual camera).
**On the same day the simulated robot was migrated to the mujoco_menagerie SO-ARM100 model** (2026-10-16): the original tutorial model's gripper cannot grasp,
while the new model's gripper uses real-machine CAD collision and was measured to grip a 34 mm cube reliably; recording/teleoperation/dual-camera/workspace pipelines are all retained,
pending one real-hardware teleoperation verification (especially the wrist_roll direction sign).
**Still to do**: after the real HBVCAM is connected, do a "real photos vs simulated renders" comparison fine-tune;
optional: replace the placeholder body with a camera STL. Real-machine camera configuration (`--robot.cameras` OpenCV) to be done as well later.

### Phase 3 · Scenes and Scale-Up (in progress)

- ✅ Workspace added to the scene (2026-10-16): mat + three colored cubes (34mm, graspable) + storage box + fixed top camera `top_cam`
  (defined in `so101_assets.add_workspace`, with render/benefit inspection tool `preview_workspace.py`); **the dual-camera (wrist+top)
  recording pipeline is working end to end** (`--robot.top_camera=top_cam`);
- **Automatic data generation**: scripted policies/RL run in simulation in batches overnight (no human in the loop), which is where the "tens of times the efficiency" comes from;
- Visual domain randomization (textures/lighting/camera jitter) to prepare for sim2real.

### Phase 4 · Training and Deployment

- ✅ **Training/deployment pipeline verified** (2026-10-16): `lerobot-train` (ACT, 12-step CPU smoke—about 2s/step, loss decreasing normally,
  checkpoint written to disk as expected) and `lerobot-rollout --strategy.type=base` (actually executing the policy in simulation for 20s,
  automatically returning the arm to the initial pose before finishing) both work end to end; full commands, key points, and resume-training instructions are in [09](09-usage-tutorial.md) sections 7/8,
  and the tutorial's bundled demo checkpoint `outputs/train/smoke_act` can be used directly to try out the deployment pipeline;
- Full training happens on a **GPU-equipped machine** (ACT / SmolVLA; this machine's CPU-only setup is suitable only for small-step pipeline validation);
  just copy the dataset or push it to a private HF repository;
- Real-hardware deployment also goes through `lerobot-rollout` (replace `--robot.*` with the `so101_follower` configuration).

### Long Term · sim2real

Mix simulation data + a small amount of real data for training → zero-cost evaluation on real hardware (policy success rates can be reproducibly evaluated in simulation).
Note: going straight from pure simulation data to the real robot (zero-shot transfer) is the hardest route; start with a "short loop" (train on real data → deploy on real hardware),
and layer in simulation gradually.

## Positioning in One Sentence

For teams that already have physical arms: simulation = **a development sandbox + demo material + a data multiplier**;
for prospective customers: simulation = **a hands-on tool for walking the entire workflow before buying**.
