"""Convert a STEP/CAD file to STL using gmsh's OpenCASCADE kernel.

Reusable for any Juxi CAD asset that needs to go into a MuJoCo scene: STEP
files (e.g. Pro/E exports) are tessellated into a surface mesh and written as
binary STL, in the *source units* (millimeters for most CAD exports) -- use
``scale="0.001 0.001 0.001"`` on the ``<mesh>`` element in MJCF.

Usage (from the repo root):

    uv run --frozen --with gmsh python examples/so101_mujoco/step_to_stl.py \
        --input examples/so101_mujoco/assets/camera/arm_mount_bracket_v3.step \
        --output examples/so101_mujoco/assets/camera/mesh/arm_mount_bracket_v3.stl
"""

from __future__ import annotations

import argparse
from pathlib import Path

import gmsh


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", required=True, help="source CAD file (.step/.stp/...)")
    p.add_argument("--output", required=True, help="destination .stl")
    p.add_argument(
        "--deflection",
        type=float,
        default=0.4,
        help="tessellation size in source units (mm); smaller = finer mesh (default 0.4)",
    )
    args = p.parse_args()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.open(args.input)
        gmsh.option.setNumber("Mesh.MeshSizeMin", args.deflection)
        gmsh.option.setNumber("Mesh.MeshSizeMax", args.deflection * 5)
        gmsh.option.setNumber("Mesh.Binary", 1)
        gmsh.model.mesh.generate(2)  # surface mesh only (enough for rendering/collision)
        gmsh.write(str(out))
    finally:
        gmsh.finalize()

    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
