#!/usr/bin/env python3
"""Render a quick shaded SVG preview of an OBJ mesh. Pure standard library.

Usage:
    python preview_svg.py model.obj [-o preview.svg] [--size 512] [--yaw 30] [--pitch 20]

Uses an orthographic projection with painter's-algorithm depth sorting and
simple Lambertian shading — good enough to sanity-check silhouettes and
proportions, not a physically accurate render.
"""

import argparse
import math
import os


def load_obj(path):
    vertices, faces = [], []
    with open(path) as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "v":
                vertices.append(tuple(float(p) for p in parts[1:4]))
            elif parts[0] == "f":
                idx = [int(p.split("/")[0]) - 1 for p in parts[1:]]
                for i in range(1, len(idx) - 1):  # fan-triangulate
                    faces.append((idx[0], idx[i], idx[i + 1]))
    return vertices, faces


def rotate(v, yaw, pitch):
    x, y, z = v
    cy, sy = math.cos(yaw), math.sin(yaw)
    x, z = x * cy + z * sy, -x * sy + z * cy
    cp, sp = math.cos(pitch), math.sin(pitch)
    y, z = y * cp - z * sp, y * sp + z * cp
    return (x, y, z)


def render(vertices, faces, size=512, yaw_deg=30.0, pitch_deg=20.0):
    rotated = [rotate(v, math.radians(yaw_deg), math.radians(pitch_deg)) for v in vertices]

    xs = [v[0] for v in rotated]
    ys = [v[1] for v in rotated]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    scale = size * 0.85 / span
    cx = (max(xs) + min(xs)) / 2.0
    cy = (max(ys) + min(ys)) / 2.0

    def project(v):
        return ((v[0] - cx) * scale + size / 2.0, size / 2.0 - (v[1] - cy) * scale)

    light = (0.408, 0.816, 0.408)  # normalized (1, 2, 1)
    polys = []
    for a, b, c in faces:
        va, vb, vc = rotated[a], rotated[b], rotated[c]
        ux, uy, uz = (vb[i] - va[i] for i in range(3))
        vx, vy, vz = (vc[i] - va[i] for i in range(3))
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        if nz <= 0:  # back-face cull (camera looks down -z)
            continue
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        lam = max(0.0, (nx * light[0] + ny * light[1] + nz * light[2]) / length)
        shade = int(60 + 180 * lam)
        depth = (va[2] + vb[2] + vc[2]) / 3.0
        polys.append((depth, [project(va), project(vb), project(vc)], shade))

    polys.sort(key=lambda p: p[0])  # far to near

    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
             f'viewBox="0 0 {size} {size}">',
             f'<rect width="{size}" height="{size}" fill="#1a1a2e"/>']
    for _, pts, shade in polys:
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        color = f"rgb({shade},{int(shade * 0.85)},{int(shade * 0.6)})"
        lines.append(f'<polygon points="{d}" fill="{color}" stroke="{color}" stroke-width="0.5"/>')
    lines.append("</svg>")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Render an OBJ mesh to an SVG preview")
    parser.add_argument("input", help="input .obj file")
    parser.add_argument("-o", "--output", help="output .svg (default: input name + .svg)")
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--yaw", type=float, default=30.0)
    parser.add_argument("--pitch", type=float, default=20.0)
    args = parser.parse_args()

    vertices, faces = load_obj(args.input)
    if not vertices or not faces:
        raise SystemExit(f"{args.input}: no mesh data found")
    svg = render(vertices, faces, args.size, args.yaw, args.pitch)
    out = args.output or os.path.splitext(args.input)[0] + ".svg"
    with open(out, "w") as f:
        f.write(svg)
    print(f"{out}: {len(faces)} triangles rendered")


if __name__ == "__main__":
    main()
