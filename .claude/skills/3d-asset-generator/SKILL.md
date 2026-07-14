---
name: 3d-asset-generator
description: Generate 3D assets (OBJ, STL, PLY meshes) procedurally with Python. Use when the user asks to create, generate, or export a 3D model, mesh, primitive shape, or printable/game-ready asset — e.g. "make me a 3D cube", "generate an STL of a torus", "create a low-poly sphere".
---

# 3D Asset Generator

Generate 3D mesh assets from the command line using the bundled, dependency-free
Python scripts. Everything runs on the standard library — no pip installs needed.

## Quick start: primitive shapes

Use `scripts/generate_asset.py` for any of the six built-in primitives.
The output format is inferred from the file extension (`.obj`, `.stl`, `.ply`).

```bash
python scripts/generate_asset.py -o cube.obj cube --size 2
python scripts/generate_asset.py -o ball.stl sphere --radius 1.5 --segments 48 --rings 24
python scripts/generate_asset.py -o pillar.obj cylinder --radius 0.5 --height 3
python scripts/generate_asset.py -o spike.ply cone --radius 1 --height 2
python scripts/generate_asset.py -o donut.obj torus --major-radius 2 --minor-radius 0.5
python scripts/generate_asset.py -o ground.obj plane --width 10 --depth 10 --subdivisions 8
```

Global options (place BEFORE the shape name): `--scale F` and `--translate X Y Z`.
Run `python scripts/generate_asset.py --help` (or `<shape> --help`) for all parameters.

Conventions: Y-up, right-handed coordinates; triangles with counter-clockwise
winding and outward normals. All primitives except `plane` and `--open`
cylinders/cones are watertight, so STL exports are 3D-print ready.

## Preview a result

Render a shaded SVG preview (no 3D viewer or GPU needed) and show it to the user:

```bash
python scripts/preview_svg.py model.obj -o preview.svg --yaw 30 --pitch 20
```

Always generate a preview after creating an asset and send it to the user
alongside the mesh file so they can verify the shape without opening a 3D tool.

## Composite and custom shapes

For anything beyond a single primitive (a snowman, a table, a house, an
extruded profile, terrain), import the module in a short Python script instead
of shelling out repeatedly:

```python
import sys
sys.path.insert(0, "scripts")  # adjust to the skill's scripts/ directory
from generate_asset import (make_cube, make_sphere, make_cylinder, make_cone,
                            make_torus, make_plane, transform, export)

parts = []
def add(vertices, faces, scale=1.0, translate=(0, 0, 0)):
    offset = sum(len(v) for v, _ in parts) if parts else 0
    parts.append((transform(vertices, scale, translate),
                  [(a + offset, b + offset, c + offset) for a, b, c in faces]))

# Example: snowman = three stacked spheres
add(*make_sphere(1.0), translate=(0, 0.0, 0))
add(*make_sphere(0.7), translate=(0, 1.3, 0))
add(*make_sphere(0.45), translate=(0, 2.2, 0))

vertices = [v for vs, _ in parts for v in vs]
faces = [f for _, fs in parts for f in fs]
export("snowman.obj", vertices, faces, name="snowman")
```

For fully custom geometry (parametric surfaces, lathed profiles, heightmap
terrain), build the `vertices`/`faces` lists directly in Python and call
`export()` — keep counter-clockwise winding for outward-facing normals.

## Choosing a format

- **OBJ** — widest tool support (Blender, Unity, three.js). Default choice.
- **STL** — 3D printing. Use only watertight meshes.
- **PLY** — point-cloud/mesh processing pipelines (MeshLab, Open3D).

If the user needs glTF/GLB or textures/materials, generate an OBJ first and
tell them to convert in Blender (`File > Import > OBJ`, then export), or use
`trimesh` if it is already installed — do not pip-install anything without asking.

## Workflow checklist

1. Clarify (or infer) dimensions, polygon budget, and target format.
2. Generate the mesh with the CLI or a composite script.
3. Render an SVG preview and share both files with the user.
4. Report vertex/triangle counts and note whether the mesh is watertight.
