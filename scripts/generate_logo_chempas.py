#!/usr/bin/env python3
"""Generate 3D sphere logo for CheMPAS using NSF NCAR brand colors.

Seven hexagons on a sphere with shared geodesic edges, gnomonic
projection, smooth Blinn-Phong shading. Two variants: icon-only
and with "CheMPAS" text.

Color palette from NSF NCAR brand guidelines:
  space:     #011837
  dark_blue: #00357A
  ncar_blue: #0A5DDA
  aqua:      #00A2B4
  light_blue:#CEDFF8
  orange:    #FF8C00
"""

import math
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# Vector math
# ---------------------------------------------------------------------------

def normalize(v):
    n = math.sqrt(sum(c * c for c in v))
    return (v[0] / n, v[1] / n, v[2] / n) if n > 1e-12 else (0, 0, 0)

def add3(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def sub3(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def scale3(v, s):
    return (v[0] * s, v[1] * s, v[2] * s)

def dot3(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

def cross3(a, b):
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])

def slerp(a, b, t):
    d = max(-1.0, min(1.0, dot3(a, b)))
    omega = math.acos(d)
    if omega < 1e-10:
        return normalize(add3(scale3(a, 1 - t), scale3(b, t)))
    so = math.sin(omega)
    return normalize(add3(scale3(a, math.sin((1 - t) * omega) / so),
                          scale3(b, math.sin(t * omega) / so)))


# ---------------------------------------------------------------------------
# 3D rotation
# ---------------------------------------------------------------------------

def make_rotation(rx, ry):
    ca, sa = math.cos(rx), math.sin(rx)
    cb, sb = math.cos(ry), math.sin(ry)
    def rot(v):
        x, y, z = v
        y, z = ca * y - sa * z, sa * y + ca * z
        x, z = cb * x + sb * z, -sb * x + cb * z
        return (x, y, z)
    return rot


# ---------------------------------------------------------------------------
# Hex tiling → sphere via gnomonic projection
# ---------------------------------------------------------------------------

def gnomonic_to_sphere(x, y):
    return normalize((x, y, 1.0))


def build_hex_tiling(alpha=0.38):
    r = math.tan(alpha)
    sqrt3 = math.sqrt(3)

    all_verts_2d = []
    vert_map = {}

    def add_vert(x, y):
        key = (round(x, 8), round(y, 8))
        if key not in vert_map:
            vert_map[key] = len(all_verts_2d)
            all_verts_2d.append((x, y))
        return vert_map[key]

    centers_2d = [(0.0, 0.0)]
    for k in range(6):
        angle = math.radians(30 + k * 60)
        centers_2d.append((sqrt3 * r * math.cos(angle),
                           sqrt3 * r * math.sin(angle)))

    faces = []
    for cx, cy in centers_2d:
        face = []
        for k in range(6):
            angle = k * math.pi / 3
            face.append(add_vert(cx + r * math.cos(angle),
                                 cy + r * math.sin(angle)))
        faces.append(face)

    verts_3d = [gnomonic_to_sphere(x, y) for x, y in all_verts_2d]
    centers_3d = [gnomonic_to_sphere(x, y) for x, y in centers_2d]

    return verts_3d, faces, centers_3d


# ---------------------------------------------------------------------------
# Subdivision for smooth shading
# ---------------------------------------------------------------------------

def subdivide_tri_on_sphere(v0, v1, v2, n):
    grid = {}
    for i in range(n + 1):
        for j in range(n - i + 1):
            k = n - i - j
            pt = add3(add3(scale3(v0, i / n), scale3(v1, j / n)),
                      scale3(v2, k / n))
            grid[(i, j)] = normalize(pt)
    tris = []
    for i in range(n):
        for j in range(n - i):
            tris.append((grid[(i, j)], grid[(i + 1, j)], grid[(i, j + 1)]))
            if i + j < n - 1:
                tris.append((grid[(i + 1, j)], grid[(i + 1, j + 1)],
                             grid[(i, j + 1)]))
    return tris


def subdivide_hex_on_sphere(center_3d, corners_3d, n=5):
    all_tris = []
    for k in range(6):
        all_tris.extend(subdivide_tri_on_sphere(
            center_3d, corners_3d[k], corners_3d[(k + 1) % 6], n))
    return all_tris


# ---------------------------------------------------------------------------
# Geodesic arc
# ---------------------------------------------------------------------------

def geodesic_arc(a, b, n_seg=16):
    return [slerp(a, b, t / n_seg) for t in range(n_seg + 1)]


# ---------------------------------------------------------------------------
# Lighting & color
# ---------------------------------------------------------------------------

def lerp_color(c1, c2, t):
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    t = max(0.0, min(1.0, t))
    return "#{:02x}{:02x}{:02x}".format(
        int(r1 + (r2 - r1) * t), int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t))


def shade(normal, light_dir, view_dir, ambient, palette):
    dark, mid, bright = palette
    ndotl = max(0.0, dot3(normal, light_dir))
    intensity = ambient + (1 - ambient) * ndotl
    half_v = normalize(add3(light_dir, view_dir))
    spec = 0.3 * max(0.0, dot3(normal, half_v)) ** 20
    intensity = min(1.0, intensity + spec)
    if intensity < 0.5:
        return lerp_color(dark, mid, intensity * 2)
    else:
        return lerp_color(mid, bright, (intensity - 0.5) * 2)


# ---------------------------------------------------------------------------
# SVG builder
# ---------------------------------------------------------------------------

def build_svg(width=512, text_mode="chempas", color_scheme="blue"):
    W = width
    icon_h = W * 0.85
    H = icon_h
    scr_cx, scr_cy = W / 2, icon_h / 2
    proj_scale = W * 0.38

    # --- NSF NCAR brand palette --------------------------------------------
    space      = "#011837"
    dark_blue  = "#00357A"
    ncar_blue  = "#0A5DDA"
    aqua       = "#00A2B4"
    light_blue = "#CEDFF8"
    orange     = "#FF8C00"

    # Aqua shades
    dark_aqua  = "#005A66"
    deep_aqua  = "#007A8A"
    light_aqua = "#B0E8F0"

    if color_scheme == "aqua":
        face_palette = (dark_aqua, aqua, light_aqua)
        edge_dark = dark_aqua
        edge_light = deep_aqua
    else:
        face_palette = (space, ncar_blue, light_blue)
        edge_dark = space
        edge_light = dark_blue

    light_dir = normalize((0.55, 0.75, 0.85))
    view_dir = (0, 0, 1)
    ambient = 0.12

    rot = make_rotation(0.40, 0.28)

    def proj(v):
        return (scr_cx + v[0] * proj_scale, scr_cy - v[1] * proj_scale)

    # --- Geometry ----------------------------------------------------------
    verts_3d, faces, centers_3d = build_hex_tiling(alpha=0.38)

    sub_div = 5
    all_tris = []
    for hi, face in enumerate(faces):
        corners = [verts_3d[i] for i in face]
        for tri in subdivide_hex_on_sphere(centers_3d[hi], corners, n=sub_div):
            all_tris.append((*tri, hi))

    edge_set = set()
    edge_arcs = []
    for face in faces:
        for k in range(6):
            a, b = face[k], face[(k + 1) % 6]
            key = (min(a, b), max(a, b))
            if key not in edge_set:
                edge_set.add(key)
                edge_arcs.append(
                    geodesic_arc(verts_3d[a], verts_3d[b], 16))

    # --- Rotate & cull -----------------------------------------------------
    rotated_tris = []
    for v0, v1, v2, hi in all_tris:
        rv0, rv1, rv2 = rot(v0), rot(v1), rot(v2)
        centroid_z = (rv0[2] + rv1[2] + rv2[2]) / 3
        n = normalize(add3(add3(v0, v1), v2))
        rn = rot(n)
        if rn[2] < -0.02:
            continue
        rotated_tris.append((rv0, rv1, rv2, rn, centroid_z, hi))
    rotated_tris.sort(key=lambda t: t[4])

    # --- SVG root (viewBox updated at the end) --------------------------------
    bbox_pts = []  # collect all content coordinates for tight viewBox

    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": "0 0 1 1",  # placeholder, updated at end
        "width": str(W),
    })
    defs = ET.SubElement(svg, "defs")

    # Radial gradients for space-filling atoms
    # Carbon: dark gray sphere
    cg = ET.SubElement(defs, "radialGradient", {
        "id": "carbonGrad", "cx": "35%", "cy": "30%", "r": "65%",
    })
    ET.SubElement(cg, "stop", offset="0%", style="stop-color:#666666")
    ET.SubElement(cg, "stop", offset="100%", style="stop-color:#1a1a1a")

    # Hydrogen: white/light gray sphere
    hg = ET.SubElement(defs, "radialGradient", {
        "id": "hydrogenGrad", "cx": "35%", "cy": "30%", "r": "65%",
    })
    ET.SubElement(hg, "stop", offset="0%", style="stop-color:#ffffff")
    ET.SubElement(hg, "stop", offset="100%", style="stop-color:#aaaaaa")

    # Oxygen: CPK red sphere (using NCAR red #D62839)
    og = ET.SubElement(defs, "radialGradient", {
        "id": "oxygenGrad", "cx": "35%", "cy": "30%", "r": "65%",
    })
    ET.SubElement(og, "stop", offset="0%", style="stop-color:#FFB040")
    ET.SubElement(og, "stop", offset="100%", style="stop-color:#CC7000")

    # Nitrogen: blue for blue theme, aqua for aqua theme
    ng = ET.SubElement(defs, "radialGradient", {
        "id": "nitrogenGrad", "cx": "35%", "cy": "30%", "r": "65%",
    })
    if color_scheme == "aqua":
        ET.SubElement(ng, "stop", offset="0%", style="stop-color:#40D0E0")
        ET.SubElement(ng, "stop", offset="100%", style="stop-color:#005A66")
    else:
        ET.SubElement(ng, "stop", offset="0%", style="stop-color:#4A9AFF")
        ET.SubElement(ng, "stop", offset="100%", style="stop-color:#053080")

    # Shadow
    rg = ET.SubElement(defs, "radialGradient", {"id": "shadow"})
    ET.SubElement(rg, "stop", offset="0%", style="stop-color:#000;stop-opacity:0.06")
    ET.SubElement(rg, "stop", offset="100%", style="stop-color:#000;stop-opacity:0")
    ET.SubElement(svg, "ellipse", {
        "cx": str(scr_cx), "cy": f"{scr_cy + proj_scale * 0.92:.1f}",
        "rx": f"{proj_scale * 0.6:.1f}", "ry": f"{proj_scale * 0.10:.1f}",
        "fill": "url(#shadow)",
    })

    # --- Draw hex faces as flat-shaded polygons with geodesic edges ----------
    # Each hex gets a single fill color based on its center normal
    hex_faces_render = []
    for hi, face in enumerate(faces):
        rc = rot(centers_3d[hi])
        rn = normalize(rc)  # sphere normal = position on unit sphere
        if rn[2] < -0.02:
            continue
        # Build geodesic outline: subdivide each edge into arcs
        outline = []
        for k in range(6):
            a, b = verts_3d[face[k]], verts_3d[face[(k + 1) % 6]]
            arc = [slerp(a, b, t / 12) for t in range(12)]
            outline.extend(arc)
        outline_rot = [rot(p) for p in outline]
        outline_2d = [proj(p) for p in outline_rot]
        fill = shade(rn, light_dir, view_dir, ambient, face_palette)
        hex_faces_render.append((rc[2], outline_2d, fill))
        bbox_pts.extend(outline_2d)

    hex_faces_render.sort(key=lambda x: x[0])

    for _, outline_2d, fill in hex_faces_render:
        d = f"M {outline_2d[0][0]:.1f} {outline_2d[0][1]:.1f}"
        for p in outline_2d[1:]:
            d += f" L {p[0]:.1f} {p[1]:.1f}"
        d += " Z"
        ET.SubElement(svg, "path", {
            "d": d, "fill": fill, "stroke": fill, "stroke-width": "0.5",
        })

    # --- Draw geodesic edges on top ----------------------------------------
    for arc in edge_arcs:
        r_arc = [rot(p) for p in arc]
        mid_pt = r_arc[len(r_arc) // 2]
        if mid_pt[2] < -0.02:
            continue
        pts = [proj(p) for p in r_arc]
        d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
        for p in pts[1:]:
            d += f" L {p[0]:.1f} {p[1]:.1f}"
        avg_z = sum(p[2] for p in r_arc) / len(r_arc)
        t = max(0.0, min(1.0, (avg_z + 1) / 2))
        ec = lerp_color(edge_dark, edge_light, t)
        opacity = 0.4 + 0.55 * t
        ET.SubElement(svg, "path", {
            "d": d, "fill": "none",
            "stroke": ec, "stroke-width": "2.2",
            "stroke-opacity": f"{opacity:.2f}",
            "stroke-linecap": "round", "stroke-linejoin": "round",
        })

    # --- Methane molecule (space-filling, upper left) -------------------------
    # Tetrahedral CH4: C at center, 4 H at tetrahedral vertices
    # Van der Waals radii: C=1.7Å, H=1.2Å; bond length=1.09Å
    # Project central hex center to find its screen position
    center_rot = rot(centers_3d[0])
    center_2d = proj(center_rot)

    mol_cx = center_2d[0] - proj_scale * 0.62
    mol_cy = center_2d[1] - proj_scale * 0.48
    mol_scale = W * 0.06  # scale factor Å → px
    # True vdW radii make the H atoms hide behind C; use scaled-down
    # radii so the tetrahedral shape is clearly visible
    vdw_c = 1.0 * mol_scale  # reduced from 1.7
    vdw_h = 0.75 * mol_scale  # reduced from 1.2
    bond = 1.09  # C-H bond length in Å

    # Tetrahedral directions (unit vectors)
    inv_sqrt3 = 1.0 / math.sqrt(3)
    tet = [
        ( inv_sqrt3,  inv_sqrt3,  inv_sqrt3),
        ( inv_sqrt3, -inv_sqrt3, -inv_sqrt3),
        (-inv_sqrt3,  inv_sqrt3, -inv_sqrt3),
        (-inv_sqrt3, -inv_sqrt3,  inv_sqrt3),
    ]

    # Rotate to an edge-on view where all 4 H atoms are visible
    mol_rot = make_rotation(0.95, 0.0)
    h_positions_3d = [mol_rot(scale3(t, bond)) for t in tet]

    # All atoms: (element, x3d, y3d, z3d, radius)
    atoms = [("C", 0.0, 0.0, 0.0, vdw_c)]
    for hx, hy, hz in h_positions_3d:
        atoms.append(("H", hx, hy, hz, vdw_h))

    # Sort by z (back to front) for painter's algorithm
    atoms.sort(key=lambda a: a[3])

    for elem, ax, ay, az, ar in atoms:
        sx = mol_cx + ax * mol_scale
        sy = mol_cy - ay * mol_scale
        grad = "url(#carbonGrad)" if elem == "C" else "url(#hydrogenGrad)"
        ET.SubElement(svg, "circle", {
            "cx": f"{sx:.1f}", "cy": f"{sy:.1f}", "r": f"{ar:.1f}",
            "fill": grad,
        })
        bbox_pts.extend([(sx - ar, sy - ar), (sx + ar, sy + ar)])

    # --- Small molecules upper right: CO, NO, NO2 ----------------------------
    # Shared scale and radii
    sm_scale = mol_scale
    r_c = 1.0 * sm_scale
    r_o = 1.0 * sm_scale
    r_n = 1.0 * sm_scale

    grad_map = {
        "C": "url(#carbonGrad)",
        "O": "url(#oxygenGrad)",
        "N": "url(#nitrogenGrad)",
    }

    def draw_molecule(atoms_local, mcx, mcy, rot_func):
        """Draw a space-filling molecule at (mcx, mcy) screen coords."""
        rotated = []
        for elem, lx, ly, lz, ar in atoms_local:
            rx, ry, rz = rot_func((lx, ly, lz))
            rotated.append((elem, rx, ry, rz, ar))
        rotated.sort(key=lambda a: a[3])
        for elem, ax, ay, az, ar in rotated:
            sx = mcx + ax * sm_scale
            sy = mcy - ay * sm_scale
            ET.SubElement(svg, "circle", {
                "cx": f"{sx:.1f}", "cy": f"{sy:.1f}", "r": f"{ar:.1f}",
                "fill": grad_map[elem],
            })
            bbox_pts.extend([(sx - ar, sy - ar), (sx + ar, sy + ar)])

    small_rot = make_rotation(0.3, -0.4)

    # CO: linear, C-O bond 1.13Å
    co_cx = center_2d[0] + proj_scale * 0.65
    co_cy = center_2d[1] - proj_scale * 0.55
    co_bond = 1.13
    co_atoms = [
        ("C", -co_bond / 2, 0.0, 0.0, r_c),
        ("O",  co_bond / 2, 0.0, 0.0, r_o),
    ]
    draw_molecule(co_atoms, co_cx, co_cy, small_rot)

    # NO: linear, N-O bond 1.15Å
    no_cx = center_2d[0] + proj_scale * 0.32
    no_cy = center_2d[1] - proj_scale * 0.26
    no_bond = 1.15
    no_atoms = [
        ("N", -no_bond / 2, 0.0, 0.0, r_n),
        ("O",  no_bond / 2, 0.0, 0.0, r_o),
    ]
    draw_molecule(no_atoms, no_cx, no_cy, small_rot)

    # NO2: bent, O-N-O angle 134°, N-O bond 1.20Å
    no2_cx = center_2d[0] + proj_scale * 0.55
    no2_cy = center_2d[1] + proj_scale * 0.25
    no2_bond = 1.20
    half_ang = 134.0 / 2 * math.pi / 180
    no2_atoms = [
        ("N", 0.0, 0.0, 0.0, r_n),
        ("O", -no2_bond * math.sin(half_ang),  no2_bond * math.cos(half_ang), 0.0, r_o),
        ("O",  no2_bond * math.sin(half_ang),  no2_bond * math.cos(half_ang), 0.0, r_o),
    ]
    draw_molecule(no2_atoms, no2_cx, no2_cy, small_rot)

    # --- Text (clear of all icons placed above) ------------------------------
    # The central hex's lowest projected corner sets the floor of the sphere;
    # the small molecules can sit lower (NO2 in particular). Place the
    # wordmark below whichever extends further, plus padding.
    if text_mode == "chempas":
        content_bottom = max(p[1] for p in bbox_pts)
        text_y = content_bottom + 56
        ET.SubElement(svg, "text", {
            "x": f"{center_2d[0]:.0f}", "y": f"{text_y:.0f}",
            "text-anchor": "middle",
            "font-family": "Poppins, 'Helvetica Neue', Helvetica, Arial, sans-serif",
            "font-weight": "600", "font-size": "46",
            "letter-spacing": "10", "fill": orange,
        }).text = "CheMPAS-A"
        # Estimate text bounding box (9 chars × ~35 px per glyph + spacing)
        text_x = center_2d[0]
        bbox_pts.extend([(text_x - 215, text_y - 46), (text_x + 215, text_y + 10)])

    # --- Finalize viewBox to tightly fit all content -----------------------
    pad = 15
    min_x = min(p[0] for p in bbox_pts) - pad
    min_y = min(p[1] for p in bbox_pts) - pad
    max_x = max(p[0] for p in bbox_pts) + pad
    max_y = max(p[1] for p in bbox_pts) + pad
    vb_w = max_x - min_x
    vb_h = max_y - min_y
    svg.set("viewBox", f"{min_x:.1f} {min_y:.1f} {vb_w:.1f} {vb_h:.1f}")
    svg.set("height", f"{W * vb_h / vb_w:.0f}")

    return svg


def write_svg(svg, path):
    tree = ET.ElementTree(svg)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="unicode", xml_declaration=True)
    print(f"Wrote {path}")


def main():
    write_svg(build_svg(text_mode="chempas"), "logo_chempas_blue.svg")
    write_svg(build_svg(text_mode="none"), "logo_chempas_blue_icon.svg")
    write_svg(build_svg(text_mode="chempas", color_scheme="aqua"), "logo_chempas_aqua.svg")
    write_svg(build_svg(text_mode="none", color_scheme="aqua"), "logo_chempas_aqua_icon.svg")


if __name__ == "__main__":
    main()
