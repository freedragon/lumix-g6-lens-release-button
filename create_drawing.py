"""Create a separate dimensioned SVG from the validated exported STEP model."""

from html import escape
from pathlib import Path
import xml.etree.ElementTree as ET

from create_button import Dimensions, check_shape, rear_edge_y, wireframe_polylines

import Part


SCALE = 48


class Drawing:
    def __init__(self):
        self.elements = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1840" '
            'viewBox="0 0 1800 1840">',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" '
            'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            '<path d="M 0 0 L 10 5 L 0 10 z" fill="#1769a0"/></marker></defs>',
            '<rect width="1800" height="1840" fill="white"/>',
            '<g font-family="sans-serif" font-size="17" fill="#183047">',
        ]

    def text(self, x, y, text, size=17, color="#183047", anchor="start", rotation=0):
        self.elements.append(
            f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" transform="rotate({rotation} {x:.3f} {y:.3f})">'
            f'{escape(text)}</text>'
        )

    def line(self, start, end, color="#bcc8d2", arrows=False):
        markers = ' marker-start="url(#arrow)" marker-end="url(#arrow)"' if arrows else ""
        self.elements.append(
            f'<line x1="{start[0]:.3f}" y1="{start[1]:.3f}" '
            f'x2="{end[0]:.3f}" y2="{end[1]:.3f}" '
            f'stroke="{color}" stroke-width="1"{markers}/>'
        )

    def horizontal(self, start, end, y, label):
        self.line(start, (start[0], y + 8))
        self.line(end, (end[0], y + 8))
        self.line((start[0], y), (end[0], y), "#1769a0", True)
        self.text((start[0] + end[0]) / 2, y - 9, label, color="#1769a0", anchor="middle")

    def vertical(self, start, end, x, label):
        self.line(start, (x + 8, start[1]))
        self.line(end, (x + 8, end[1]))
        self.line((x, start[1]), (x, end[1]), "#1769a0", True)
        self.text(x - 10, (start[1] + end[1]) / 2, label,
                  color="#1769a0", anchor="middle", rotation=-90)

    def geometry(self, shape, project):
        for points in wireframe_polylines(shape, project):
            coordinates = " ".join(f"{x:.3f},{y:.3f}" for x, y in points)
            self.elements.append(
                f'<polyline points="{coordinates}" fill="none" stroke="#293e50" '
                'stroke-width="1.5" stroke-linejoin="round"/>'
            )

    def save(self, path):
        content = "\n".join(self.elements + ["</g></svg>"])
        ET.fromstring(content)
        path.write_text(content, encoding="utf-8")


def main():
    folder = Path(__file__).resolve().parent
    d = Dimensions()
    d.validate()
    shape = Part.read(str(folder / "lumix_g6_button_prototype.step"))
    check_shape(shape, d)
    drawing = Drawing()
    drawing.text(40, 42, "LUMIX G6 LENS-RELEASE BUTTON - DIMENSION CHECK DRAWING", 27)
    drawing.text(40, 73, "All dimensions in mm. Separate drawing; original preview and CAD exports are unchanged.", 18)
    drawing.text(40, 101, "Orthographic wireframes include hidden edges. Blue: dimensions; orange: unmeasured trial values.", 17)
    drawing.line((900, 120), (900, 1710))
    drawing.line((30, 790), (1770, 790))

    half = d.face_width / 2
    shell_half = d.shell_width / 2
    rear_y = d.shell_rear_y
    wing_rear = d.wing_center_y - d.wing_height / 2
    wing_front = wing_rear + d.wing_height
    stem_inner = d.wing_inner_gap / 2
    stem_outer = stem_inner + d.wing_stem_width
    stem_middle = (stem_inner + stem_outer) / 2
    wing_top_start = d.depth - d.hook_thickness
    fmt = lambda value: f"{value:.3f}".rstrip("0").rstrip(".")

    plan = lambda x, y: (430 + x * SCALE, 510 - y * SCALE)
    drawing.text(40, 139, "A. REAR / INSIDE VIEW (X-Y)", 21)
    drawing.geometry(shape, lambda point: plan(point.x, point.y))
    drawing.horizontal(plan(-half, 0), plan(half, 0), 172,
                       f"{fmt(d.face_width)} BASE")
    drawing.horizontal(plan(-shell_half, rear_y + d.shell_height),
                       plan(shell_half, rear_y + d.shell_height), 214, fmt(d.shell_width))
    drawing.vertical(plan(-half, 0), plan(0, d.height), 80, fmt(d.height))
    drawing.vertical(plan(-half, 0), plan(-half, d.side_height), 125, fmt(d.side_height))
    drawing.horizontal(plan(-d.pin_diameter / 2, d.pin_center_y),
                       plan(d.pin_diameter / 2, d.pin_center_y), 320,
                       f"DIA {fmt(d.pin_diameter)} PIN")
    drawing.vertical(plan(d.wing_span / 2, wing_rear),
                     plan(d.wing_span / 2, wing_front), 755, f"{fmt(d.wing_height)} WING")
    drawing.vertical(plan(stem_middle, rear_edge_y(d, stem_middle)),
                     plan(stem_middle, wing_rear), 825, f"{fmt(d.wing_rear_clearance)} LOCAL")
    drawing.horizontal(plan(-d.rear_wall_length / 2, rear_y),
                       plan(d.rear_wall_length / 2, rear_y), 566,
                       f"{fmt(d.rear_wall_length)} REAR WALL")
    drawing.horizontal(plan(-d.rear_rim_length / 2, rear_y),
                       plan(d.rear_rim_length / 2, rear_y), 610,
                       f"{fmt(d.rear_rim_length)} RAISED RIM")
    drawing.horizontal(plan(-stem_inner, wing_rear), plan(stem_inner, wing_rear),
                       654, f"{fmt(d.wing_inner_gap)} CLEAR GAP")
    drawing.horizontal(plan(shell_half, wing_front), plan(d.wing_span / 2, wing_front),
                       700, f"{fmt(d.wing_projection)} TOP")
    drawing.text(45, 741, f"Front corners R{fmt(d.front_corner_radius)}; rear concavity "
                 f"{fmt(d.rear_concavity)}: trial values.", color="#aa5913")
    drawing.text(45, 768, f"Front support ends: X = +/-{fmt(d.reinforcement_span / 2)}, aligned to outer stems.")

    elevation = lambda x, z: (1320 + x * SCALE, 510 - z * SCALE)
    drawing.text(935, 139, "B. WIDTH / DEPTH VIEW (X-Z)", 21)
    drawing.geometry(shape, lambda point: elevation(point.x, point.z))
    drawing.horizontal(elevation(-d.wing_span / 2, d.depth), elevation(d.wing_span / 2, d.depth),
                       172, f"{fmt(d.wing_span)} TOP WINGS")
    drawing.vertical(elevation(half, 0), elevation(half, d.overall_depth), 1730,
                     f"{fmt(d.overall_depth)} OVERALL")
    drawing.vertical(elevation(0, 0), elevation(0, d.rear_rim_depth), 1680,
                     f"{fmt(d.rear_rim_depth)} RIM")
    drawing.vertical(elevation(-shell_half, 0), elevation(-shell_half, d.shell_depth), 1000,
                     f"{fmt(d.shell_depth)} SHELL")
    drawing.vertical(elevation(-half, 0), elevation(-half, d.face_thickness), 950,
                     f"{fmt(d.face_thickness)} BASE")
    drawing.horizontal(elevation(stem_inner, wing_top_start),
                       elevation(stem_outer, wing_top_start), 565, fmt(d.wing_stem_width))
    drawing.horizontal(elevation(-stem_outer, d.face_thickness + d.reinforcement_height),
                       elevation(stem_outer, d.face_thickness + d.reinforcement_height), 610,
                       f"{fmt(d.reinforcement_span)} SUPPORT / OUTER STEMS")
    drawing.horizontal(elevation(-half, 0), elevation(half, 0), 655,
                       f"{fmt(d.face_width)} BASE")
    drawing.text(935, 741, f"Z heights {fmt(d.shell_depth)} / {fmt(d.rear_rim_depth)} / "
                 f"{fmt(d.depth)} are measured from the outside face (Z=0).")
    drawing.text(935, 768, f"Half-round trunk ribs: R{fmt(d.wing_rib_radius)}; "
                 f"height {fmt(d.wing_rib_height)} above base.", color="#aa5913")
    corner_point = elevation(
        half - d.bottom_edge_radius * (1 - 2**-0.5),
        d.bottom_edge_radius * (1 - 2**-0.5),
    )
    drawing.line(corner_point, (1665, 685), "#1769a0")
    drawing.text(1665, 710, f"R{fmt(d.bottom_edge_radius)} BOTTOM", 16,
                 "#1769a0", anchor="middle")

    side = lambda y, z: (230 + y * SCALE, 1300 - z * SCALE)
    drawing.text(40, 835, "C. FRONT-TO-BACK / DEPTH VIEW (Y-Z)", 21)
    drawing.text(40, 865, "Low Y = rear; high Y = rounded front. Hidden edges are shown.")
    drawing.geometry(shape, lambda point: side(point.y, point.z))
    drawing.vertical(side(0, 0), side(0, d.overall_depth), 140,
                     f"{fmt(d.overall_depth)} OVERALL")
    drawing.vertical(side(d.pin_center_y, d.face_thickness),
                     side(d.pin_center_y, d.pin_tip_depth), 600,
                     f"{fmt(d.pin_length)} PIN ABOVE BASE")
    drawing.vertical(side(wing_front, wing_top_start), side(wing_front, d.depth), 740,
                     f"{fmt(d.hook_thickness)} TOP THICKNESS")
    drawing.vertical(side(d.height, d.face_thickness),
                     side(d.height, d.face_thickness + d.reinforcement_height), 670,
                     f"{fmt(d.reinforcement_height)} ABOVE BASE")
    drawing.horizontal(side(0, 0), side(d.height, 0), 1360, fmt(d.height))
    drawing.horizontal(side(rear_y, d.face_thickness),
                       side(rear_y + d.shell_height, d.face_thickness), 1405,
                       f"{fmt(d.shell_height)} SHELL")
    drawing.horizontal(side(rear_edge_y(d, stem_middle), d.face_thickness),
                       side(wing_rear, d.face_thickness), 1450,
                       f"{fmt(d.wing_rear_clearance)} REAR CLEARANCE")
    drawing.text(45, 1500, f"Rear clearance uses local base edge at X = +/-{fmt(stem_middle)}.")

    labels = {
        "face_width": "Base width X",
        "wing_projection": "Each top wing projection X",
        "height": "Maximum base height Y",
        "side_height": "Straight side edge Y",
        "depth": "Top wing absolute Z (excluding pin)",
        "shell_width": "Shell outside width X",
        "shell_height": "Shell outside height Y",
        "shell_rear_y": "Fixed shell rear Y (base trim only)",
        "face_thickness": "Solid base thickness Z",
        "pin_diameter": "Central pin diameter",
        "pin_length": "Central pin length ABOVE base",
        "shell_depth": "Shell top absolute Z",
        "wall_thickness": "Shell / curved support wall thickness",
        "rear_rim_width": "Raised rear rim thickness Y",
        "rear_rim_length": "Raised rear rim length X",
        "rear_wall_length": "Extended rear wall length X",
        "rear_rim_depth": "Raised rear rim top absolute Z",
        "wing_stem_width": "Each stem thickness X",
        "wing_inner_gap": "Clear gap between stems X",
        "wing_rear_y": "Fixed stem rear Y (base trim only)",
        "wing_height": "Stem + top wing breadth Y",
        "hook_thickness": "Top wing thickness Z",
        "wing_rib_radius": "TRIAL: outer trunk half-round rib radius",
        "reinforcement_span": "Curved front support outside span X",
        "reinforcement_height": "Curved support height ABOVE base",
        "bottom_edge_radius": "Full Z=0 perimeter edge fillet radius",
        "front_corner_radius": "TRIAL: front corner radius",
        "rear_concavity": "TRIAL: rear midpoint concavity Y",
        "shell_bulge": "TRIAL: shell front arc bulge Y",
    }
    if labels.keys() != vars(d).keys():
        raise RuntimeError("Dimension table must cover every source parameter.")
    drawing.text(935, 835, "D. COMPLETE DIMENSION REGISTER", 21)
    drawing.text(935, 865, "Values correspond to the STEP geometry validated before drawing.")
    drawing.text(935, 902, "FEATURE / AXIS", 16)
    drawing.text(1530, 902, "mm", 16)
    estimated = {"front_corner_radius", "rear_concavity", "shell_bulge", "wing_rib_radius"}
    rows = [(label, getattr(d, name), name in estimated) for name, label in labels.items()]
    rows.extend([
        ("DERIVED: top wing tip span", d.wing_span, False),
        ("DERIVED: outer stem span", d.wing_inner_gap + 2 * d.wing_stem_width, False),
        ("DERIVED: each front support extension X", d.reinforcement_length, False),
        ("DERIVED: front support top absolute Z", d.face_thickness + d.reinforcement_height, False),
        ("DERIVED: local rear clearance Y", d.wing_rear_clearance, False),
        ("DERIVED: trunk rib height ABOVE base", d.wing_rib_height, False),
        ("DERIVED: pin center Y (X=0)", d.pin_center_y, False),
        ("DERIVED: pin tip absolute Z", d.pin_tip_depth, False),
        ("DERIVED: overall depth including pin", d.overall_depth, False),
    ])
    for index, (label, value, trial) in enumerate(rows):
        y = 928 + index * 19
        color = "#aa5913" if trial else "#183047"
        drawing.text(935, y, label, 16, color)
        drawing.text(1530, y, fmt(value), 16, color)
    drawing.text(935, 1695, "No fit tolerance or printer shrinkage allowance has been applied.", 16)
    drawing.line((30, 1720), (1770, 1720))
    drawing.text(40, 1752, "VERIFIED: one valid symmetric CAD solid; specified dimensions and connections pass automated checks.", 18)
    drawing.text(40, 1782, "NOT VERIFIED: physical fit, locking action, print strength, or unmeasured curvature. This is a prototype, not a factory drawing.", 17)
    drawing.text(40, 1812, f"Fit trial: wing span={fmt(d.wing_span)}; base width={fmt(d.face_width)}; "
                 f"rear rim top Z={fmt(d.rear_rim_depth)}. Verify retention and free return after printing.", 17)
    target = folder / "lumix_g6_button_dimensions.svg"
    drawing.save(target)
    print(f"Created {target}")
    print(f"Validated STEP and {len(rows)} dimension-register entries; original preview and CAD files untouched.")


if __name__ == "__main__":
    main()
