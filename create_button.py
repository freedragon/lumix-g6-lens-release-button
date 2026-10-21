"""Build an adjustable, unverified Lumix G6 lens-release button prototype.

Run with FreeCAD's Python interpreter; see README.md.
"""

import argparse
from dataclasses import dataclass
from math import pi
from pathlib import Path

import FreeCAD as App
import Mesh
import MeshPart
import Part


@dataclass(frozen=True)
class Dimensions:
    # User measurements, including the reconstructed second wing.
    face_width: float = 11.5
    wing_projection: float = 3.5
    height: float = 5.6
    side_height: float = 3.7
    depth: float = 5.7
    shell_width: float = 5.5
    shell_height: float = 5.0
    shell_rear_y: float = 0.35
    face_thickness: float = 2.10
    shell_depth: float = 4.0
    wall_thickness: float = 0.5
    rear_rim_width: float = 0.45
    rear_rim_length: float = 3.5
    rear_wall_length: float = 8.3
    rear_rim_depth: float = 4.6
    wing_stem_width: float = 1.45
    wing_inner_gap: float = 5.4
    wing_rear_y: float = 2.129095068291875
    wing_height: float = 2.0
    hook_thickness: float = 1.0
    wing_rib_radius: float = 0.2
    reinforcement_span: float = 8.3
    reinforcement_height: float = 1.2
    bottom_edge_radius: float = 0.5

    # Photo-based estimates, NOT measured dimensions. All values are in mm.
    front_corner_radius: float = 0.5
    rear_concavity: float = 0.5
    shell_bulge: float = 0.6

    @property
    def wing_span(self):
        return self.shell_width + 2 * self.wing_projection

    @property
    def overall_width(self):
        return max(self.face_width, self.wing_span)

    @property
    def wing_rib_height(self):
        return self.depth - self.hook_thickness - self.face_thickness

    @property
    def reinforcement_length(self):
        return (self.reinforcement_span - self.shell_width) / 2

    @property
    def wing_center_y(self):
        return self.wing_rear_y + self.wing_height / 2

    @property
    def wing_rear_clearance(self):
        x = (self.wing_inner_gap + self.wing_stem_width) / 2
        return self.wing_rear_y - rear_edge_y(self, x)

    def validate(self):
        if any(value <= 0 for value in vars(self).values()):
            raise ValueError("Every dimension must be positive.")
        if not self.rear_concavity < self.side_height < self.height:
            raise ValueError("Require rear concavity < side height < maximum face height.")
        if self.front_corner_radius >= min(self.height - self.side_height, self.face_width / 2):
            raise ValueError("Front corner radius leaves no room for the front arch.")
        if not (self.face_thickness < self.shell_depth < self.rear_rim_depth
                < self.depth - self.hook_thickness):
            raise ValueError("Require face < shell < rear rim < hook underside < total depth.")
        if self.rear_rim_width > self.wall_thickness:
            raise ValueError("Rear rim must fit on the rear shell wall.")
        if not self.rear_rim_length <= self.shell_width < self.rear_wall_length < self.face_width:
            raise ValueError("Require rim length <= shell width < rear wall length < face width.")
        if not self.wall_thickness < min(self.shell_width, self.shell_height) / 2:
            raise ValueError("Wall thickness leaves no cavity.")
        if not 0 < self.shell_bulge < min(self.shell_height / 2, self.shell_width / 2):
            raise ValueError("Shell bulge must leave straight side walls.")
        if self.shell_height >= self.height or self.shell_width >= self.face_width:
            raise ValueError("The central shell must fit within the face.")
        if self.shell_rear_y + self.shell_height > self.height:
            raise ValueError("The fixed shell front must not exceed the maximum face height.")
        if self.wing_rear_clearance <= 0:
            raise ValueError("The fixed wing stems must remain ahead of the rear outline.")
        if self.wing_stem_width >= self.wing_projection:
            raise ValueError("Wing stems must leave room for outward hook lips.")
        if 2 * self.wing_rib_radius >= self.wing_height:
            raise ValueError("Half-round ribs must fit within the wing breadth.")
        if self.wing_rib_radius >= self.wing_span / 2 - self.wing_inner_gap / 2 - self.wing_stem_width:
            raise ValueError("Half-round ribs must remain beneath the wing lips.")
        if not self.shell_width - 2 * self.wall_thickness < self.wing_inner_gap <= self.shell_width:
            raise ValueError("Wing stems must meet the shell walls without entering the cavity.")
        if self.wing_inner_gap / 2 + self.wing_stem_width <= self.shell_width / 2:
            raise ValueError("Wing stems must extend outside the shell.")
        if not 0 < self.wing_center_y - self.wing_height / 2:
            raise ValueError("Wing extends below the face.")
        if self.wing_center_y + self.wing_height / 2 >= self.height:
            raise ValueError("Wing must stay within the maximum face height.")
        if self.shell_width / 2 + self.reinforcement_length >= self.face_width / 2:
            raise ValueError("Front reinforcements must fit inside the button width.")
        if self.reinforcement_length <= 0:
            raise ValueError("Front reinforcement span must exceed the shell width.")
        if abs(self.reinforcement_span - self.wing_inner_gap - 2 * self.wing_stem_width) > 1e-6:
            raise ValueError("Front reinforcement ends must align with the outer stem faces.")
        if self.face_thickness + self.reinforcement_height > self.shell_depth:
            raise ValueError("Front reinforcements must not exceed the general shell height.")
        if self.bottom_edge_radius >= self.face_thickness:
            raise ValueError("Bottom edge fillet must remain below the upper base face.")


def rear_edge_y(d, x):
    half = d.face_width / 2
    if abs(x) > half:
        raise ValueError("Rear edge position lies outside the button width.")
    radius = (half**2 + d.rear_concavity**2) / (2 * d.rear_concavity)
    return d.rear_concavity - radius + (radius**2 - x**2)**0.5


def face_outline(d):
    half = d.face_width / 2
    r = d.front_corner_radius
    cx = half - r
    rise = d.height - d.side_height
    # Solve for a front circle tangent to both corner rounds while retaining
    # the measured straight side length and maximum face height.
    radius = (cx**2 + rise**2 - r**2) / (2 * (rise - r))
    cy = d.height - radius
    tx = cx * radius / (radius - r)
    ty = cy + (d.side_height - cy) * radius / (radius - r)
    ux = cx / (radius - r)
    uy = (d.side_height - cy) / (radius - r)
    midpoint_length = ((1 + ux)**2 + uy**2)**0.5
    mx = cx + r * (1 + ux) / midpoint_length
    my = d.side_height + r * uy / midpoint_length
    v = App.Vector
    edges = [
        Part.Arc(v(-half, 0, 0), v(0, d.rear_concavity, 0),
                 v(half, 0, 0)).toShape(),
        Part.makeLine(v(half, 0, 0), v(half, d.side_height, 0)),
        Part.Arc(v(half, d.side_height, 0), v(mx, my, 0), v(tx, ty, 0)).toShape(),
        Part.Arc(v(tx, ty, 0), v(0, d.height, 0), v(-tx, ty, 0)).toShape(),
        Part.Arc(v(-tx, ty, 0), v(-mx, my, 0), v(-half, d.side_height, 0)).toShape(),
        Part.makeLine(v(-half, d.side_height, 0), v(-half, 0, 0)),
    ]
    return Part.Wire(edges)


def button_base(d):
    face = Part.Face(face_outline(d)).extrude(App.Vector(0, 0, d.face_thickness))
    bottom_edges = [
        edge for edge in face.Edges
        if abs(edge.BoundBox.ZMin) < 1e-7 and abs(edge.BoundBox.ZMax) < 1e-7
    ]
    if len(bottom_edges) != len(face_outline(d).Edges):
        raise RuntimeError("Expected the complete Z=0 perimeter for bottom edge filleting.")
    rounded = face.makeFillet(d.bottom_edge_radius, bottom_edges)
    if not rounded.isValid() or len(rounded.Solids) != 1:
        raise RuntimeError("Bottom edge fillet did not produce one valid base solid.")
    return rounded


def build(d):
    d.validate()
    face = button_base(d)
    shell = central_shell(d)
    face_envelope = Part.Face(face_outline(d)).extrude(App.Vector(0, 0, d.depth))
    supported_shell = face.fuse(shell)
    if len(supported_shell.Solids) != 1 or not supported_shell.isValid():
        raise ValueError("The fixed shell must remain connected to the trimmed button base.")

    # The outward lip on each stem reconstructs the intact wing's L profile.
    x = d.wing_inner_gap / 2
    y = d.wing_center_y - d.wing_height / 2
    stem = Part.makeBox(
        d.wing_stem_width, d.wing_height,
        d.depth - d.hook_thickness - d.face_thickness,
        App.Vector(x, y, d.face_thickness),
    )
    hook = Part.makeBox(
        d.wing_projection, d.wing_height, d.hook_thickness,
        App.Vector(d.shell_width / 2, y, d.depth - d.hook_thickness),
    )
    rib = wing_rib(d)
    right = stem.fuse(hook).fuse(rib)
    if stem.cut(face_envelope).Volume > 1e-6:
        raise ValueError("Wing stem footprint extends beyond the curved button face.")
    if rib.cut(face_envelope).Volume > 1e-6:
        raise ValueError("Half-round rib footprint extends beyond the curved button face.")
    left = right.mirror(App.Vector(0, 0, 0), App.Vector(1, 0, 0))
    result = face.fuse(shell).fuse(right).fuse(left)
    for reinforcement in front_reinforcements(d):
        if reinforcement.cut(face_envelope).Volume > 1e-6:
            raise ValueError("Front reinforcement extends beyond the button face.")
        result = result.fuse(reinforcement)
    return result.removeSplitter()


def wing_rib(d):
    x = d.wing_inner_gap / 2 + d.wing_stem_width
    y = d.wing_center_y
    z = d.face_thickness
    r = d.wing_rib_radius
    start = App.Vector(x, y - r, z)
    end = App.Vector(x, y + r, z)
    outline = Part.Wire([
        Part.Arc(start, App.Vector(x + r, y, z), end).toShape(),
        Part.makeLine(end, start),
    ])
    return Part.Face(outline).extrude(App.Vector(0, 0, d.wing_rib_height))


def shell_outline(d):
    half = d.shell_width / 2
    low = d.shell_rear_y
    high = low + d.shell_height
    v = App.Vector
    return Part.Wire([
        Part.makeLine(v(-half, low, 0), v(half, low, 0)),
        Part.makeLine(v(half, low, 0),
                      v(half, high - d.shell_bulge, 0)),
        Part.Arc(v(half, high - d.shell_bulge, 0), v(0, high, 0),
                 v(-half, high - d.shell_bulge, 0)).toShape(),
        Part.makeLine(v(-half, high - d.shell_bulge, 0),
                      v(-half, low, 0)),
    ])


def central_shell(d):
    outer = shell_outline(d)
    inner = outer.makeOffset2D(-d.wall_thickness)
    if abs(outer.distToShape(inner)[0] - d.wall_thickness) > 1e-6:
        raise RuntimeError("Shell wall offset does not match the specified thickness.")
    ring = Part.Face(outer).cut(Part.Face(inner))
    shell = ring.extrude(App.Vector(0, 0, d.shell_depth - d.face_thickness))
    shell.translate(App.Vector(0, 0, d.face_thickness))
    rear_y = d.shell_rear_y
    rear_wall = Part.makeBox(
        d.rear_wall_length, d.wall_thickness, d.shell_depth - d.face_thickness,
        App.Vector(-d.rear_wall_length / 2, rear_y, d.face_thickness),
    )
    rim = Part.makeBox(
        d.rear_rim_length, d.rear_rim_width, d.rear_rim_depth - d.shell_depth,
        App.Vector(-d.rear_rim_length / 2, rear_y, d.shell_depth),
    )
    return shell.fuse(rear_wall).fuse(rim).removeSplitter()


def front_reinforcements(d):
    circle = shell_outline(d).Edges[2].Curve
    if d.shell_width / 2 + d.reinforcement_length >= circle.Radius - d.wall_thickness:
        raise ValueError("Front shell curvature cannot extend to the reinforcement tips.")
    origin = App.Vector(circle.Center.x, circle.Center.y, d.face_thickness)
    outer = Part.makeCylinder(circle.Radius, d.reinforcement_height, origin)
    inner = Part.makeCylinder(circle.Radius - d.wall_thickness, d.reinforcement_height, origin)
    region = Part.makeBox(
        d.reinforcement_length, d.height, d.reinforcement_height,
        App.Vector(d.shell_width / 2, 0, d.face_thickness),
    )
    right = outer.cut(inner).common(region)
    left = right.mirror(App.Vector(0, 0, 0), App.Vector(1, 0, 0))
    return right, left


def check_shape(shape, d):
    if not shape.isValid() or len(shape.Solids) != 1 or shape.Volume <= 0:
        raise RuntimeError("Expected one valid, connected solid with positive volume.")
    bounds = shape.optimalBoundingBox(False, False)
    actual = (bounds.XLength, bounds.YLength, bounds.ZLength)
    expected = (d.overall_width, d.height, d.depth)
    if any(abs(a - b) > 1e-6 for a, b in zip(actual, expected)):
        raise RuntimeError(f"Wrong bounding dimensions: {actual}, expected {expected}.")
    mirrored = shape.mirror(App.Vector(0, 0, 0), App.Vector(1, 0, 0))
    if shape.cut(mirrored).Volume + mirrored.cut(shape).Volume > 1e-6:
        raise RuntimeError("The reconstructed wings are not symmetric.")
    center_probe = Part.makeBox(
        1, 1, d.depth, App.Vector(-0.5, d.height / 2 - 0.5, d.face_thickness)
    )
    if shape.common(center_probe).Volume > 1e-6:
        raise RuntimeError("The central rear cavity must not contain a pin.")
    region = Part.makeBox(
        d.wing_inner_gap, d.height, d.depth,
        App.Vector(-d.wing_inner_gap / 2, 0, d.face_thickness),
    )
    actual_shell = shape.common(region)
    expected_shell = central_shell(d).common(region)
    if (actual_shell.cut(expected_shell).Volume
            + expected_shell.cut(actual_shell).Volume > 1e-6):
        raise RuntimeError("Central shell differs from its specified hollow geometry.")
    shell_bounds = actual_shell.BoundBox
    for actual, expected in zip(
        (shell_bounds.XLength, shell_bounds.YLength, shell_bounds.ZMax),
        (d.wing_inner_gap, d.shell_height, d.rear_rim_depth),
    ):
        if abs(actual - expected) > 1e-6:
            raise RuntimeError("Central shell outside dimensions or rim depth are wrong.")
    upper_region = Part.makeBox(
        d.shell_width, d.height, d.depth,
        App.Vector(-d.shell_width / 2, 0, d.shell_depth),
    )
    upper_shell = actual_shell.common(upper_region)
    rim_bounds = upper_shell.BoundBox
    if (abs(rim_bounds.XLength - d.rear_rim_length) > 1e-6
            or abs(rim_bounds.XMin + d.rear_rim_length / 2) > 1e-6
            or abs(rim_bounds.YLength - d.rear_rim_width) > 1e-6
            or abs(rim_bounds.ZLength - (d.rear_rim_depth - d.shell_depth)) > 1e-6
            or abs(rim_bounds.YMin - d.shell_rear_y) > 1e-6):
        raise RuntimeError("Only the straight rear wall may carry the specified raised rim.")
    rear_region = Part.makeBox(
        d.face_width, d.wall_thickness, d.depth,
        App.Vector(-d.face_width / 2, d.shell_rear_y, d.face_thickness),
    )
    rear_bounds = shape.common(rear_region).BoundBox
    if abs(rear_bounds.XLength - d.rear_wall_length) > 1e-6:
        raise RuntimeError("Rear wall extension length differs from its measured span.")
    for side in (-1, 1):
        extension_x = d.shell_width / 2 if side == 1 else -d.rear_wall_length / 2
        extension = Part.makeBox(
            (d.rear_wall_length - d.shell_width) / 2, d.wall_thickness,
            d.shell_depth - d.face_thickness,
            App.Vector(extension_x, d.shell_rear_y, d.face_thickness),
        )
        if abs(shape.common(extension).Volume - extension.Volume) > 1e-6:
            raise RuntimeError("Rear wall extensions must retain full wall thickness and height.")
    for side in (-1, 1):
        end_line = Part.makeLine(
            App.Vector(side * d.face_width / 2, 0, d.face_thickness / 2),
            App.Vector(side * d.face_width / 2, d.height, d.face_thickness / 2),
        )
        if abs(shape.common(end_line).Length - d.side_height) > 1e-6:
            raise RuntimeError("The two face end edges must match the measured side height.")
    rear_midpoint = Part.Vertex(App.Vector(0, d.rear_concavity, d.face_thickness / 2))
    if shape.distToShape(rear_midpoint)[0] > 1e-6 or shape.isInside(
        App.Vector(0, d.rear_concavity / 2, d.face_thickness / 2), 1e-7, False
    ):
        raise RuntimeError("The rear face outline must be concave by the specified amount.")
    base_region = Part.makeBox(
        d.face_width, d.height, d.face_thickness,
        App.Vector(-d.face_width / 2, 0, 0),
    )
    expected_base = button_base(d)
    actual_base = shape.common(base_region)
    if (actual_base.cut(expected_base).Volume
            + expected_base.cut(actual_base).Volume > 1e-6):
        raise RuntimeError("The button base differs from its specified thickness and bottom fillet.")
    wing_y = d.wing_center_y - d.wing_height / 2
    for side in (-1, 1):
        stem_x = d.wing_inner_gap / 2 if side == 1 else -d.wing_inner_gap / 2 - d.wing_stem_width
        stem_probe = Part.makeBox(
            d.wing_stem_width, d.wing_height,
            d.depth - d.hook_thickness - d.face_thickness,
            App.Vector(stem_x, wing_y, d.face_thickness),
        )
        if abs(shape.common(stem_probe).Volume - stem_probe.Volume) > 1e-6:
            raise RuntimeError("Wing stem must meet the shell directly at full thickness.")
        lip_start = d.wing_inner_gap / 2 + d.wing_stem_width
        lip_x = lip_start if side == 1 else -d.wing_span / 2
        lip_region = Part.makeBox(
            d.wing_span / 2 - lip_start, d.wing_height,
            d.depth - d.face_thickness,
            App.Vector(lip_x, wing_y, d.face_thickness),
        )
        lip = shape.common(lip_region)
        expected_lip = Part.makeBox(
            d.wing_span / 2 - lip_start, d.wing_height, d.hook_thickness,
            App.Vector(lip_x, wing_y, d.depth - d.hook_thickness),
        )
        rib = wing_rib(d)
        if side == -1:
            rib = rib.mirror(App.Vector(0, 0, 0), App.Vector(1, 0, 0))
        expected_lip = expected_lip.fuse(rib)
        if (lip.cut(expected_lip).Volume + expected_lip.cut(lip).Volume > 1e-6):
            raise RuntimeError("Wing lip must retain its top thickness and centered half-round rib.")
        expected_volume = pi * d.wing_rib_radius**2 * d.wing_rib_height / 2
        if abs(rib.Volume - expected_volume) > 1e-6:
            raise RuntimeError("Wing rib must have the specified half-cylinder volume.")
    stem_region = Part.makeBox(
        d.wing_inner_gap + 2 * d.wing_stem_width, d.height,
        d.depth - d.hook_thickness - d.rear_rim_depth,
        App.Vector(-d.wing_inner_gap / 2 - d.wing_stem_width, 0, d.rear_rim_depth),
    )
    stems = sorted(shape.common(stem_region).Solids, key=lambda solid: solid.BoundBox.XMin)
    if len(stems) != 2:
        raise RuntimeError("Expected two separate stems above the shell and rear rim.")
    if abs(stems[1].BoundBox.XMin - stems[0].BoundBox.XMax - d.wing_inner_gap) > 1e-6:
        raise RuntimeError("Inner stem spacing differs from the measured gap.")
    for stem in stems:
        bounds = stem.BoundBox
        if abs(bounds.XLength - d.wing_stem_width) > 1e-6:
            raise RuntimeError("Wing stem width differs from its measured thickness.")
        if abs(bounds.YLength - d.wing_height) > 1e-6:
            raise RuntimeError("Wing stem front-to-back breadth differs from its measured width.")
        if abs(bounds.YMin - d.wing_rear_y) > 1e-6:
            raise RuntimeError("Wing stems must retain their fixed rear positions after base trimming.")
        reference_x = (bounds.XMin + bounds.XMax) / 2
        rear_point = App.Vector(reference_x, bounds.YMin - d.wing_rear_clearance, 0)
        rear_arc = face_outline(d).Edges[0]
        if rear_arc.distToShape(Part.Vertex(rear_point))[0] > 1e-6:
            raise RuntimeError("Wing rear clearance must be measured from the local rear arc.")
    wing_region = Part.makeBox(
        d.wing_span, d.height, d.hook_thickness,
        App.Vector(-d.wing_span / 2, 0, d.depth - d.hook_thickness),
    )
    top_wings = shape.common(wing_region)
    if abs(top_wings.BoundBox.XLength - d.wing_span) > 1e-6:
        raise RuntimeError("Top wing span differs from the shell width plus both projections.")
    if (abs(top_wings.BoundBox.XMin + d.wing_span / 2) > 1e-6
            or abs(top_wings.BoundBox.XMax - d.wing_span / 2) > 1e-6):
        raise RuntimeError("Top wing tips must be symmetric at the specified overall wing span.")
    if len(top_wings.Solids) != 2 or any(
        abs(wing.BoundBox.YLength - d.wing_height) > 1e-6 for wing in top_wings.Solids
    ):
        raise RuntimeError("Both top wings must have the measured front-to-back breadth.")
    front_rounds = [
        surface for surface in (face.Surface for face in shape.Faces)
        if isinstance(surface, Part.Cylinder)
        and abs(surface.Radius - d.front_corner_radius) < 1e-6
        and abs(abs(surface.Axis.z) - 1) < 1e-6
        and surface.Center.y > d.side_height - 1e-6
    ]
    if len(front_rounds) != 2:
        raise RuntimeError("Expected two front corner rounds with the requested radius.")
    shell = central_shell(d)
    for reinforcement in front_reinforcements(d):
        bounds = reinforcement.BoundBox
        if (not reinforcement.isValid() or len(reinforcement.Solids) != 1
                or abs(bounds.XLength - d.reinforcement_length) > 1e-6
                or abs(bounds.ZLength - d.reinforcement_height) > 1e-6
                or abs(bounds.ZMin - d.face_thickness) > 1e-6):
            raise RuntimeError("Front reinforcement must have the specified length and height.")
        radii = sorted(
            face.Surface.Radius for face in reinforcement.Faces
            if isinstance(face.Surface, Part.Cylinder)
        )
        if len(radii) != 2 or abs(radii[1] - radii[0] - d.wall_thickness) > 1e-6:
            raise RuntimeError("Curved reinforcement must retain the shell wall thickness.")
        if reinforcement.cut(shape).Volume > 1e-6:
            raise RuntimeError("Front reinforcement is missing from the exported button.")
        joined = reinforcement.fuse(shell)
        if len(joined.Solids) != 1 or not joined.isValid():
            raise RuntimeError("Front reinforcement must join the shell.")
        stem_x = d.wing_inner_gap / 2 if bounds.XMin > 0 else -d.wing_inner_gap / 2 - d.wing_stem_width
        stem = Part.makeBox(
            d.wing_stem_width, d.wing_height, d.reinforcement_height,
            App.Vector(stem_x, wing_y, d.face_thickness),
        )
        outer_x = bounds.XMax if bounds.XMin > 0 else bounds.XMin
        stem_outer_x = stem.BoundBox.XMax if bounds.XMin > 0 else stem.BoundBox.XMin
        if (abs(outer_x - stem_outer_x) > 1e-6
                or abs(abs(outer_x) * 2 - d.reinforcement_span) > 1e-6):
            raise RuntimeError("Front reinforcement tips must match the  outer stem faces and span.")
        if reinforcement.common(stem).Volume < 1e-6:
            raise RuntimeError("Curved reinforcement must connect to its wing stem.")


def write_preview(shape, target):
    bounds = shape.optimalBoundingBox(False, False)
    panels = [
        ("Face outline (rear features behind)", lambda p: (p.x, -p.y)),
        ("Side: face down, hooks up", lambda p: (p.x, -p.z)),
        ("Isometric wireframe", lambda p: (0.86 * (p.x - p.y),
                                         0.5 * (p.x + p.y) - p.z)),
    ]
    content = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="430" '
        'viewBox="0 0 1080 430">',
        '<rect width="1080" height="430" fill="#f5f7fa"/>',
        '<g font-family="sans-serif" fill="#182c40">',
        '<text x="25" y="32" font-size="22">Lumix G6 button - FIRST-FIT PROTOTYPE</text>',
        '<text x="25" y="60" font-size="15">'
        f'{bounds.XLength:g} mm overall width x {bounds.YLength:g} mm height '
        f'x {bounds.ZLength:g} mm depth; small features estimated</text>',
    ]
    for index, (label, project) in enumerate(panels):
        content.append(f'<text x="{25 + index * 355}" y="104" font-size="14">{label}</text>')
        for edge in shape.Edges:
            points = []
            for point in edge.discretize(Deflection=0.025):
                x, y = project(point)
                points.append(f"{195 + index * 355 + x * 23:.3f},{295 + y * 23:.3f}")
            content.append(
                f'<polyline points="{" ".join(points)}" fill="none" '
                'stroke="#276a97" stroke-width="1.2"/>'
            )
    content.extend([
        '<text x="25" y="395" font-size="15">'
        'Wireframe includes hidden edges. Physical fit and hook strength are NOT verified.</text>',
        '</g></svg>',
    ])
    target.write_text("\n".join(content), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    d = Dimensions()
    shape = build(d)
    check_shape(shape, d)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = args.output_dir / "lumix_g6_button_prototype"

    document = App.newDocument("LumixG6ButtonPrototype")
    feature = document.addObject("PartDesign::Feature", "Button")
    feature.Label = "FIRST-FIT ONLY - estimated wings and shell"
    feature.Shape = shape
    for name, value in vars(d).items():
        measured = ("face_width", "wing_projection", "height", "depth", "shell_width",
                    "shell_height", "shell_rear_y", "shell_depth", "wall_thickness", "face_thickness",
                    "rear_rim_width", "rear_rim_length", "rear_wall_length", "side_height",
                    "rear_rim_depth", "wing_stem_width", "wing_inner_gap",
                    "wing_rear_y", "wing_height", "hook_thickness",
                    "reinforcement_span", "reinforcement_height", "bottom_edge_radius")
        group = "Measured dimensions" if name in measured else "Estimated geometry"
        feature.addProperty("App::PropertyLength", name, group)
        setattr(feature, name, value)
        feature.setEditorMode(name, 1)
    document.recompute()
    document.saveAs(str(base.with_suffix(".FCStd")))
    shape.exportStep(str(base.with_suffix(".step")))

    mesh = MeshPart.meshFromShape(
        Shape=shape, LinearDeflection=0.015, AngularDeflection=0.1, Relative=False
    )
    mesh.write(str(base.with_suffix(".stl")))
    reloaded = Mesh.Mesh(str(base.with_suffix(".stl")))
    if not reloaded.isSolid() or reloaded.countComponents() != 1:
        raise RuntimeError("Exported STL is not one closed mesh.")
    if abs(reloaded.Volume - shape.Volume) > shape.Volume * 0.005:
        raise RuntimeError("STL volume differs from the CAD solid by more than 0.5%.")
    mesh_bounds = reloaded.BoundBox
    for actual, expected in zip(
        (mesh_bounds.XLength, mesh_bounds.YLength, mesh_bounds.ZLength),
        (d.overall_width, d.height, d.depth),
    ):
        if abs(actual - expected) > 0.02:
            raise RuntimeError("Exported STL dimensions exceed 0.02 mm tolerance.")
    check_shape(Part.read(str(base.with_suffix(".step"))), d)
    write_preview(shape, base.with_suffix(".svg"))
    App.closeDocument(document.Name)
    print(f"Verified CAD and STEP: one valid symmetric solid, {shape.Volume:.3f} mm^3.")
    print(f"Verified STL: one closed component, {reloaded.CountFacets} triangles.")
    print(f"Envelope: {d.overall_width} x {d.height} x {d.depth} mm; base width {d.face_width} mm.")
    print(f"Wing span: {d.wing_span} mm; front corner radius: {d.front_corner_radius} mm.")
    print(f"Files written to {args.output_dir}. Physical fit remains unverified.")


if __name__ == "__main__":
    main()
