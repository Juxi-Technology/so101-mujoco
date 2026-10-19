"""Summarize a LeRobotDataset: per-episode frames, duration, action spans,
and action-vs-observation tracking error.

A quick health check after recording (works for both real-arm and sim datasets):

* ``action span`` — how far each joint moved in the episode (0 = static episode,
  usually a failed take);
* ``|action - obs|`` — how well the follower tracked the teleop targets; a big
  value on the first frames is the connect/converge transient, not an error.

Usage (from the repo root):

    uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
        --repo-id local/so101_sim_teleop \
        --root examples/so101_mujoco/outputs/datasets/sim_run2
"""

from __future__ import annotations

import argparse

import torch

from lerobot.datasets import LeRobotDataset

# Column order of the 6-dof vectors in SO-101 datasets.
JOINT_NAMES = ["pan", "lift", "elbow", "wflex", "wroll", "grip"]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo-id", required=True)
    p.add_argument("--root", required=True, help="dataset directory (root IS the dataset dir)")
    p.add_argument("--step", type=int, default=3, help="read every Nth frame (default 3)")
    args = p.parse_args()

    ds = LeRobotDataset(args.repo_id, root=args.root)
    print(f"repo_id={ds.repo_id} episodes={ds.num_episodes} frames={ds.num_frames} fps={ds.fps}")

    actions, obs, eps = [], [], []
    for i in range(0, len(ds), args.step):
        f = ds[i]
        actions.append(f["action"])
        obs.append(f["observation.state"])
        eps.append(int(f["episode_index"]))
    a = torch.stack(actions)
    o = torch.stack(obs)
    e = torch.tensor(eps)

    for ep in e.unique().tolist():
        m = e == ep
        n = int(m.sum()) * args.step
        aspan = (a[m].max(0).values - a[m].min(0).values).tolist()
        track = (a[m] - o[m]).abs().max(0).values.tolist()
        print(f"ep{ep}: ~{n} frames ({n / ds.fps:.1f}s)")
        print("  action span    : " + " ".join(f"{k}={v:.0f}" for k, v in zip(JOINT_NAMES, aspan)))
        print("  max |act-obs|  : " + " ".join(f"{k}={v:.1f}" for k, v in zip(JOINT_NAMES, track)))

    tasks = {ds[i].get("task") for i in range(0, len(ds), max(1, len(ds) // 10))}
    print("task(s):", tasks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
