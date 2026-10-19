"""Export a LeRobotDataset recording as per-episode playable videos plus a
two-camera preview strip.

LeRobotDataset v3 packs all of one camera's episodes into a single mp4
(episodes concatenated in order), which makes casual viewing awkward. This
tool decodes that packed file once per camera and writes:

* ``outputs/videos/<dataset>/ep<N>_<cam>.mp4`` -- one playable h264 file per
  episode per camera, same fps;
* ``outputs/renders/<dataset>_ep<N>_dual.png`` -- a strip of evenly spaced
  frames (top row = overhead ``observation.images.top``, bottom row = wrist
  ``observation.images.wrist``) for a quick eyeball check (``--no-strips``
  skips it).

Assumes the small-dataset layout where each camera's frames live in one packed
file; anything else is rejected with a clear error.

Usage (from the repo root):

    uv run --frozen python examples/so101_mujoco/export_videos.py \
        --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import av
import numpy as np
import pyarrow.parquet as pq
from PIL import Image, ImageDraw

CAMS = {"top": "observation.images.top", "wrist": "observation.images.wrist"}
STRIP_W, STRIP_H = 320, 240


def _open_writer(path: Path, fps: int):
    container = av.open(str(path), "w")
    stream = container.add_stream("h264", rate=fps)
    # pyav 15 requires string option values (same as lerobot's as_strings=True).
    stream.options = {"g": "30", "crf": "26", "preset": "veryfast"}
    stream.width, stream.height, stream.pix_fmt = 640, 480, "yuv420p"
    return container, stream


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", required=True, help="dataset directory (root IS the dataset dir)")
    p.add_argument("--strip-count", type=int, default=6, help="frames per episode in the preview strip")
    p.add_argument("--no-strips", action="store_true", help="only export the per-episode videos")
    args = p.parse_args()

    root = Path(args.root).resolve()
    here = Path(__file__).resolve().parent
    out_v = here / "outputs" / "videos" / root.name
    out_r = here / "outputs" / "renders"
    out_v.mkdir(parents=True, exist_ok=True)

    fps = int(json.loads((root / "meta/info.json").read_text())["fps"])
    t = pq.read_table(
        sorted(root.glob("meta/episodes/chunk-*/*.parquet"))[0],
        columns=["episode_index", "length"],
    )
    lengths = [
        int(n)
        for _, n in sorted(zip(t["episode_index"].to_pylist(), t["length"].to_pylist()))
    ]
    print(f"{root.name}: {len(lengths)} episodes, {sum(lengths)} frames, fps={fps}")

    strips: dict[str, list[Image.Image]] = {}
    for cam_short, cam_key in CAMS.items():
        vids = sorted((root / "videos" / cam_key / "chunk-000").glob("file-*.mp4"))
        if len(vids) != 1:
            raise SystemExit(
                f"{cam_key}: expected one packed mp4, found {len(vids)}; "
                "this tool only handles small single-file datasets"
            )
        samples = {
            e: {int((k + 0.5) * n / args.strip_count) for k in range(args.strip_count)}
            for e, n in enumerate(lengths)
        }
        cam_strips: list[Image.Image] = []
        ep, remaining, consumed = 0, lengths[0], 0
        container = stream = None
        seg: dict[int, np.ndarray] = {}
        seen = 0
        with av.open(str(vids[0])) as src:
            for frame in src.decode(video=0):
                if container is None:
                    container, stream = _open_writer(out_v / f"ep{ep}_{cam_short}.mp4", fps)
                    seg = {}
                arr = frame.to_ndarray(format="rgb24")
                if consumed in samples[ep]:
                    seg[consumed] = arr
                for pkt in stream.encode(av.VideoFrame.from_ndarray(arr, format="rgb24")):
                    container.mux(pkt)
                seen += 1
                consumed += 1
                remaining -= 1
                if remaining == 0:
                    for pkt in stream.encode():
                        container.mux(pkt)
                    container.close()
                    container = stream = None
                    if not args.no_strips:
                        imgs = [
                            Image.fromarray(seg[k]).resize((STRIP_W, STRIP_H))
                            for k in sorted(seg)
                        ]
                        canvas = Image.new(
                            "RGB",
                            (STRIP_W * len(imgs) + 4 * (len(imgs) - 1), STRIP_H),
                            (255, 255, 255),
                        )
                        for j, im in enumerate(imgs):
                            canvas.paste(im, (j * (STRIP_W + 4), 0))
                        draw = ImageDraw.Draw(canvas)
                        draw.rectangle((0, 0, 82, 16), fill=(0, 0, 0))
                        draw.text((4, 2), f"ep{ep} · {cam_short}", fill=(255, 255, 0))
                        cam_strips.append(canvas)
                    ep += 1
                    consumed = 0
                    if ep < len(lengths):
                        remaining = lengths[ep]
        if ep != len(lengths) or seen != sum(lengths):
            raise SystemExit(
                f"{cam_key}: decoded {seen} frames across {ep} episodes, "
                f"expected {sum(lengths)} / {len(lengths)}"
            )
        strips[cam_short] = cam_strips
        print(f"  {cam_short}: {seen} frames -> {len(cam_strips)} episode mp4s")

    if not args.no_strips:
        width = max(s.width for s in strips["top"])
        for e in range(len(lengths)):
            top, wrist = strips["top"][e], strips["wrist"][e]
            combo = Image.new("RGB", (width, top.height + wrist.height + 6), (255, 255, 255))
            combo.paste(top, (0, 0))
            combo.paste(wrist, (0, top.height + 6))
            combo.save(out_r / f"{root.name}_ep{e}_dual.png")
        print(f"strips -> {out_r}")

    print(f"videos -> {out_v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
