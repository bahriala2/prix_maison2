#!/usr/bin/env python3
"""Procedural 3D asset generator.

Generates parametric primitive meshes and exports them as OBJ, STL (ASCII)
or PLY (ASCII). Pure standard library — no third-party dependencies.

Usage examples:
    python generate_asset.py cube --size 2 -o cube.obj
    python generate_asset.py sphere --radius 1.5 --segments 48 --rings 24 -o ball.stl
    python generate_asset.py cylinder --radius 0.5 --height 3 -o pillar.obj
    python generate_asset.py cone --radius 1 --height 2 -o cone.ply
    python generate_asset.py torus --major-radius 2 --minor-radius 0.5 -o donut.obj
    python generate_asset.py plane --width 10 --depth 10 --subdivisions 8 -o ground.obj

The output format is inferred from the file extension (.obj, .stl, .ply).
Coordinate system: Y-up, right-handed. Faces are triangles with
counter-clockwise winding (outward normals).
"""

import argparse
import math
import os
import sys

Vec3 = tuple  # (x, y, z)


# ---------------------------------------------------------------------------
# Primitive generators — each returns (vertices, faces) where vertices is a
# list of (x, y, z) floats and faces is a list of (i, j, k) vertex indices.
# ---------------------------------------------------------------------------

def make_cube(size_x=1.0, size_y=1.0, size_z=1.0):
    hx, hy, hz = size_x / 2.0, size_y / 2.0, size_z / 2.0
    vertices = [
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
    ]
    quads = [
        (0, 3, 2, 1),  # back  (-z)
        (4, 5, 6, 7),  # front (+z)
        (0, 1, 5, 4),  # bottom (-y)
        (2, 3, 7, 6),  # top (+y)
        (0, 4, 7, 3),  # left (-x)
        (1, 2, 6, 5),  # right (+x)
    ]
    faces = []
    for a, b, c, d in quads:
        faces.append((a, b, c))
        faces.append((a, c, d))
    return vertices, faces


def make_sphere(radius=1.0, segments=32, rings=16):
    if segments < 3 or rings < 2:
        raise ValueError("sphere needs segments >= 3 and rings >= 2")
    vertices = [(0.0, radius, 0.0)]  # top pole
    for r in range(1, rings):
        phi = math.pi * r / rings
        y = radius * math.cos(phi)
        ring_r = radius * math.sin(phi)
        for s in range(segments):
            theta = 2.0 * math.pi * s / segments
            vertices.append((ring_r * math.cos(theta), y, ring_r * math.sin(theta)))
    vertices.append((0.0, -radius, 0.0))  # bottom pole
    bottom = len(vertices) - 1

    def ring_index(r, s):
        return 1 + (r - 1) * segments + (s % segments)

    faces = []
    for s in range(segments):  # top cap
        faces.append((0, ring_index(1, s + 1), ring_index(1, s)))
    for r in range(1, rings - 1):  # body
        for s in range(segments):
            a = ring_index(r, s)
            b = ring_index(r, s + 1)
            c = ring_index(r + 1, s + 1)
            d = ring_index(r + 1, s)
            faces.append((a, b, c))
            faces.append((a, c, d))
    for s in range(segments):  # bottom cap
        faces.append((bottom, ring_index(rings - 1, s), ring_index(rings - 1, s + 1)))
    return vertices, faces


def make_cylinder(radius=1.0, height=2.0, segments=32, capped=True):
    if segments < 3:
        raise ValueError("cylinder needs segments >= 3")
    h = height / 2.0
    vertices = []
    for y in (h, -h):
        for s in range(segments):
            theta = 2.0 * math.pi * s / segments
            vertices.append((radius * math.cos(theta), y, radius * math.sin(theta)))
    faces = []
    for s in range(segments):  # side wall
        a = s
        b = (s + 1) % segments
        c = segments + (s + 1) % segments
        d = segments + s
        faces.append((a, b, c))
        faces.append((a, c, d))
    if capped:
        top_center = len(vertices)
        vertices.append((0.0, h, 0.0))
        bottom_center = len(vertices)
        vertices.append((0.0, -h, 0.0))
        for s in range(segments):
            faces.append((top_center, (s + 1) % segments, s))
            faces.append((bottom_center, segments + s, segments + (s + 1) % segments))
    return vertices, faces


def make_cone(radius=1.0, height=2.0, segments=32, capped=True):
    if segments < 3:
        raise ValueError("cone needs segments >= 3")
    h = height / 2.0
    vertices = [(0.0, h, 0.0)]  # apex
    for s in range(segments):
        theta = 2.0 * math.pi * s / segments
        vertices.append((radius * math.cos(theta), -h, radius * math.sin(theta)))
    faces = []
    for s in range(segments):  # sloped side
        a = 1 + s
        b = 1 + (s + 1) % segments
        faces.append((0, b, a))
    if capped:
        center = len(vertices)
        vertices.append((0.0, -h, 0.0))
        for s in range(segments):
            a = 1 + s
            b = 1 + (s + 1) % segments
            faces.append((center, a, b))
    return vertices, faces


def make_torus(major_radius=2.0, minor_radius=0.5, major_segments=32, minor_segments=16):
    if major_segments < 3 or minor_segments < 3:
        raise ValueError("torus needs major_segments >= 3 and minor_segments >= 3")
    vertices = []
    for i in range(major_segments):
        u = 2.0 * math.pi * i / major_segments
        cu, su = math.cos(u), math.sin(u)
        for j in range(minor_segments):
            v = 2.0 * math.pi * j / minor_segments
            cv, sv = math.cos(v), math.sin(v)
            x = (major_radius + minor_radius * cv) * cu
            z = (major_radius + minor_radius * cv) * su
            y = minor_radius * sv
            vertices.append((x, y, z))
    faces = []
    for i in range(major_segments):
        for j in range(minor_segments):
            a = i * minor_segments + j
            b = i * minor_segments + (j + 1) % minor_segments
            c = ((i + 1) % major_segments) * minor_segments + (j + 1) % minor_segments
            d = ((i + 1) % major_segments) * minor_segments + j
            faces.append((a, b, c))
            faces.append((a, c, d))
    return vertices, faces


def make_plane(width=1.0, depth=1.0, subdivisions=1):
    if subdivisions < 1:
        raise ValueError("plane needs subdivisions >= 1")
    n = subdivisions
    vertices = []
    for iz in range(n + 1):
        for ix in range(n + 1):
            x = -width / 2.0 + width * ix / n
            z = -depth / 2.0 + depth * iz / n
            vertices.append((x, 0.0, z))
    faces = []
    for iz in range(n):
        for ix in range(n):
            a = iz * (n + 1) + ix
            b = a + 1
            c = a + (n + 1) + 1
            d = a + (n + 1)
            faces.append((a, c, b))
            faces.append((a, d, c))
    return vertices, faces


PRIMITIVES = {
    "cube": make_cube,
    "sphere": make_sphere,
    "cylinder": make_cylinder,
    "cone": make_cone,
    "torus": make_torus,
    "plane": make_plane,
}


# ---------------------------------------------------------------------------
# Mesh utilities
# ---------------------------------------------------------------------------

def face_normal(vertices, face):
    (ax, ay, az) = vertices[face[0]]
    (bx, by, bz) = vertices[face[1]]
    (cx, cy, cz) = vertices[face[2]]
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length == 0.0:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def transform(vertices, scale=1.0, translate=(0.0, 0.0, 0.0)):
    tx, ty, tz = translate
    return [(x * scale + tx, y * scale + ty, z * scale + tz) for x, y, z in vertices]


# ---------------------------------------------------------------------------
# Exporters
# ---------------------------------------------------------------------------

def write_obj(path, vertices, faces, name="asset"):
    with open(path, "w") as f:
        f.write(f"# Generated by 3d-asset-generator\no {name}\n")
        for x, y, z in vertices:
            f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        for a, b, c in faces:
            f.write(f"f {a + 1} {b + 1} {c + 1}\n")


def write_stl(path, vertices, faces, name="asset"):
    with open(path, "w") as f:
        f.write(f"solid {name}\n")
        for face in faces:
            nx, ny, nz = face_normal(vertices, face)
            f.write(f"  facet normal {nx:.6f} {ny:.6f} {nz:.6f}\n")
            f.write("    outer loop\n")
            for idx in face:
                x, y, z = vertices[idx]
                f.write(f"      vertex {x:.6f} {y:.6f} {z:.6f}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write(f"endsolid {name}\n")


def write_ply(path, vertices, faces):
    with open(path, "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write("comment Generated by 3d-asset-generator\n")
        f.write(f"element vertex {len(vertices)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write(f"element face {len(faces)}\n")
        f.write("property list uchar int vertex_indices\n")
        f.write("end_header\n")
        for x, y, z in vertices:
            f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")
        for a, b, c in faces:
            f.write(f"3 {a} {b} {c}\n")


WRITERS = {".obj": write_obj, ".stl": write_stl, ".ply": write_ply}


def export(path, vertices, faces, name="asset"):
    ext = os.path.splitext(path)[1].lower()
    writer = WRITERS.get(ext)
    if writer is None:
        raise ValueError(f"unsupported format '{ext}' (use .obj, .stl or .ply)")
    if writer is write_ply:
        writer(path, vertices, faces)
    else:
        writer(path, vertices, faces, name=name)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(description="Generate parametric 3D primitive meshes")
    parser.add_argument("-o", "--output", required=True,
                        help="output file (.obj, .stl or .ply)")
    parser.add_argument("--scale", type=float, default=1.0, help="uniform scale factor")
    parser.add_argument("--translate", type=float, nargs=3, default=(0.0, 0.0, 0.0),
                        metavar=("X", "Y", "Z"), help="translation applied after scaling")
    sub = parser.add_subparsers(dest="shape", required=True)

    p = sub.add_parser("cube", help="axis-aligned box")
    p.add_argument("--size", type=float, default=None, help="uniform edge length")
    p.add_argument("--size-x", type=float, default=1.0)
    p.add_argument("--size-y", type=float, default=1.0)
    p.add_argument("--size-z", type=float, default=1.0)

    p = sub.add_parser("sphere", help="UV sphere")
    p.add_argument("--radius", type=float, default=1.0)
    p.add_argument("--segments", type=int, default=32)
    p.add_argument("--rings", type=int, default=16)

    p = sub.add_parser("cylinder", help="capped cylinder")
    p.add_argument("--radius", type=float, default=1.0)
    p.add_argument("--height", type=float, default=2.0)
    p.add_argument("--segments", type=int, default=32)
    p.add_argument("--open", action="store_true", help="omit end caps")

    p = sub.add_parser("cone", help="capped cone")
    p.add_argument("--radius", type=float, default=1.0)
    p.add_argument("--height", type=float, default=2.0)
    p.add_argument("--segments", type=int, default=32)
    p.add_argument("--open", action="store_true", help="omit base cap")

    p = sub.add_parser("torus", help="torus (donut)")
    p.add_argument("--major-radius", type=float, default=2.0)
    p.add_argument("--minor-radius", type=float, default=0.5)
    p.add_argument("--major-segments", type=int, default=32)
    p.add_argument("--minor-segments", type=int, default=16)

    p = sub.add_parser("plane", help="subdivided flat plane (Y=0)")
    p.add_argument("--width", type=float, default=1.0)
    p.add_argument("--depth", type=float, default=1.0)
    p.add_argument("--subdivisions", type=int, default=1)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.shape == "cube":
        if args.size is not None:
            vertices, faces = make_cube(args.size, args.size, args.size)
        else:
            vertices, faces = make_cube(args.size_x, args.size_y, args.size_z)
    elif args.shape == "sphere":
        vertices, faces = make_sphere(args.radius, args.segments, args.rings)
    elif args.shape == "cylinder":
        vertices, faces = make_cylinder(args.radius, args.height, args.segments,
                                        capped=not args.open)
    elif args.shape == "cone":
        vertices, faces = make_cone(args.radius, args.height, args.segments,
                                    capped=not args.open)
    elif args.shape == "torus":
        vertices, faces = make_torus(args.major_radius, args.minor_radius,
                                     args.major_segments, args.minor_segments)
    elif args.shape == "plane":
        vertices, faces = make_plane(args.width, args.depth, args.subdivisions)
    else:  # unreachable: argparse enforces the choices
        raise SystemExit(f"unknown shape {args.shape}")

    vertices = transform(vertices, scale=args.scale, translate=tuple(args.translate))
    export(args.output, vertices, faces, name=args.shape)
    print(f"{args.output}: {len(vertices)} vertices, {len(faces)} triangles")


if __name__ == "__main__":
    main()
