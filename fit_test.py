"""
Rail clamp fit test pieces
==========================

Short sections of the monopod's rail clamp, one per JAW_LIP (how far
the jaw lips hook up under the rail's widest point), so the right
value can be found by test fitting before printing the whole monopod.
Everything else comes from params.json, so each piece is the real clamp profile:
fixed half with base plate, recoil lug and nut trap, plus the moving
jaw, held by one M5 x 25 bolt, washer and nut.

Run:
    python fit_test.py                    lips 1.5 2.0 2.5
    python fit_test.py 1.8 2.2            your own values

Output (fit_test/ next to params.json):
    fit_test_plate.stl   every piece laid out flat, ready to print
    fit_<lip>_body.stl / _jaw.stl     the same, one value at a time

Each piece is engraved with its value on the end faces.  Use the
biggest one that goes on without the clamp walls touching the stock
and pulls up snug, with no rocking, when the bolt is done up.  Put that
value into JAW_LIP.
"""

import json
import sys
from pathlib import Path

import cadquery as cq


HERE = Path(__file__).parent
PARAMS_FILE = HERE / "params.json"
OUT_DIR = HERE / "fit_test"

LIPS = [float(arg) for arg in sys.argv[1:]] or [1.5, 2.0, 2.5]
PIECE_LENGTH = 22.0
BOLT_X = -5.0
LUG_X = 5.5


def load_params(path):
    """Flat {name: value} from the grouped file; '_' keys are notes."""

    with open(path, encoding="utf-8") as file:
        groups = json.load(file)
    return {
        name: value
        for group, values in groups.items() if not group.startswith("_")
        for name, value in values.items() if not name.startswith("_")
    }


P = load_params(PARAMS_FILE)


def box(x0, x1, y0, y1, z0, z1):

    return (
        cq.Workplane("XY")
        .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
        .translate((x0, y0, z0))
    )


def cylinder_y(radius, x, z, y0, y1):

    # Built along +Z, turned so it runs along +Y.
    return (
        cq.Workplane("XY").circle(radius).extrude(y1 - y0)
        .rotate((0, 0, 0), (1, 0, 0), -90)
        .translate((x, y0, z))
    )


def profile_yz(points, x0, x1):
    """Closed (y, z) outline extruded along X from x0 to x1."""

    return (
        cq.Workplane("YZ").polyline(points).close().extrude(x1 - x0)
        .translate((x0, 0, 0))
    )


def label_x(text, x_face, y, z, size, depth=0.5):
    """Text cut into the +X end face at x_face, centred on (y, z)."""

    return (
        cq.Workplane("YZ")
        .text(text, size, depth, combine=False, halign="center", valign="center")
        .translate((x_face - depth + 0.01, y, z))
    )


def to_bed(shape):

    bb = shape.val().BoundingBox()
    return shape.translate((-bb.xmin, -bb.ymin, -bb.zmin))


def clamp_pieces(lip):
    """Fixed half (with base plate) and moving jaw, as assembled."""

    rail_half = P["RAIL_WIDTH"] / 2.0
    flank_height = rail_half - P["RAIL_NECK_WIDTH"] / 2.0
    if not 0.5 <= lip <= flank_height - 0.3:
        sys.exit(f"Lip {lip} must be 0.5 - {flank_height - 0.3:.1f}")

    c = P["RAIL_CLEARANCE"]
    floor = P["CLAMP_FLOOR"]
    clamp_y_min = -(rail_half + P["CLAMP_WALL"])
    clamp_y_max = rail_half + P["CLAMP_WALL"]
    clamp_top = floor + flank_height + lip
    cavity_floor = floor - P["FLOOR_GAP"]
    lip_tip_half = rail_half + c - lip
    x0, x1 = -PIECE_LENGTH / 2.0, PIECE_LENGTH / 2.0
    big = 100.0

    # Same profile as generate.py: straight up to the rail's widest
    # point, then the lips follow its lower flank in.
    cavity = [
        (-(rail_half + c), cavity_floor),
        (rail_half + c, cavity_floor),
        (rail_half + c, floor + flank_height),
        (lip_tip_half, clamp_top),
        (lip_tip_half, clamp_top + 1.0),
        (-lip_tip_half, clamp_top + 1.0),
        (-lip_tip_half, clamp_top),
        (-(rail_half + c), floor + flank_height),
    ]

    bolt_hole_radius = (P["BOLT_DIAMETER"] + P["BOLT_HOLE_CLEARANCE"]) / 2.0
    bolt_z = bolt_hole_radius + 1.5
    nut_af = P["NUT_ACROSS_FLATS"] + P["NUT_CLEARANCE"]
    nut_ac = nut_af / 0.8660254
    washer_radius = P["WASHER_DIAMETER"] / 2.0

    block = box(x0, x1, clamp_y_min, clamp_y_max, 0.0, clamp_top).cut(
        profile_yz(cavity, x0 - 1.0, x1 + 1.0)
    )

    split = P["JAW_SPLIT_Y"]
    fixed = block.intersect(box(-big, big, -big, split - P["JAW_GAP"], -1.0, big))
    jaw = block.intersect(box(-big, big, split, big, -1.0, big))

    fixed = fixed.union(
        box(x0, x1, clamp_y_min, clamp_y_max, -P["BASE_PLATE"], 0.0)
    ).union(
        box(
            LUG_X - P["LUG_WIDTH"] / 2.0, LUG_X + P["LUG_WIDTH"] / 2.0,
            -(rail_half + c + 0.01), split - P["JAW_GAP"],
            cavity_floor - 0.01, floor + P["LUG_HEIGHT"]
        )
    )
    jaw = jaw.union(
        box(
            LUG_X - P["LUG_WIDTH"] / 2.0, LUG_X + P["LUG_WIDTH"] / 2.0,
            split, rail_half + c + 0.01,
            cavity_floor - 0.01, floor + P["LUG_HEIGHT"]
        )
    )

    # Bolt, nut trap and washer relief exactly as generate.py places them.
    head_y = clamp_y_max - 2.0 * c + P["WASHER_THICKNESS"]
    nut_inner_y = head_y - P["BOLT_LENGTH"] + P["NUT_THICKNESS"] + 0.5
    hole = cylinder_y(bolt_hole_radius, BOLT_X, bolt_z, -big, big)
    fixed = fixed.cut(hole).cut(
        box(
            BOLT_X - nut_ac / 2.0 - 0.2, BOLT_X + nut_ac / 2.0 + 0.2,
            clamp_y_min - 1.0, nut_inner_y,
            bolt_z - nut_af / 2.0, bolt_z + nut_af / 2.0
        )
    ).cut(
        box(
            BOLT_X - washer_radius - 0.5, BOLT_X + washer_radius + 0.5,
            clamp_y_max - P["JAW_GAP"] - 0.5, big,
            bolt_z - washer_radius - 0.5, 0.01
        )
    )
    jaw = jaw.cut(hole)

    text = f"{lip:.1f}"
    fixed = fixed.cut(label_x(text, x1, 0.0, -P["BASE_PLATE"] / 2.0, 3.0))
    jaw = jaw.cut(label_x(text, x1, (split + clamp_y_max) / 2.0, bolt_z + 4.0, 2.5))

    return fixed, jaw


def main():

    OUT_DIR.mkdir(exist_ok=True)
    plate = None
    row_y = 0.0

    for lip in LIPS:
        fixed, jaw = clamp_pieces(lip)

        # Fixed half on its base plate; jaw on its outer (+Y) face.
        fixed_print = to_bed(fixed)
        jaw_print = to_bed(jaw.rotate((0, 0, 0), (1, 0, 0), -90))

        stem = f"fit_{lip:.1f}"
        cq.exporters.export(fixed_print, str(OUT_DIR / f"{stem}_body.stl"))
        cq.exporters.export(jaw_print, str(OUT_DIR / f"{stem}_jaw.stl"))

        fixed_width = fixed_print.val().BoundingBox().ylen
        row = fixed_print.translate((0, row_y, 0)).union(
            jaw_print.translate((PIECE_LENGTH + 6.0, row_y, 0))
        )
        plate = row if plate is None else plate.union(row)
        row_y += fixed_width + 6.0
        above = P["RAIL_WIDTH"] / 2.0 - P["RAIL_NECK_WIDTH"] / 2.0 + lip
        print(f"  {stem}: clamp walls reach {above:.1f} mm above the rail top face")

    cq.exporters.export(plate, str(OUT_DIR / "fit_test_plate.stl"))
    print(f"Wrote {OUT_DIR / 'fit_test_plate.stl'} and one body + jaw per lip")


if __name__ == "__main__":
    main()
