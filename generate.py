"""
Parametric Picatinny monopod generator
======================================

Units: millimetres

A rear monopod that clamps to a Picatinny (MIL-STD-1913) rail.  A
knurled thumb wheel, captured in a pocket in the housing, turns on a
threaded leg; the leg is keyed so it cannot spin, so turning the
wheel raises and lowers the leg.  The leg ends in a sled that runs
along the rifle so it slides straight back under recoil.

Requires:
    CadQuery, matplotlib (preview only)

Run:
    python generate.py                 (reads params.json)
    python generate.py other.json      (reads a different parameter file)

Output (see "output" in the parameter file):
    monopod_body.stl     clamp body + fixed jaw + housing
    monopod_jaw.stl      moving clamp jaw
    monopod_wheel.stl    thumb wheel (internal thread)
    monopod_leg.stl      threaded leg + sled foot
    monopod_preview.png  assembled / section / part views

Every STL is already in its print orientation (flat face on the bed,
no supports needed).

Hardware:
    BOLT_COUNT x M5 socket head bolts + M5 hex nuts (length printed
    at the end of the run).

Assembly:
    1. Drop the nuts into the hex pockets on the body.
    2. Slide the wheel into the pocket from the open (+Y) side.
    3. Push the leg up through the bottom of the housing, groove
       lined up with the key rib, and turn the wheel to draw it in.
    4. Put the clamp on the rail, add the moving jaw and run the
       bolts through the rail slots into the nuts.
"""

import json
import math
import sys
from pathlib import Path

import cadquery as cq


# ============================================================
# PARAMETERS
# ============================================================

HERE = Path(__file__).parent

PARAMS_FILE = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else HERE / "params.json"
)


def load_params(path):
    """
    Read a grouped parameter file into a flat {name: value} dict.
    Groups and keys starting with '_' are notes and are skipped.
    """

    try:
        with open(path, encoding="utf-8") as file:
            groups = json.load(file)
    except FileNotFoundError:
        sys.exit(f"Parameter file not found: {path}")
    except json.JSONDecodeError as error:
        sys.exit(f"{path}: invalid JSON - {error}")

    flat = {}

    for group, values in groups.items():
        if group.startswith("_"):
            continue
        for name, value in values.items():
            if name.startswith("_"):
                continue
            if name in flat:
                sys.exit(f"{path}: '{name}' appears more than once")
            flat[name] = value

    return flat


_params = load_params(PARAMS_FILE)


def param(name):
    try:
        return _params.pop(name)
    except KeyError:
        sys.exit(f"{PARAMS_FILE}: missing parameter '{name}'")


# Rail
RAIL_TOP_WIDTH = param("RAIL_TOP_WIDTH")
RAIL_APEX_WIDTH = param("RAIL_APEX_WIDTH")
RAIL_SLOT_PITCH = param("RAIL_SLOT_PITCH")
RAIL_SLOT_WIDTH = param("RAIL_SLOT_WIDTH")
RAIL_SLOT_DEPTH = param("RAIL_SLOT_DEPTH")

# Clamp
BODY_LENGTH = param("BODY_LENGTH")
CLAMP_WALL = param("CLAMP_WALL")
CLAMP_FLOOR = param("CLAMP_FLOOR")
JAW_DEPTH = param("JAW_DEPTH")
RAIL_CLEARANCE = param("RAIL_CLEARANCE")
FLOOR_GAP = param("FLOOR_GAP")
JAW_SPLIT_Y = param("JAW_SPLIT_Y")
JAW_GAP = param("JAW_GAP")
BOLT_COUNT = param("BOLT_COUNT")
BOLT_SPACING_SLOTS = param("BOLT_SPACING_SLOTS")
BOLT_DIAMETER = param("BOLT_DIAMETER")
BOLT_HOLE_CLEARANCE = param("BOLT_HOLE_CLEARANCE")
BOLT_FROM_RAIL_TOP = param("BOLT_FROM_RAIL_TOP")
NUT_ACROSS_FLATS = param("NUT_ACROSS_FLATS")
NUT_THICKNESS = param("NUT_THICKNESS")
NUT_CLEARANCE = param("NUT_CLEARANCE")
NUT_RECESS = param("NUT_RECESS")
BASE_PLATE = param("BASE_PLATE")

# Housing
HOUSING_WIDTH = param("HOUSING_WIDTH")
TRAVEL = param("TRAVEL")
LOWER_GUIDE = param("LOWER_GUIDE")
POCKET_CLEARANCE_DIA = param("POCKET_CLEARANCE_DIA")
POCKET_CLEARANCE_HEIGHT = param("POCKET_CLEARANCE_HEIGHT")
BORE_CLEARANCE = param("BORE_CLEARANCE")
EDGE_RADIUS = param("EDGE_RADIUS")

# Thread
THREAD_MAJOR_DIAMETER = param("THREAD_MAJOR_DIAMETER")
THREAD_PITCH = param("THREAD_PITCH")
THREAD_DEPTH = param("THREAD_DEPTH")
THREAD_CLEARANCE = param("THREAD_CLEARANCE")

# Leg
KEY_WIDTH = param("KEY_WIDTH")
KEY_GROOVE_RADIUS = param("KEY_GROOVE_RADIUS")
KEY_CLEARANCE = param("KEY_CLEARANCE")
LEG_EXPOSED = param("LEG_EXPOSED")
COLLAR_HEIGHT = param("COLLAR_HEIGHT")

# Sled foot
SLED_LENGTH = param("SLED_LENGTH")
SLED_WIDTH = param("SLED_WIDTH")
SLED_THICKNESS = param("SLED_THICKNESS")
SLED_TIP_HEIGHT = param("SLED_TIP_HEIGHT")
SLED_TIP_THICKNESS = param("SLED_TIP_THICKNESS")
SLED_CURVE_RADIUS = param("SLED_CURVE_RADIUS")
SLED_TIP_FILLET = param("SLED_TIP_FILLET")
SLED_CORNER_RADIUS = param("SLED_CORNER_RADIUS")

# Wheel
WHEEL_DIAMETER = param("WHEEL_DIAMETER")
WHEEL_THICKNESS = param("WHEEL_THICKNESS")
KNURL_COUNT = param("KNURL_COUNT")
KNURL_RADIUS = param("KNURL_RADIUS")
WHEEL_CHAMFER = param("WHEEL_CHAMFER")

# Output
OUTPUT_PREFIX = param("OUTPUT_PREFIX")
PREVIEW = param("PREVIEW")
PREVIEW_FILE = param("PREVIEW_FILE")
PREVIEW_RAIL = param("PREVIEW_RAIL")


# A typo in a key would otherwise be silently ignored.
if _params:
    sys.exit(
        f"{PARAMS_FILE}: unknown parameter(s): "
        + ", ".join(sorted(_params))
    )

print(f"Parameters: {PARAMS_FILE}")


# ============================================================
# DERIVED DIMENSIONS
# ============================================================

# Coordinates (assembled, rifle upside up):
#
#   X  along the rail
#   Y  across the rifle (moving jaw and wheel opening on +Y)
#   Z  up; z = 0 is the top of the base plate, the rail top sits
#      at z = CLAMP_FLOOR and the clamp top at CLAMP_FLOOR + JAW_DEPTH
#
#        rail  ─────────────┐   ┌─ moving jaw
#   ┌──┐  ▼▼▼▼▼▼▼▼▼▼▼▼  ┌──┐  │
#   │  └──────────────┘  │  │  ── z = CLAMP_FLOOR
#   ├────────────────────┴──┤   ── z = 0      base plate
#   └──┐   │ leg │      ┌───┘   ── z = -BASE_PLATE
#      │   │     │      │        upper guide (TRAVEL)
#    ══╪═══╪═════╪══════╪══      thumb wheel pocket
#      │   │     │      │        lower guide
#      └───┤     ├──────┘
#          └──┬──┘
#     ╱▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀╲          sled foot (runs along X)

rail_half = RAIL_TOP_WIDTH / 2.0
apex_half = RAIL_APEX_WIDTH / 2.0
flank_height = rail_half - apex_half          # 45 degree flanks

clamp_width = RAIL_TOP_WIDTH + 2.0 * CLAMP_WALL
clamp_top = CLAMP_FLOOR + JAW_DEPTH
half_length = BODY_LENGTH / 2.0

bolt_z = CLAMP_FLOOR + BOLT_FROM_RAIL_TOP
bolt_hole_radius = (BOLT_DIAMETER + BOLT_HOLE_CLEARANCE) / 2.0
bolt_spacing = BOLT_SPACING_SLOTS * RAIL_SLOT_PITCH
bolt_xs = [
    (index - (BOLT_COUNT - 1) / 2.0) * bolt_spacing
    for index in range(BOLT_COUNT)
]
nut_pocket_depth = NUT_THICKNESS + NUT_RECESS

thread_major_radius = THREAD_MAJOR_DIAMETER / 2.0
thread_minor_radius = thread_major_radius - THREAD_DEPTH

# 45 degree flanks: the ridge is THREAD_DEPTH wider on each side at
# the root than at the crest.  Crest = pitch / 2 - depth keeps the
# male and female ridges the same width.
thread_crest = THREAD_PITCH / 2.0 - THREAD_DEPTH
thread_root = thread_crest + 2.0 * THREAD_DEPTH

bore_radius = thread_major_radius + BORE_CLEARANCE

pocket_radius = (WHEEL_DIAMETER + POCKET_CLEARANCE_DIA) / 2.0
pocket_height = WHEEL_THICKNESS + POCKET_CLEARANCE_HEIGHT
pocket_top = -BASE_PLATE - TRAVEL
pocket_bottom = pocket_top - pocket_height
housing_bottom = pocket_bottom - LOWER_GUIDE

wheel_bottom = pocket_bottom + POCKET_CLEARANCE_HEIGHT / 2.0
wheel_top = wheel_bottom + WHEEL_THICKNESS

leg_thread_length = (-BASE_PLATE - housing_bottom) + LEG_EXPOSED

# Fully retracted: leg top against the bore roof.
# Fully extended:  leg top level with the top of the wheel.
actual_travel = -BASE_PLATE - wheel_top


# ------------------------------------------------------------
# Sanity checks
# ------------------------------------------------------------

problems = []

if thread_crest <= 0.2:
    problems.append(
        f"THREAD_DEPTH {THREAD_DEPTH} is too deep for THREAD_PITCH "
        f"{THREAD_PITCH} (crest would be {thread_crest:.2f} mm)"
    )

if thread_root + THREAD_CLEARANCE >= THREAD_PITCH:
    problems.append("THREAD_CLEARANCE leaves no ridge in the wheel")

if KEY_GROOVE_RADIUS >= thread_minor_radius:
    problems.append(
        f"KEY_GROOVE_RADIUS {KEY_GROOVE_RADIUS} must be below the thread "
        f"minor radius {thread_minor_radius:.2f}"
    )

if BOLT_FROM_RAIL_TOP + BOLT_DIAMETER / 2.0 > RAIL_SLOT_DEPTH:
    problems.append(
        "Bolt would hit the bottom of the rail slot: lower "
        "BOLT_FROM_RAIL_TOP or BOLT_DIAMETER"
    )

if BOLT_DIAMETER > RAIL_SLOT_WIDTH:
    problems.append("BOLT_DIAMETER is wider than RAIL_SLOT_WIDTH")

if pocket_radius >= half_length - 2.0:
    problems.append(
        "WHEEL_DIAMETER leaves less than 2 mm of housing wall at the "
        "ends: raise BODY_LENGTH or shrink the wheel"
    )

if WHEEL_DIAMETER / 2.0 <= HOUSING_WIDTH / 2.0 + 2.0:
    problems.append("Wheel does not stick out past the housing sides")

if bore_radius >= HOUSING_WIDTH / 2.0 - 1.5:
    problems.append("HOUSING_WIDTH is too narrow for the leg bore")

if not (-rail_half < JAW_SPLIT_Y < rail_half):
    problems.append("JAW_SPLIT_Y must be inside the rail width")

if bolt_xs and max(abs(x) for x in bolt_xs) + bolt_hole_radius > half_length - 2.0:
    problems.append("Bolts do not fit in BODY_LENGTH")

if COLLAR_HEIGHT >= LEG_EXPOSED:
    problems.append("COLLAR_HEIGHT must be less than LEG_EXPOSED or it jams the housing")

if SLED_CURVE_RADIUS * math.sqrt(0.5) >= SLED_TIP_HEIGHT - SLED_TIP_THICKNESS / 2.0:
    problems.append("SLED_CURVE_RADIUS is too big for SLED_TIP_HEIGHT")

if SLED_TIP_HEIGHT <= SLED_THICKNESS + SLED_TIP_FILLET:
    problems.append("SLED_TIP_HEIGHT must clear the deck plus SLED_TIP_FILLET")

if SLED_LENGTH / 2.0 - SLED_TIP_THICKNESS - SLED_TIP_FILLET <= thread_major_radius + COLLAR_HEIGHT:
    problems.append("SLED_LENGTH is too short for the tips and the leg collar")

if problems:
    print()
    for problem in problems:
        print(f"ERROR: {problem}")
    sys.exit(1)


# ============================================================
# HELPERS
# ============================================================

def box(x0, x1, y0, y1, z0, z1):

    return (
        cq.Workplane("XY")
        .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
        .translate((x0, y0, z0))
    )


def cylinder_z(radius, z0, z1, x=0.0, y=0.0):

    return (
        cq.Workplane("XY")
        .circle(radius)
        .extrude(z1 - z0)
        .translate((x, y, z0))
    )


def along_y(shape, y0):
    """Turn a shape extruded up +Z from z = 0 so it runs along +Y from y0."""

    return shape.rotate((0, 0, 0), (1, 0, 0), -90).translate((0, y0, 0))


def cylinder_y(radius, x, z, y0, y1):

    return along_y(
        cq.Workplane("XY").circle(radius).extrude(y1 - y0),
        y0
    ).translate((x, 0, z))


def hex_y(across_flats, x, z, y0, y1):
    """Hex prism along Y with flats top and bottom."""

    across_corners = across_flats / math.cos(math.radians(30))

    return along_y(
        cq.Workplane("XY").polygon(6, across_corners).extrude(y1 - y0),
        y0
    ).translate((x, 0, z))


def profile_yz(points, x0, x1):
    """Extrude a closed (y, z) polygon along X from x0 to x1."""

    return (
        cq.Workplane("YZ")
        .polyline(points)
        .close()
        .extrude(x1 - x0)
        .translate((x0, 0, 0))
    )


def thread_ridge(root_radius, depth, crest, root, z0, z1):
    """
    Helical thread ridge from root_radius out to root_radius + depth,
    covering z0..z1 (it overruns both ends by one pitch; trim it with
    an intersect or let a cut overrun).  The ridge sinks 0.3 mm into
    the core so the union is clean.
    """

    sink = 0.3
    inner = root_radius - sink
    outer = root_radius + depth

    height = (z1 - z0) + 2.0 * THREAD_PITCH
    base = z0 - THREAD_PITCH

    # (radius, z) corners of the ridge cross-section.
    outline = [
        (inner, -root / 2.0),
        (root_radius, -root / 2.0),
        (outer, -crest / 2.0),
        (outer, crest / 2.0),
        (root_radius, root / 2.0),
        (inner, root / 2.0),
    ]

    # One exact helix through each corner, ruled surfaces between
    # them, flat caps at the ends.  (A helical sweep gives solids
    # that OCC booleans handle erratically - some lengths silently
    # lose the core.)
    helices = [
        cq.Wire.makeHelix(
            THREAD_PITCH, height, radius,
            center=cq.Vector(0, 0, base + dz)
        )
        for radius, dz in outline
    ]

    faces = [
        cq.Face.makeRuledSurface(helices[i], helices[(i + 1) % len(helices)])
        for i in range(len(helices))
    ]

    end_angle = 2.0 * math.pi * height / THREAD_PITCH

    for angle, rise in [(0.0, 0.0), (end_angle, height)]:
        cap = cq.Wire.makePolygon(
            [
                cq.Vector(
                    radius * math.cos(angle),
                    radius * math.sin(angle),
                    base + dz + rise
                )
                for radius, dz in outline
            ],
            close=True
        )
        faces.append(cq.Face.makeFromWires(cap))

    ridge = cq.Solid.makeSolid(cq.Shell.makeShell(faces))

    return cq.Workplane("XY").add(ridge)


# ============================================================
# RAIL CAVITY
# ============================================================

# Rail top faces down into the clamp (the rail is on the rifle above).
# Half-width of the rail, measured from its top surface:
#   0              rail_half          (top edge)
#   flank_height   apex_half          (point of the V, 45 degrees in)
#   above that     widens again at 45 degrees towards the rifle
# The jaw lips fill the V; the clamp top stops at JAW_DEPTH.

cavity_floor = CLAMP_FLOOR - FLOOR_GAP
c = RAIL_CLEARANCE

lip_top_half = apex_half + c + (JAW_DEPTH - flank_height)

cavity_points = [
    (-(rail_half + c), cavity_floor),
    (rail_half + c, cavity_floor),
    (rail_half + c, CLAMP_FLOOR),
    (apex_half + c, CLAMP_FLOOR + flank_height),
    (lip_top_half + 1.0, clamp_top + 1.0),
    (-(lip_top_half + 1.0), clamp_top + 1.0),
    (-(apex_half + c), CLAMP_FLOOR + flank_height),
    (-(rail_half + c), CLAMP_FLOOR),
]


# ============================================================
# CLAMP BLOCK -> FIXED HALF + MOVING JAW
# ============================================================

clamp_block = box(
    -half_length, half_length,
    -clamp_width / 2.0, clamp_width / 2.0,
    0.0, clamp_top
)

clamp_block = clamp_block.cut(
    profile_yz(cavity_points, -half_length - 1.0, half_length + 1.0)
)

for x in bolt_xs:
    clamp_block = clamp_block.cut(
        cylinder_y(
            bolt_hole_radius, x, bolt_z,
            -clamp_width, clamp_width
        )
    )

big = clamp_width

clamp_fixed = clamp_block.intersect(
    box(-big, big, -big, JAW_SPLIT_Y - JAW_GAP, -1.0, clamp_top + 1.0)
)

jaw = clamp_block.intersect(
    box(-big, big, JAW_SPLIT_Y, big, -1.0, clamp_top + 1.0)
)

# Nut pockets on the fixed (-Y) side.  With the nut this close to
# the rail they may break out of the clamp top; the hex sides still
# stop the nut turning.
for x in bolt_xs:
    clamp_fixed = clamp_fixed.cut(
        hex_y(
            NUT_ACROSS_FLATS + NUT_CLEARANCE, x, bolt_z,
            -clamp_width / 2.0 - 1.0,
            -clamp_width / 2.0 + nut_pocket_depth
        )
    )


# ============================================================
# BODY: FIXED CLAMP + BASE PLATE + HOUSING
# ============================================================

base_plate = box(
    -half_length, half_length,
    -clamp_width / 2.0, clamp_width / 2.0,
    -BASE_PLATE, 0.0
)

housing = box(
    -half_length, half_length,
    -HOUSING_WIDTH / 2.0, HOUSING_WIDTH / 2.0,
    housing_bottom, -BASE_PLATE + 0.01
)

if EDGE_RADIUS > 0:
    try:
        housing = housing.edges("|Z").fillet(EDGE_RADIUS)
        base_plate = base_plate.edges("|Z").fillet(EDGE_RADIUS)
    except Exception as error:
        print(f"WARNING: edge fillet skipped: {error}")

body = clamp_fixed.union(base_plate).union(housing)

# Leg bore, up to the underside of the base plate.
body = body.cut(cylinder_z(bore_radius, housing_bottom - 1.0, -BASE_PLATE))

# Key rib on the -X side of the bore; it runs in the leg's groove.
rib_half = KEY_WIDTH / 2.0 - KEY_CLEARANCE
rib = box(
    -(bore_radius + 0.5), -(KEY_GROOVE_RADIUS + KEY_CLEARANCE),
    -rib_half, rib_half,
    housing_bottom, -BASE_PLATE + 0.01
)
body = body.union(rib)

# Thumb wheel pocket: round, plus a slot out of the +Y side so the
# wheel slides in sideways.  Cut after the rib so the rib stops at
# the wheel.
pocket = cylinder_z(pocket_radius, pocket_bottom, pocket_top).union(
    box(
        -pocket_radius, pocket_radius,
        0.0, clamp_width,
        pocket_bottom, pocket_top
    )
)
body = body.cut(pocket)

# Lead-in chamfer at the bottom of the bore.
body = body.cut(
    cq.Workplane("XY")
    .circle(bore_radius + 1.0)
    .workplane(offset=1.0)
    .circle(bore_radius)
    .loft()
    .translate((0, 0, housing_bottom))
)


# ============================================================
# THUMB WHEEL
# ============================================================

print("Building wheel thread ...")

wheel_radius = WHEEL_DIAMETER / 2.0

wheel = (
    cq.Workplane("XY")
    .circle(wheel_radius)
    .extrude(WHEEL_THICKNESS)
    .edges()
    .chamfer(WHEEL_CHAMFER)
)

for index in range(KNURL_COUNT):
    angle = 2.0 * math.pi * index / KNURL_COUNT
    wheel = wheel.cut(
        cylinder_z(
            KNURL_RADIUS,
            -1.0, WHEEL_THICKNESS + 1.0,
            wheel_radius * math.cos(angle),
            wheel_radius * math.sin(angle)
        )
    )

# Internal thread: cut a male thread grown by THREAD_CLEARANCE.
female_root = thread_minor_radius + THREAD_CLEARANCE

wheel = wheel.cut(cylinder_z(female_root, -1.0, WHEEL_THICKNESS + 1.0))
wheel = wheel.cut(
    thread_ridge(
        female_root,
        THREAD_DEPTH,
        thread_crest + THREAD_CLEARANCE,
        thread_root + THREAD_CLEARANCE,
        -1.0, WHEEL_THICKNESS + 1.0
    )
)

# Countersink both ends so the thread starts cleanly.
sink_radius = thread_major_radius + THREAD_CLEARANCE + 0.6
sink_depth = sink_radius - female_root

for z0, z1, r0, r1 in [
    (-0.01, sink_depth, sink_radius, female_root),
    (WHEEL_THICKNESS - sink_depth, WHEEL_THICKNESS + 0.01, female_root, sink_radius),
]:
    wheel = wheel.cut(
        cq.Workplane("XY")
        .workplane(offset=z0)
        .circle(r0)
        .workplane(offset=z1 - z0)
        .circle(r1)
        .loft()
    )


# ============================================================
# LEG
# ============================================================

print("Building leg thread ...")

# Built in print orientation: sled on the bed at z = 0.
#
# The sled runs along the rail (X) so the rifle can slide straight
# back under recoil instead of the foot digging in.  Both ends curl
# up like sledge runners so it rides over the bag or bench edge.
# The leg is keyed, so the sled always stays lined up with the rifle.
#
#   side view:   ╭╮                              ╭╮   rounded tips
#                ││╲____________________________╱││   concave fillet into the deck
#                ╰╮                              ╭╯   runner curve
#                  ╲____________________________╱     45 degree start
#
# The runner curve leaves the flat bottom at 45 degrees and turns
# up to vertical, so no overhang is ever worse than 45 degrees and
# the part still prints without supports.

x_end = SLED_LENGTH / 2.0
r = SLED_CURVE_RADIUS
s45 = math.sqrt(0.5)
tip_r = SLED_TIP_THICKNESS / 2.0
f = SLED_TIP_FILLET

curve_top = r * s45                          # where the runner turns vertical
curve_start = x_end - r * (1.0 - s45)        # where it leaves the flat bottom
inner_x = x_end - SLED_TIP_THICKNESS         # inner face of the tip


def runner_mid(angle_deg):
    """Point on the runner curve (centre (x_end - r, curve_top))."""

    a = math.radians(angle_deg)
    return (x_end - r + r * math.cos(a), curve_top + r * math.sin(a))


def end_points(sign):
    """Profile from the bottom-start of one end round to the deck, x scaled by sign."""

    def p(x, z):
        return (sign * x, z)

    return [
        ("arc", p(*runner_mid(-22.5)), p(x_end, curve_top)),
        ("line", p(x_end, SLED_TIP_HEIGHT - tip_r)),
        ("arc", p(x_end - tip_r, SLED_TIP_HEIGHT), p(inner_x, SLED_TIP_HEIGHT - tip_r)),
        ("line", p(inner_x, SLED_THICKNESS + f)),
        ("arc", p(inner_x - f + f * s45, SLED_THICKNESS + f - f * s45), p(inner_x - f, SLED_THICKNESS)),
    ]


def reverse(segments, start):
    """Walk a segment list backwards, starting from where it ended."""

    points = [start] + [segment[-1] for segment in segments]
    backwards = []
    for index in range(len(segments) - 1, -1, -1):
        kind = segments[index][0]
        target = points[index]
        if kind == "arc":
            backwards.append(("arc", segments[index][1], target))
        else:
            backwards.append(("line", target))
    return backwards


profile = cq.Workplane("XZ").moveTo(-curve_start, 0.0).lineTo(curve_start, 0.0)

for segment in end_points(1.0):
    if segment[0] == "arc":
        profile = profile.threePointArc(segment[1], segment[2])
    else:
        profile = profile.lineTo(*segment[1])

profile = profile.lineTo(-(inner_x - f), SLED_THICKNESS)

for segment in reverse(end_points(-1.0), (-curve_start, 0.0)):
    if segment[0] == "arc":
        profile = profile.threePointArc(segment[1], segment[2])
    else:
        profile = profile.lineTo(*segment[1])

sled = profile.close().extrude(SLED_WIDTH / 2.0, both=True)

# Round the corners in plan view so the tips look like runners.
sled = sled.intersect(
    cq.Workplane("XY")
    .rect(SLED_LENGTH, SLED_WIDTH)
    .extrude(SLED_TIP_HEIGHT + 1.0)
    .edges("|Z")
    .fillet(SLED_CORNER_RADIUS)
    .translate((0, 0, -0.5))
)

leg_z0 = SLED_THICKNESS
leg_z1 = SLED_THICKNESS + leg_thread_length

# 45 degree collar where the leg meets the sled, to spread the
# recoil load.  It stays out of the housing (COLLAR_HEIGHT <
# LEG_EXPOSED).
collar = (
    cq.Workplane("XY")
    .circle(thread_minor_radius + COLLAR_HEIGHT)
    .workplane(offset=COLLAR_HEIGHT)
    .circle(thread_minor_radius - 0.1)
    .loft()
    .translate((0, 0, leg_z0 - 0.01))
)

# Thread overruns both ends: the bottom end is buried in the foot,
# the top is cut flat, so no thread face is coplanar with anything.
leg = cylinder_z(thread_minor_radius, leg_z0 - 1.0, leg_z1 + 1.0).union(
    thread_ridge(
        thread_minor_radius,
        THREAD_DEPTH,
        thread_crest,
        thread_root,
        leg_z0 - 1.0, leg_z1 + 1.0
    )
)

leg = leg.cut(box(-50, 50, -50, 50, leg_z1, leg_z1 + 20.0))

# 45 degree lead-in at the top of the thread.
lead_in = cylinder_z(thread_major_radius + 2.0, leg_z1 - THREAD_DEPTH - 0.5, leg_z1 + 0.01).cut(
    cq.Workplane("XY")
    .circle(thread_major_radius + 0.5)
    .workplane(offset=THREAD_DEPTH + 0.5)
    .circle(thread_minor_radius - 0.4)
    .loft()
    .translate((0, 0, leg_z1 - THREAD_DEPTH - 0.5))
)
leg = leg.cut(lead_in)

leg = leg.union(sled).union(collar)

# The thread overrun pokes a little out of the bottom of the sled.
leg = leg.cut(box(-100, 100, -100, 100, -20.0, 0.0))

# Anti-rotation groove on the -X side (matches the rib in the bore).
# It starts above the collar; that part never enters the housing.
leg = leg.cut(
    box(
        -(thread_major_radius + 1.0), -KEY_GROOVE_RADIUS,
        -KEY_WIDTH / 2.0, KEY_WIDTH / 2.0,
        leg_z0 + COLLAR_HEIGHT, leg_z1 + 1.0
    )
)


# ============================================================
# EXPORT (print orientation)
# ============================================================

def to_bed(shape):
    """Move a shape so its lowest point is on z = 0."""

    bb = shape.val().BoundingBox()
    return shape.translate((0, 0, -bb.zmin))


# Moving jaw printed on its outer face (+Y down): the 45 degree lip
# then needs no support.
jaw_print = jaw.rotate((0, 0, 0), (1, 0, 0), -90)

parts = {
    "body": to_bed(body),
    "jaw": to_bed(jaw_print),
    "wheel": wheel,
    "leg": leg,
}

out_dir = PARAMS_FILE.resolve().parent
written = []

for name, shape in parts.items():
    filename = out_dir / f"{OUTPUT_PREFIX}_{name}.stl"
    cq.exporters.export(
        shape, str(filename),
        tolerance=0.02, angularTolerance=0.1
    )
    written.append(filename.name)


# ============================================================
# PREVIEW IMAGE
# ============================================================

# Renders the assembly (retracted, extended, cut in half) and each
# part to a PNG so the design can be checked without a slicer.
# Needs matplotlib; skipped if it is missing.


def leg_assembled(extension):
    """Leg in assembly position, lowered `extension` mm from retracted."""

    return leg.translate((0, 0, -BASE_PLATE - leg_z1 - extension))


def wheel_assembled():
    return wheel.translate((0, 0, wheel_bottom))


def rail_ghost():

    rail_length = BODY_LENGTH + 3.0 * RAIL_SLOT_PITCH
    rail_points = [
        (-rail_half, CLAMP_FLOOR),
        (rail_half, CLAMP_FLOOR),
        (apex_half, CLAMP_FLOOR + flank_height),
        (rail_half, CLAMP_FLOOR + 2.0 * flank_height),
        (rail_half, CLAMP_FLOOR + 9.4),
        (-rail_half, CLAMP_FLOOR + 9.4),
        (-rail_half, CLAMP_FLOOR + 2.0 * flank_height),
        (-apex_half, CLAMP_FLOOR + flank_height),
    ]
    rail = profile_yz(rail_points, -rail_length / 2.0, rail_length / 2.0)

    # Slots lined up with the bolts.
    offset = (bolt_xs[0] if bolt_xs else 0.0) % RAIL_SLOT_PITCH
    count = int(rail_length / RAIL_SLOT_PITCH) + 2
    for index in range(-count, count + 1):
        x = offset + index * RAIL_SLOT_PITCH
        if abs(x) + RAIL_SLOT_WIDTH / 2.0 > rail_length / 2.0 - 2.0:
            continue
        rail = rail.cut(
            box(
                x - RAIL_SLOT_WIDTH / 2.0, x + RAIL_SLOT_WIDTH / 2.0,
                -rail_half - 1.0, rail_half + 1.0,
                CLAMP_FLOOR - 1.0, CLAMP_FLOOR + RAIL_SLOT_DEPTH
            )
        )

    return rail


def bolts_ghost():

    shapes = None
    head_radius = BOLT_DIAMETER * 0.8
    for x in bolt_xs:
        bolt = cylinder_y(
            BOLT_DIAMETER / 2.0, x, bolt_z,
            -clamp_width / 2.0 + NUT_RECESS, clamp_width / 2.0
        ).union(
            cylinder_y(
                head_radius, x, bolt_z,
                clamp_width / 2.0, clamp_width / 2.0 + BOLT_DIAMETER
            )
        ).union(
            hex_y(
                NUT_ACROSS_FLATS, x, bolt_z,
                -clamp_width / 2.0 + NUT_RECESS,
                -clamp_width / 2.0 + nut_pocket_depth
            )
        )
        shapes = bolt if shapes is None else shapes.union(bolt)
    return shapes


COLORS = {
    "body": (0.30, 0.36, 0.42),
    "jaw": (0.85, 0.45, 0.20),
    "wheel": (0.25, 0.60, 0.45),
    "leg": (0.62, 0.72, 0.80),
    "rail": (0.80, 0.80, 0.80),
    "bolt": (0.55, 0.55, 0.58),
}


def mesh(shape, color):

    import numpy as np

    vertices, triangles = shape.val().tessellate(0.05, 0.2)
    xyz = np.array([(v.x, v.y, v.z) for v in vertices])
    tris = xyz[np.array(triangles)]

    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals = normals / np.where(lengths == 0.0, 1.0, lengths)[:, None]

    light = np.array([-0.4, -0.7, 0.6])
    light = light / np.linalg.norm(light)

    shade = 0.35 + 0.65 * np.abs(normals @ light)
    colors = shade[:, None] * np.array(color)

    return tris, colors


def render_preview(filename):

    import numpy as np
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    jaw_closed = jaw.translate((0, -JAW_GAP, 0))

    def assembly(extension, with_rail=True):
        items = [
            (body, "body"),
            (jaw_closed, "jaw"),
            (wheel_assembled(), "wheel"),
            (leg_assembled(extension), "leg"),
        ]
        if bolt_xs:
            items.append((bolts_ghost(), "bolt"))
        if with_rail and PREVIEW_RAIL:
            items.append((rail_ghost(), "rail"))
        return items

    # Section through the leg axis (keeps the +Y half, viewed from -Y).
    keep = box(-200, 200, 0.0, 200, -400, 200)
    section = [
        (shape.intersect(keep), color)
        for shape, color in assembly(actual_travel / 2.0)
    ]

    views = [
        ("Assembled - retracted", assembly(0.0), 20, -55),
        (f"Extended {actual_travel:.0f} mm", assembly(actual_travel), 20, -55),
        ("Section (mid travel)", section, 0, -90),
        ("End view (along rail)", assembly(0.0), 0, 0),
        ("Body", [(body, "body")], 25, -60),
        ("Moving jaw", [(jaw, "jaw")], 25, -60),
        ("Thumb wheel", [(wheel, "wheel")], 45, -60),
        ("Leg + sled", [(leg, "leg")], 20, -60),
    ]

    fig = plt.figure(figsize=(18, 10))

    for index, (title, items, elevation, azimuth) in enumerate(views):

        ax = fig.add_subplot(2, 4, index + 1, projection="3d")

        all_tris = []
        all_colors = []
        for shape, color_name in items:
            tris, colors = mesh(shape, COLORS[color_name])
            all_tris.append(tris)
            all_colors.append(colors)

        tris = np.concatenate(all_tris)
        colors = np.concatenate(all_colors)

        ax.add_collection3d(
            Poly3DCollection(tris, facecolors=colors, edgecolors="none")
        )

        lo = tris.reshape(-1, 3).min(axis=0)
        hi = tris.reshape(-1, 3).max(axis=0)
        centre = (lo + hi) / 2.0
        half = (hi - lo).max() / 2.0 + 1.0

        ax.set_xlim(centre[0] - half, centre[0] + half)
        ax.set_ylim(centre[1] - half, centre[1] + half)
        ax.set_zlim(centre[2] - half, centre[2] + half)
        ax.set_box_aspect((1, 1, 1))
        ax.set_proj_type("ortho")
        ax.view_init(elev=elevation, azim=azimuth)
        ax.set_axis_off()
        ax.set_title(title, fontsize=10)

    fig.suptitle(
        f"Picatinny monopod - rail top to ground "
        f"{height_min:.0f}-{height_max:.0f} mm, "
        f"{THREAD_PITCH:g} mm per wheel turn",
        fontsize=12
    )

    fig.tight_layout()
    fig.savefig(out_dir / filename, dpi=130)


# Rail top to the bottom of the sled.
height_min = CLAMP_FLOOR + BASE_PLATE + leg_thread_length + SLED_THICKNESS
height_max = height_min + actual_travel

if PREVIEW:
    print("Rendering preview ...")
    try:
        render_preview(PREVIEW_FILE)
        written.append(PREVIEW_FILE)
    except ImportError:
        print("Preview skipped (python -m pip install matplotlib)")
    except Exception as error:
        print(f"WARNING: Preview failed: {error}")


# ============================================================
# FINAL REPORT
# ============================================================

# Bolt runs from the moving jaw face (gap closed) into the nut.
bolt_min = (clamp_width - JAW_GAP) - nut_pocket_depth + NUT_THICKNESS
bolt_max = (clamp_width - JAW_GAP) - 0.5
standard = [12, 16, 20, 25, 30, 35, 40, 45, 50]
fitting = [length for length in standard if bolt_min <= length <= bolt_max]
bolt_text = (
    f"M{BOLT_DIAMETER:g} x {fitting[-1]}"
    if fitting
    else f"M{BOLT_DIAMETER:g}, {bolt_min:.1f}-{bolt_max:.1f} mm long (no standard length fits)"
)

print()
print("=============================================================")
print("SUCCESS")
print("=============================================================")
print()
print("Generated:")
for name in written:
    print(f"  {name}")
print()
print("Geometry:")
print(f"  Clamp:          {BODY_LENGTH:.1f} long x {clamp_width:.1f} wide mm")
print(f"  Housing:        {-housing_bottom:.1f} mm below the base plate top")
print(f"  Leg thread:     {THREAD_MAJOR_DIAMETER:g} mm x {THREAD_PITCH:g} pitch, "
      f"{leg_thread_length:.1f} mm long")
print(f"  Travel:         {actual_travel:.1f} mm "
      f"({actual_travel / THREAD_PITCH:.1f} wheel turns)")
print(f"  Rail to ground: {height_min:.1f} - {height_max:.1f} mm")
print()
print("Hardware:")
print(f"  {BOLT_COUNT} x {bolt_text} socket head bolt")
print(f"  {BOLT_COUNT} x M{BOLT_DIAMETER:g} hex nut")
print("=============================================================")
