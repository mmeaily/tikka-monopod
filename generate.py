"""
Parametric Picatinny monopod generator
======================================

Units: millimetres

A rear monopod that clamps to a Picatinny (MIL-STD-1913) rail.  The
leg is a swinging arm, worked by a lead screw that runs along the
rail inside a low body:

    knob ─ lead screw ─ slider ─ twin links ─ leg arm ─ pivoting sled

Turning the knob moves the slider along the screw; the links push
the leg arm down (or let it fold up).  The sled foot pivots on the
end of the leg so it stays flat on the bag at any height.

Requires:
    CadQuery, matplotlib (preview only)

Run:
    python generate.py                 (reads params.json)
    python generate.py other.json      (reads a different parameter file)

Output (see "output" in the parameter file):
    monopod_body.stl     rail clamp + screw channel (fixed jaw)
    monopod_jaw.stl      moving clamp jaw
    monopod_screw.stl    lead screw with knob
    monopod_slider.stl   lead screw nut / link carrier
    monopod_link.stl     link (print two)
    monopod_bushing.stl  pivot bushing (print three)
    monopod_leg.stl      leg arm
    monopod_foot.stl     sled foot
    monopod_clip.stl     screw retaining clip
    monopod_preview.png  assembled / side / part views

Every STL is already in its print orientation (flat face on the bed,
no supports needed).

Hardware: every bolt is the same (BOLT_LENGTH, M5 x 25 by default)
socket head bolt with a washer under the head and a plain hex nut;
BOLT_COUNT + 4 of each.  The run checks every joint against
BOLT_LENGTH.

    rail clamp (x BOLT_COUNT)  under the rail, nut slid into a trap
    leg pin                    head and nut recessed in the body walls
    slider, link, foot pins    through a printed bushing

The bushing is a printed tube a little longer than the part that
turns on it: the bolt clamps the bushing solid and the joint turns
on the outside of it, so the nut can be done up tight and stays put.

Assembly:
    1. Bolt the two links to the slider (slider pin) and to the leg
       (link pin), and the foot to the end of the leg (foot pin),
       each through a bushing.  Tighten.
    2. Put the slider into the channel from underneath; the slider
       pin's head and nut run in the slots in the walls.
    3. Bolt the top of the leg between the bosses (leg pin).
    4. Run the screw in through the knob end wall and turn it
       through the slider until its tip comes out of the far end
       wall.  Push the clip sideways onto the groove in the tip.
    5. Slide the clamp nuts into the traps in the fixed (-Y) side.
    6. Slide the clamp onto the rail sideways with the recoil lugs
       in rail slots, add the moving jaw and bolt it up.

Turn the knob clockwise (seen from the knob end) to raise the rifle.
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
RAIL_WIDTH = param("RAIL_WIDTH")
RAIL_NECK_WIDTH = param("RAIL_NECK_WIDTH")
RAIL_SLOT_PITCH = param("RAIL_SLOT_PITCH")
RAIL_SLOT_WIDTH = param("RAIL_SLOT_WIDTH")
RAIL_SLOT_DEPTH = param("RAIL_SLOT_DEPTH")

# Clamp
CLAMP_LENGTH = param("CLAMP_LENGTH")
CLAMP_WALL = param("CLAMP_WALL")
CLAMP_FLOOR = param("CLAMP_FLOOR")
JAW_LIP = param("JAW_LIP")
RAIL_CLEARANCE = param("RAIL_CLEARANCE")
FLOOR_GAP = param("FLOOR_GAP")
JAW_SPLIT_Y = param("JAW_SPLIT_Y")
JAW_GAP = param("JAW_GAP")
BOLT_COUNT = param("BOLT_COUNT")
BOLT_SPACING = param("BOLT_SPACING")
LUG_COUNT = param("LUG_COUNT")
LUG_SPACING_SLOTS = param("LUG_SPACING_SLOTS")
LUG_HEIGHT = param("LUG_HEIGHT")
LUG_WIDTH = param("LUG_WIDTH")
BASE_PLATE = param("BASE_PLATE")

# Hardware
BOLT_DIAMETER = param("BOLT_DIAMETER")
BOLT_LENGTH = param("BOLT_LENGTH")
BOLT_HOLE_CLEARANCE = param("BOLT_HOLE_CLEARANCE")
BOLT_HEAD_DIAMETER = param("BOLT_HEAD_DIAMETER")
BOLT_HEAD_HEIGHT = param("BOLT_HEAD_HEIGHT")
WASHER_DIAMETER = param("WASHER_DIAMETER")
WASHER_THICKNESS = param("WASHER_THICKNESS")
NUT_ACROSS_FLATS = param("NUT_ACROSS_FLATS")
NUT_THICKNESS = param("NUT_THICKNESS")
NUT_CLEARANCE = param("NUT_CLEARANCE")
BUSHING_DIAMETER = param("BUSHING_DIAMETER")
BUSHING_CLEARANCE = param("BUSHING_CLEARANCE")

# Body
WALL = param("WALL")
END_WALL = param("END_WALL")
BOTTOM_WALL = param("BOTTOM_WALL")
SIDE_CLEARANCE = param("SIDE_CLEARANCE")
EDGE_RADIUS = param("EDGE_RADIUS")

# Lead screw
SCREW_DIAMETER = param("SCREW_DIAMETER")
SCREW_PITCH = param("SCREW_PITCH")
SCREW_THREAD_DEPTH = param("SCREW_THREAD_DEPTH")
SCREW_THREAD_CLEARANCE = param("SCREW_THREAD_CLEARANCE")
SCREW_HOLE_CLEARANCE = param("SCREW_HOLE_CLEARANCE")
CLIP_DIAMETER = param("CLIP_DIAMETER")
CLIP_THICKNESS = param("CLIP_THICKNESS")
CLIP_SNAP = param("CLIP_SNAP")

# Slider
SLIDER_LENGTH = param("SLIDER_LENGTH")
SLIDER_WALL = param("SLIDER_WALL")

# Linkage
LEG_LENGTH = param("LEG_LENGTH")
LINK_PIVOT = param("LINK_PIVOT")
LINK_LENGTH = param("LINK_LENGTH")
LEG_ANGLE_MIN = param("LEG_ANGLE_MIN")
LEG_ANGLE_MAX = param("LEG_ANGLE_MAX")
LEG_WIDTH = param("LEG_WIDTH")
LEG_DEPTH = param("LEG_DEPTH")
LEG_HUB_RADIUS = param("LEG_HUB_RADIUS")
LINK_THICKNESS = param("LINK_THICKNESS")
LINK_END_RADIUS = param("LINK_END_RADIUS")

# Sled foot
SLED_LENGTH = param("SLED_LENGTH")
SLED_WIDTH = param("SLED_WIDTH")
SLED_THICKNESS = param("SLED_THICKNESS")
SLED_TIP_HEIGHT = param("SLED_TIP_HEIGHT")
SLED_TIP_THICKNESS = param("SLED_TIP_THICKNESS")
SLED_CURVE_RADIUS = param("SLED_CURVE_RADIUS")
SLED_TIP_FILLET = param("SLED_TIP_FILLET")
SLED_CORNER_RADIUS = param("SLED_CORNER_RADIUS")
FOOT_PIVOT_HEIGHT = param("FOOT_PIVOT_HEIGHT")
CHEEK_THICKNESS = param("CHEEK_THICKNESS")

# Knob
KNOB_DIAMETER = param("KNOB_DIAMETER")
KNOB_THICKNESS = param("KNOB_THICKNESS")
KNURL_COUNT = param("KNURL_COUNT")
KNURL_RADIUS = param("KNURL_RADIUS")
KNOB_CHAMFER = param("KNOB_CHAMFER")
KNOB_GAP = param("KNOB_GAP")

# Output
OUTPUT_PREFIX = param("OUTPUT_PREFIX")
PREVIEW = param("PREVIEW")
PREVIEW_FILE = param("PREVIEW_FILE")
PREVIEW_RAIL = param("PREVIEW_RAIL")
CHECK_CLEARANCES = param("CHECK_CLEARANCES")


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
#   X  along the rail; the knob is on the -X end
#   Y  across the rifle (moving jaw on +Y)
#   Z  up; z = 0 is the top of the base plate, the rail top sits
#      at z = CLAMP_FLOOR and the clamp top JAW_LIP above its widest point
#
#   side view:
#                 rail
#         ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼          ── z = CLAMP_FLOOR
#     ┌───┬──────────────────────┬───┐   ── z = 0  base plate / roof
#   ┌─┤   │ ═══════[slider]══════│   │      lead screw (z = screw_z)
#   │K├   │         ╲  ═ ═ ═ ═ ═ │   │      slot for the slider pin S
#   └─┤ P0●          ╲           │   │
#     └───┴─╲─────────╲──────────┴───┘   ── z = body_bottom
#            ╲         ● Q   twin links S-Q
#             ╲  leg
#              ╲
#               ● F   foot pivot
#          ╱▀▀▀▀▀▀▀▀▀▀▀▀╲   sled foot
#
# The leg swings about P0 (fixed in the body).  The links run from
# the slider pin S down to Q on the leg.  Moving the slider towards
# the knob pushes the leg down.  Load on the foot pushes the slider
# away from the knob, so the knob face takes the screw's thrust
# against the end wall.

rail_half = RAIL_WIDTH / 2.0                  # at the widest point
neck_half = RAIL_NECK_WIDTH / 2.0             # top face and neck
flank_height = rail_half - neck_half          # 45 degree flanks

# ---- rail clamp ----

clamp_y_min = -(rail_half + CLAMP_WALL)
clamp_y_max = rail_half + CLAMP_WALL
clamp_width = clamp_y_max - clamp_y_min
clamp_top = CLAMP_FLOOR + flank_height + JAW_LIP
clamp_half = CLAMP_LENGTH / 2.0
cavity_floor = CLAMP_FLOOR - FLOOR_GAP

# ---- hardware ----

bolt_hole_radius = (BOLT_DIAMETER + BOLT_HOLE_CLEARANCE) / 2.0
bolt_head_radius = BOLT_HEAD_DIAMETER / 2.0
washer_radius = WASHER_DIAMETER / 2.0
nut_pocket_af = NUT_ACROSS_FLATS + NUT_CLEARANCE
nut_pocket_ac = nut_pocket_af / math.cos(math.radians(30))   # across corners
bushing_radius = BUSHING_DIAMETER / 2.0
bushing_hole_radius = bushing_radius + BUSHING_CLEARANCE

# ---- rail clamp bolts ----
#
# The bolts run across under the rail, from the moving jaw (head and
# washer on its outer face) to a nut slid into a trap in the fixed
# side.  They only span half the clamp, so a short bolt does.  The
# recoil lugs on the clamp floor sit in the rail's cross slots.

# Low as possible while the hole stays whole in the moving jaw, which
# sits on z = 0: 1.5 mm of jaw under the hole.
bolt_z = bolt_hole_radius + 1.5
bolt_xs = [
    (index - (BOLT_COUNT - 1) / 2.0) * BOLT_SPACING
    for index in range(BOLT_COUNT)
]
lug_xs = [
    (index - (LUG_COUNT - 1) / 2.0) * LUG_SPACING_SLOTS * RAIL_SLOT_PITCH
    for index in range(LUG_COUNT)
]

# Jaw clamped on the rail: it closes 2 x RAIL_CLEARANCE from as built.
jaw_closed_shift = 2.0 * RAIL_CLEARANCE
clamp_head_y = clamp_y_max - jaw_closed_shift + WASHER_THICKNESS
clamp_tip_y = clamp_head_y - BOLT_LENGTH
# Nut placed so the bolt just pokes through it with the jaw closed;
# with the jaw fully open it still has most of the nut.
nut_inner_y = clamp_tip_y + NUT_THICKNESS + 0.5
nut_trap_half_x = nut_pocket_ac / 2.0 + 0.2

# ---- across the body (Y) ----
#
#   wall | link | slider tongue / leg | link | wall
#
# The slider's top block (around the screw) is the full channel
# width so the walls stop it turning with the screw.

channel_half = LEG_WIDTH / 2.0 + LINK_THICKNESS + 2.0 * SIDE_CLEARANCE
body_half = channel_half + WALL
link_y = LEG_WIDTH / 2.0 + SIDE_CLEARANCE + LINK_THICKNESS / 2.0
gap_half = LEG_WIDTH / 2.0 + SIDE_CLEARANCE   # between the leg pin bosses

# ---- heights (Z) ----

screw_radius = SCREW_DIAMETER / 2.0
screw_minor_radius = screw_radius - SCREW_THREAD_DEPTH

slider_top = -BASE_PLATE - 0.5
screw_z = slider_top - SLIDER_WALL - screw_radius
slider_block_bottom = screw_z - screw_radius - SLIDER_WALL
slider_pin_z = slider_block_bottom - LINK_END_RADIUS - 0.5
# The slider pin's head, nut and washers stick out past the links,
# so they run in slots through the walls.  They turn with the links.
slot_half = max(washer_radius, nut_pocket_ac / 2.0) + 0.5
body_bottom = slider_pin_z - slot_half - BOTTOM_WALL
leg_pivot_z = body_bottom + BOTTOM_WALL + bolt_hole_radius

# Leg pin: head (on a washer) and nut recessed into the outside of
# the walls just far enough for BOLT_LENGTH.
leg_pin_nut_y = -body_half + NUT_THICKNESS                   # nut inner face
leg_pin_head_y = min(body_half, -body_half + BOLT_LENGTH - WASHER_THICKNESS - 0.5)
leg_pin_counterbore = body_half - leg_pin_head_y

# Slider, link and foot pins: bushing between the two outer parts.
bushing_length = LEG_WIDTH + 2.0 * SIDE_CLEARANCE
pin_grip = bushing_length + 2.0 * max(LINK_THICKNESS, CHEEK_THICKNESS)

# ---- linkage ----


def linkage(angle_deg, leg_pivot_x=0.0):
    """
    Pose of the linkage with the leg angle_deg below horizontal.
    Returns the link pin Q, slider pin S x position and foot pivot F,
    or None if the link cannot reach.
    """

    a = math.radians(angle_deg)
    qx = leg_pivot_x + LINK_PIVOT * math.cos(a)
    qz = leg_pivot_z - LINK_PIVOT * math.sin(a)
    dz = slider_pin_z - qz
    if abs(dz) >= LINK_LENGTH:
        return None
    return {
        "angle": angle_deg,
        "qx": qx,
        "qz": qz,
        "sx": qx + math.sqrt(LINK_LENGTH ** 2 - dz ** 2),
        "fx": leg_pivot_x + LEG_LENGTH * math.cos(a),
        "fz": leg_pivot_z - LEG_LENGTH * math.sin(a),
    }


angle_mid = (LEG_ANGLE_MIN + LEG_ANGLE_MAX) / 2.0
samples = [
    LEG_ANGLE_MIN + (LEG_ANGLE_MAX - LEG_ANGLE_MIN) * i / 40.0
    for i in range(41)
]
poses = [linkage(angle) for angle in samples]
linkage_ok = all(poses)

if linkage_ok:
    sx_far = poses[0]["sx"]       # retracted: slider furthest from the knob
    sx_near = poses[-1]["sx"]     # extended:  slider closest to the knob
else:
    sx_far = sx_near = 0.0

# ---- along the body (X) ----
#
# Laid out from the knob end, then centred on x = 0.

leg_pivot_from_inner = LEG_HUB_RADIUS + 1.0
inner_length = leg_pivot_from_inner + sx_far + SLIDER_LENGTH / 2.0 + 0.5
body_length = inner_length + 2.0 * END_WALL

body_x0 = -body_length / 2.0
body_x1 = body_length / 2.0
inner_x0 = body_x0 + END_WALL
inner_x1 = body_x1 - END_WALL
leg_pivot_x = inner_x0 + leg_pivot_from_inner

slider_x_near = leg_pivot_x + sx_near
slider_x_far = leg_pivot_x + sx_far
slider_travel = sx_far - sx_near

# The screw is a plain journal from the knob up to here; the slider
# runs off its thread onto the journal and stops at full extension.
thread_start_x = slider_x_near - SLIDER_LENGTH / 2.0
thread_end_x = inner_x1 - 0.5
tip_radius = screw_minor_radius - 0.5

# The tip runs out through the far wall; a clip snapped into a groove
# on it bears on the outside of the wall, so the screw cannot be
# pulled back out towards the knob.
clip_x0 = body_x1 + 0.1
groove_radius = tip_radius - 1.0
groove_x0 = body_x1 - 0.3
groove_x1 = clip_x0 + CLIP_THICKNESS + 0.2
tip_x1 = groove_x1 + 1.5

knob_radius = KNOB_DIAMETER / 2.0
knob_outer_x = body_x0 - KNOB_GAP - KNOB_THICKNESS

foot_pivot_height = SLED_THICKNESS + FOOT_PIVOT_HEIGHT   # F above the ground


def pose(angle_deg):
    return linkage(angle_deg, leg_pivot_x)


def height(angle_deg):
    """Rail top to the ground."""

    return CLAMP_FLOOR - pose(angle_deg)["fz"] + foot_pivot_height


def foot_rate(angle_deg):
    """Foot drop per mm of slider travel (also slider force / foot load)."""

    step = 0.25
    a, b = pose(angle_deg - step), pose(angle_deg + step)
    return abs((b["fz"] - a["fz"]) / (b["sx"] - a["sx"]))


def link_leg_angle(p):
    """Angle between the link and the leg at Q, degrees."""

    a = math.radians(p["angle"])
    lx, lz = p["sx"] - p["qx"], slider_pin_z - p["qz"]
    cos_angle = (lx * -math.cos(a) + lz * math.sin(a)) / LINK_LENGTH
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_angle))))


# ------------------------------------------------------------
# Sanity checks
# ------------------------------------------------------------

problems = []

screw_crest = SCREW_PITCH / 2.0 - SCREW_THREAD_DEPTH
screw_root = screw_crest + 2.0 * SCREW_THREAD_DEPTH

if screw_crest <= 0.2:
    problems.append(
        f"SCREW_THREAD_DEPTH {SCREW_THREAD_DEPTH} is too deep for "
        f"SCREW_PITCH {SCREW_PITCH} (crest would be {screw_crest:.2f} mm)"
    )

if screw_root + SCREW_THREAD_CLEARANCE >= SCREW_PITCH:
    problems.append("SCREW_THREAD_CLEARANCE leaves no ridge in the slider")

nut_skin = min(
    cavity_floor - (bolt_z + nut_pocket_af / 2.0),
    (bolt_z - nut_pocket_af / 2.0) + BASE_PLATE,
)
if nut_skin < 2.0:
    problems.append(
        f"Only {nut_skin:.2f} mm of floor around the clamp nut traps: "
        "raise CLAMP_FLOOR"
    )

if nut_inner_y > JAW_SPLIT_Y - JAW_GAP - 3.0:
    problems.append(
        "BOLT_LENGTH is too long for the clamp: the nut would sit "
        "too close to the moving jaw"
    )

if nut_inner_y - NUT_THICKNESS < clamp_y_min + 1.0:
    problems.append("BOLT_LENGTH is too short to reach across the clamp to the nut")

if flank_height <= 1.0:
    problems.append("RAIL_NECK_WIDTH must be well under RAIL_WIDTH")

if not 0.5 <= JAW_LIP <= flank_height - 0.3:
    problems.append(
        "JAW_LIP must be at least 0.5 mm and stay 0.3 mm short of the rail's "
        "neck ((RAIL_WIDTH - RAIL_NECK_WIDTH) / 2)"
    )

if LUG_HEIGHT > RAIL_SLOT_DEPTH - 0.5:
    problems.append("LUG_HEIGHT must stay 0.5 mm short of RAIL_SLOT_DEPTH")

if LUG_WIDTH > RAIL_SLOT_WIDTH - 0.2:
    problems.append("LUG_WIDTH must be at least 0.2 mm narrower than RAIL_SLOT_WIDTH")

if not (-rail_half < JAW_SPLIT_Y < rail_half):
    problems.append("JAW_SPLIT_Y must be inside the rail width")

if bolt_xs and max(abs(x) for x in bolt_xs) + nut_trap_half_x > clamp_half - 2.0:
    problems.append("Clamp bolts (nut traps) do not fit in CLAMP_LENGTH")

if lug_xs and max(abs(x) for x in lug_xs) + LUG_WIDTH / 2.0 > clamp_half - 1.0:
    problems.append("Recoil lugs do not fit in CLAMP_LENGTH")

if any(
    abs(bx - lx) < nut_trap_half_x + LUG_WIDTH / 2.0 + 1.0
    for bx in bolt_xs for lx in lug_xs
):
    problems.append(
        "A clamp nut trap sits under a recoil lug: change BOLT_SPACING "
        "or LUG_SPACING_SLOTS"
    )

# The wall and boss are solid from the leg hub out to the body side.
if min(leg_pin_head_y, -leg_pin_nut_y) - gap_half < 3.0:
    problems.append(
        "BOLT_LENGTH is too short for the leg pin: the head or nut "
        "recess leaves under 3 mm beside the leg"
    )

if pin_grip + WASHER_THICKNESS + NUT_THICKNESS > BOLT_LENGTH:
    problems.append(
        f"Slider/link/foot pins need {pin_grip + WASHER_THICKNESS + NUT_THICKNESS:.1f} mm "
        f"bolts (BOLT_LENGTH {BOLT_LENGTH}): thin LEG_WIDTH, LINK_THICKNESS "
        "or CHEEK_THICKNESS"
    )

if bushing_radius < bolt_hole_radius + 1.2:
    problems.append("BUSHING_DIAMETER leaves less than 1.2 mm of wall")

if not linkage_ok:
    problems.append(
        "The link cannot reach the leg over the whole angle range: "
        "raise LINK_LENGTH or narrow LEG_ANGLE_MIN..LEG_ANGLE_MAX"
    )
else:
    if any(b["sx"] >= a["sx"] for a, b in zip(poses, poses[1:])):
        problems.append(
            "The slider does not move steadily one way over the leg "
            "angle range (linkage folds over): change LINK_LENGTH / LINK_PIVOT"
        )

    q_clear = body_bottom - (poses[0]["qz"] + slot_half)
    if q_clear < 0.5:
        problems.append(
            f"At LEG_ANGLE_MIN the link pin heads are {0.5 - q_clear:.1f} mm "
            "too close to the body: raise LEG_ANGLE_MIN or LINK_PIVOT"
        )

    angles = [link_leg_angle(p) for p in poses]
    if min(angles) < 30.0 or max(angles) > 150.0:
        problems.append(
            f"Link-to-leg angle runs {min(angles):.0f}-{max(angles):.0f} deg; "
            "keep it within 30-150 deg or the screw has to push too hard"
        )

    # The links must clear the leg pin bosses (same Y band).
    for p in poses:
        dx, dz = p["sx"] - p["qx"], slider_pin_z - p["qz"]
        px, pz = leg_pivot_x - p["qx"], leg_pivot_z - p["qz"]
        t = max(0.0, min(1.0, (px * dx + pz * dz) / LINK_LENGTH ** 2))
        dist = math.hypot(px - t * dx, pz - t * dz)
        if dist < LINK_END_RADIUS + LEG_HUB_RADIUS + 0.5:
            problems.append(
                f"At {p['angle']:.0f} deg the links hit the leg pin bosses: "
                "raise LINK_PIVOT or lower LEG_ANGLE_MAX"
            )
            break

    if slider_x_near - slot_half < leg_pivot_x + max(LEG_HUB_RADIUS, washer_radius) + 1.0:
        problems.append(
            "The slider pin slots run into the leg pin: lower LEG_ANGLE_MAX"
        )

    if thread_start_x < inner_x0 + 2.0:
        problems.append(
            "No room for the screw journal at full extension: lower "
            "LEG_ANGLE_MAX"
        )

if screw_z + knob_radius > CLAMP_FLOOR - 0.5:
    problems.append("KNOB_DIAMETER is too big: the knob would hit the rail")

if screw_z - knob_radius < body_bottom - 3.0:
    problems.append("KNOB_DIAMETER hangs well below the body")

if CLIP_DIAMETER / 2.0 < tip_radius + SCREW_HOLE_CLEARANCE + 1.5:
    problems.append("CLIP_DIAMETER is too small to bear on the far end wall")

if groove_radius < 2.5:
    problems.append("SCREW_DIAMETER is too small for the retaining clip groove")

if FOOT_PIVOT_HEIGHT < LEG_HUB_RADIUS + 0.5:
    problems.append("FOOT_PIVOT_HEIGHT must clear LEG_HUB_RADIUS")

if LEG_DEPTH / 2.0 + 1.0 < bushing_hole_radius + 2.0:
    problems.append("LEG_DEPTH leaves less than 2 mm around the link pin")

if SLED_CURVE_RADIUS * math.sqrt(0.5) >= SLED_TIP_HEIGHT - SLED_TIP_THICKNESS / 2.0:
    problems.append("SLED_CURVE_RADIUS is too big for SLED_TIP_HEIGHT")

if SLED_TIP_HEIGHT <= SLED_THICKNESS + SLED_TIP_FILLET:
    problems.append("SLED_TIP_HEIGHT must clear the deck plus SLED_TIP_FILLET")

if SLED_LENGTH / 2.0 - SLED_TIP_THICKNESS - SLED_TIP_FILLET <= LEG_HUB_RADIUS + 4.0:
    problems.append("SLED_LENGTH is too short for the tips and the foot pivot cheeks")

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


def z_to_x(shape):
    """Turn a shape built along +Z so it runs along +X."""

    return shape.rotate((0, 0, 0), (0, 1, 0), 90)


def teardrop_x(radius, z, x0, x1):
    """
    Hole along X with a 45 degree point towards +Z (up as the body
    prints), so the hole needs no support.
    """

    s = math.sqrt(0.5)
    point = (
        cq.Workplane("XY")
        .polyline([(-radius * s, -radius * s), (radius * s, -radius * s), (0.0, -radius / s)])
        .close()
        .extrude(x1 - x0)
    )
    # Built along Z with the point on -y; turn it so the point is +Z.
    drop = z_to_x(cq.Workplane("XY").circle(radius).extrude(x1 - x0).union(point))
    drop = drop.rotate((0, 0, 0), (1, 0, 0), -90)
    return drop.translate((x0, 0, z))


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


def disc_xz(radius, x, z, thickness):
    """Disc in the XZ plane, centred on y = 0."""

    return (
        cq.Workplane("XZ")
        .center(x, z)
        .circle(radius)
        .extrude(thickness / 2.0, both=True)
    )


def bar_xz(length, depth, thickness):
    """Bar from x = 0 to x = length, depth across Z, centred on y = 0."""

    return box(0.0, length, -thickness / 2.0, thickness / 2.0, -depth / 2.0, depth / 2.0)


def thread_ridge(root_radius, depth, crest, root, pitch, z0, z1):
    """
    Right-hand helical thread ridge from root_radius out to
    root_radius + depth, covering z0..z1 (it overruns both ends by one
    pitch; trim it with an intersect or let a cut overrun).  The ridge
    sinks 0.3 mm into the core so the union is clean.
    """

    sink = 0.3
    inner = root_radius - sink
    outer = root_radius + depth

    height = (z1 - z0) + 2.0 * pitch
    base = z0 - pitch

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
            pitch, height, radius,
            center=cq.Vector(0, 0, base + dz)
        )
        for radius, dz in outline
    ]

    faces = [
        cq.Face.makeRuledSurface(helices[i], helices[(i + 1) % len(helices)])
        for i in range(len(helices))
    ]

    end_angle = 2.0 * math.pi * height / pitch

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


def cone_z(r0, r1, z0, z1):

    return (
        cq.Workplane("XY")
        .workplane(offset=z0)
        .circle(r0)
        .workplane(offset=z1 - z0)
        .circle(r1)
        .loft()
    )


def to_bed(shape):
    """Move a shape so its lowest point is on z = 0."""

    bb = shape.val().BoundingBox()
    return shape.translate((0, 0, -bb.zmin))


# ============================================================
# RAIL CAVITY
# ============================================================

# Rail top faces down into the clamp (the rail is on the rifle above).
# Half-width of the rail, measured from its top surface:
#   0                 neck_half       (top face)
#   flank_height      rail_half       (widest point, 45 degrees out)
#   2 x flank_height  neck_half       (neck, 45 degrees back in)
#
#        rifle
#      ┃       ┃      neck
#     ╱         ╲     lips hook up under here
#     ╲         ╱     widest point
#      ┗━━━━━━━┛      top face, over the clamp floor
#
# The cavity is straight-sided up to the widest point; the jaw lips
# then follow the lower flank in for JAW_LIP, short of the neck.
# Pulling the jaw in wedges the clamp up against that flank.

c = RAIL_CLEARANCE

lip_tip_half = rail_half + c - JAW_LIP

cavity_points = [
    (-(rail_half + c), cavity_floor),
    (rail_half + c, cavity_floor),
    (rail_half + c, CLAMP_FLOOR + flank_height),
    (lip_tip_half, clamp_top),
    (lip_tip_half, clamp_top + 1.0),
    (-lip_tip_half, clamp_top + 1.0),
    (-lip_tip_half, clamp_top),
    (-(rail_half + c), CLAMP_FLOOR + flank_height),
]


# ============================================================
# CLAMP BLOCK -> FIXED HALF + MOVING JAW
# ============================================================

clamp_block = box(
    -clamp_half, clamp_half,
    clamp_y_min, clamp_y_max,
    0.0, clamp_top
)

clamp_block = clamp_block.cut(
    profile_yz(cavity_points, -clamp_half - 1.0, clamp_half + 1.0)
)

for x in bolt_xs:
    clamp_block = clamp_block.cut(
        cylinder_y(
            bolt_hole_radius, x, bolt_z,
            -clamp_width, clamp_width
        )
    )

big = 4.0 * clamp_width

clamp_fixed = clamp_block.intersect(
    box(-big, big, -big, JAW_SPLIT_Y - JAW_GAP, -1.0, clamp_top + 1.0)
)

jaw = clamp_block.intersect(
    box(-big, big, JAW_SPLIT_Y, big, -1.0, clamp_top + 1.0)
)

# Recoil lugs: ribs right across the clamp floor that sit in the
# rail's cross slots, on both the fixed half and the moving jaw.  The
# rail slides on sideways along them, and the jaw slides in along them.
# They run out to the walls (the slots are deeper than the lugs right
# across the rail), so the jaw's lugs print standing on its wall.
for x in lug_xs:
    clamp_fixed = clamp_fixed.union(
        box(
            x - LUG_WIDTH / 2.0, x + LUG_WIDTH / 2.0,
            -(rail_half + c + 0.01), JAW_SPLIT_Y - JAW_GAP,
            cavity_floor - 0.01, CLAMP_FLOOR + LUG_HEIGHT
        )
    )
    jaw = jaw.union(
        box(
            x - LUG_WIDTH / 2.0, x + LUG_WIDTH / 2.0,
            JAW_SPLIT_Y, rail_half + c + 0.01,
            cavity_floor - 0.01, CLAMP_FLOOR + LUG_HEIGHT
        )
    )


# ============================================================
# BODY: FIXED CLAMP + ROOF + SCREW CHANNEL
# ============================================================

print("Building body ...")

# Roof of the channel; under the clamp it is the full clamp width so
# the moving jaw rests on it.
roof = box(
    body_x0, body_x1,
    -body_half, body_half,
    -BASE_PLATE, 0.0
).union(
    box(
        -clamp_half, clamp_half,
        clamp_y_min, clamp_y_max,
        -BASE_PLATE, 0.0
    )
)

channel_body = box(
    body_x0, body_x1,
    -body_half, body_half,
    body_bottom, -BASE_PLATE + 0.01
)

if EDGE_RADIUS > 0:
    try:
        channel_body = channel_body.edges("|Z").fillet(EDGE_RADIUS)
        roof = roof.edges("|Z").fillet(EDGE_RADIUS)
    except Exception as error:
        print(f"WARNING: edge fillet skipped: {error}")

channel_body = channel_body.cut(
    box(
        inner_x0, inner_x1,
        -channel_half, channel_half,
        body_bottom - 1.0, -BASE_PLATE
    )
)

# Bosses that close the channel down to the leg width around the
# leg pin, so the top of the leg is held on both sides.
for sign in (-1.0, 1.0):
    y0, y1 = sorted((sign * gap_half, sign * (channel_half + 0.01)))
    boss = cylinder_y(LEG_HUB_RADIUS, leg_pivot_x, leg_pivot_z, y0, y1).union(
        box(
            inner_x0 - 0.01, leg_pivot_x,
            y0, y1,
            leg_pivot_z - LEG_HUB_RADIUS, leg_pivot_z + LEG_HUB_RADIUS
        )
    ).intersect(
        box(-big, big, -big, big, body_bottom, 0.0)
    )
    channel_body = channel_body.union(boss)

body = clamp_fixed.union(roof).union(channel_body)

# Clamp nut traps: a slot in from the fixed (-Y) side the nut slides
# along, flats top and bottom so it cannot turn.  Tightening pulls
# the nut against the end of the slot.
for x in bolt_xs:
    body = body.cut(
        box(
            x - nut_trap_half_x, x + nut_trap_half_x,
            clamp_y_min - 1.0, nut_inner_y,
            bolt_z - nut_pocket_af / 2.0, bolt_z + nut_pocket_af / 2.0
        )
    )
    # Cut again now the roof is on, in case the hole dips into it.
    body = body.cut(cylinder_y(bolt_hole_radius, x, bolt_z, -big, big))

# Relief under the clamp bolt washers, which hang below z = 0, so
# they pull on the moving jaw and not on the roof.
head_relief_y = clamp_y_max - JAW_GAP - 0.5
for x in bolt_xs:
    body = body.cut(
        box(
            x - washer_radius - 0.5, x + washer_radius + 0.5,
            head_relief_y, big,
            bolt_z - washer_radius - 0.5, 0.01
        )
    )

# Leg pin: hole, counterbore for the head and washer on +Y, hex
# pocket for the nut on -Y.
body = body.cut(
    cylinder_y(bolt_hole_radius, leg_pivot_x, leg_pivot_z, -big, big)
)
if leg_pin_counterbore > 0.0:
    body = body.cut(
        cylinder_y(washer_radius + 0.5, leg_pivot_x, leg_pivot_z, leg_pin_head_y, big)
    )
body = body.cut(
    hex_y(nut_pocket_af, leg_pivot_x, leg_pivot_z, -big, leg_pin_nut_y)
)

# Slots for the slider pin, through both walls.
slot_x0 = slider_x_near
slot_x1 = slider_x_far
body = body.cut(
    box(slot_x0, slot_x1, -big, big, slider_pin_z - slot_half, slider_pin_z + slot_half)
    .union(cylinder_y(slot_half, slot_x0, slider_pin_z, -big, big))
    .union(cylinder_y(slot_half, slot_x1, slider_pin_z, -big, big))
)

# Screw journal through the knob end wall, and the tip through the
# far wall.
body = body.cut(
    teardrop_x(
        screw_radius + SCREW_HOLE_CLEARANCE, screw_z,
        body_x0 - 1.0, inner_x0 + 1.0
    )
)
body = body.cut(
    teardrop_x(
        tip_radius + SCREW_HOLE_CLEARANCE, screw_z,
        inner_x1 - 1.0, body_x1 + 1.0
    )
)


# ============================================================
# LEAD SCREW + KNOB
# ============================================================

# Built in print orientation: knob on the bed, screw pointing up.
# Local z = 0 is the knob's outer face; assembled, local z runs
# along +X from knob_outer_x.

print("Building lead screw ...")


def screw_local(x):
    return x - knob_outer_x


journal_end = screw_local(thread_start_x)
thread_end = screw_local(thread_end_x)
tip_end = screw_local(tip_x1)

knob = (
    cq.Workplane("XY")
    .circle(knob_radius)
    .extrude(KNOB_THICKNESS)
    .edges()
    .chamfer(KNOB_CHAMFER)
)

for index in range(KNURL_COUNT):
    angle = 2.0 * math.pi * index / KNURL_COUNT
    knob = knob.cut(
        cylinder_z(
            KNURL_RADIUS,
            -1.0, KNOB_THICKNESS + 1.0,
            knob_radius * math.cos(angle),
            knob_radius * math.sin(angle)
        )
    )

# "UP" and a clockwise arrow engraved in the outer face (the face on
# the bed).  Drawn in XY as seen from inside (+Z).
try:
    engrave_depth = 0.6
    arrow_radius = knob_radius * 0.62
    arrow_width = 1.4
    sweep = 250.0
    start = 90.0 + sweep / 2.0
    ring = (
        cq.Workplane("XY")
        .circle(arrow_radius + arrow_width / 2.0)
        .circle(arrow_radius - arrow_width / 2.0)
        .extrude(engrave_depth)
    )
    gap = (
        cq.Workplane("XY")
        .polyline([
            (0.0, 0.0),
            (2.0 * knob_radius * math.cos(math.radians(start)),
             2.0 * knob_radius * math.sin(math.radians(start))),
            (0.0, -2.0 * knob_radius),
            (2.0 * knob_radius * math.cos(math.radians(start - sweep)),
             2.0 * knob_radius * math.sin(math.radians(start - sweep))),
        ])
        .close()
        .extrude(engrave_depth)
    )
    arc = ring.cut(gap)
    # Arrow head at the end of the sweep (anticlockwise from inside).
    end = math.radians(start)
    ex, ey = arrow_radius * math.cos(end), arrow_radius * math.sin(end)
    tx, ty = -math.sin(end), math.cos(end)       # anticlockwise tangent
    nx, ny = math.cos(end), math.sin(end)
    head = (
        cq.Workplane("XY")
        .polyline([
            (ex + nx * 2.2, ey + ny * 2.2),
            (ex - nx * 2.2, ey - ny * 2.2),
            (ex + tx * 3.0, ey + ty * 3.0),
        ])
        .close()
        .extrude(engrave_depth)
    )
    text = (
        cq.Workplane("XY")
        .text("UP", knob_radius * 0.45, engrave_depth, combine=False, halign="center", valign="center")
    )
    # Anticlockwise seen from inside is clockwise seen from outside,
    # so only the text needs mirroring.
    marking = arc.union(head).union(text.mirror("YZ")).translate((0, 0, -0.01))
    knob = knob.cut(marking)
except Exception as error:
    print(f"WARNING: knob marking skipped: {error}")

screw = knob.union(
    cylinder_z(screw_radius, KNOB_THICKNESS - 0.5, journal_end)
)

screw = screw.union(
    cylinder_z(screw_minor_radius, journal_end - 0.5, thread_end)
).union(
    thread_ridge(
        screw_minor_radius, SCREW_THREAD_DEPTH,
        screw_crest, screw_root, SCREW_PITCH,
        journal_end, thread_end
    ).intersect(box(-50, 50, -50, 50, journal_end - 0.5, thread_end))
)

# 45 degree lead-in at the end of the thread, then the tip.
screw = screw.cut(
    cylinder_z(screw_radius + 2.0, thread_end - SCREW_THREAD_DEPTH - 0.5, thread_end + 0.01).cut(
        cone_z(
            screw_radius + 0.5, screw_minor_radius - 0.4,
            thread_end - SCREW_THREAD_DEPTH - 0.5, thread_end + 0.01
        )
    )
)

screw = screw.union(
    cylinder_z(tip_radius, thread_end - 0.5, tip_end - 0.5)
).union(
    cone_z(tip_radius, tip_radius - 0.5, tip_end - 0.5, tip_end)
)

# Groove for the retaining clip.
screw = screw.cut(
    cylinder_z(tip_radius + 1.0, screw_local(groove_x0), screw_local(groove_x1)).cut(
        cylinder_z(groove_radius, screw_local(groove_x0) - 1.0, screw_local(groove_x1) + 1.0)
    )
)


def screw_assembled():
    return z_to_x(screw).translate((knob_outer_x, 0, screw_z))


# ============================================================
# RETAINING CLIP
# ============================================================

# Snaps sideways into the groove on the screw tip, outside the far end
# wall.  Built flat (print orientation) with the slot towards +X,
# which points down once assembled.

clip_radius = CLIP_DIAMETER / 2.0
clip_slot_half = groove_radius - CLIP_SNAP / 2.0

clip = (
    cq.Workplane("XY").circle(clip_radius).extrude(CLIP_THICKNESS)
    .cut(cylinder_z(groove_radius + 0.15, -1.0, CLIP_THICKNESS + 1.0))
    .cut(box(0.0, clip_radius + 1.0, -clip_slot_half, clip_slot_half, -1.0, CLIP_THICKNESS + 1.0))
)
# Lead-in at the mouth of the slot so it spreads over the groove.
mouth_x = clip_radius - 1.5
clip = clip.cut(
    cq.Workplane("XY")
    .polyline([
        (mouth_x, -clip_slot_half),
        (clip_radius + 1.0, -clip_slot_half - 1.5 - 1.0),
        (clip_radius + 1.0, clip_slot_half + 1.5 + 1.0),
        (mouth_x, clip_slot_half),
    ])
    .close()
    .extrude(CLIP_THICKNESS + 2.0)
    .translate((0, 0, -1.0))
)


def clip_assembled():
    return z_to_x(clip).translate((clip_x0, 0, screw_z))


# ============================================================
# SLIDER (lead screw nut + link carrier)
# ============================================================

# Built assembled, centred on x = 0; moved to the slider position.
# Printed standing on end so the internal thread prints without
# support.

print("Building slider ...")

slider_half = SLIDER_LENGTH / 2.0

slider = box(
    -slider_half, slider_half,
    -(channel_half - SIDE_CLEARANCE), channel_half - SIDE_CLEARANCE,
    slider_block_bottom, slider_top
).union(
    box(
        -slider_half, slider_half,
        -LEG_WIDTH / 2.0, LEG_WIDTH / 2.0,
        slider_pin_z - bushing_hole_radius - 2.5, slider_block_bottom + 0.01
    )
)

# Internal thread: cut a male thread grown by SCREW_THREAD_CLEARANCE.
female_root = screw_minor_radius + SCREW_THREAD_CLEARANCE
nut_cut = cylinder_z(female_root, -slider_half - 1.0, slider_half + 1.0).union(
    thread_ridge(
        female_root, SCREW_THREAD_DEPTH,
        screw_crest + SCREW_THREAD_CLEARANCE,
        screw_root + SCREW_THREAD_CLEARANCE,
        SCREW_PITCH,
        -slider_half - 1.0, slider_half + 1.0
    )
)

# Countersink both ends so the thread starts cleanly.
sink_radius = screw_radius + SCREW_THREAD_CLEARANCE + 0.6
sink_depth = sink_radius - female_root
nut_cut = nut_cut.union(
    cone_z(sink_radius, female_root, -slider_half - 0.01, -slider_half + sink_depth)
).union(
    cone_z(female_root, sink_radius, slider_half - sink_depth, slider_half + 0.01)
)

# Built along Z centred on z = 0: turn it along X onto the screw axis.
slider = slider.cut(z_to_x(nut_cut).translate((0, 0, screw_z)))

slider = slider.cut(
    cylinder_y(bushing_hole_radius, 0.0, slider_pin_z, -big, big)
)


# ============================================================
# LINK (print two)
# ============================================================

# Local frame: link pin Q at the origin, slider pin S at
# (LINK_LENGTH, 0, 0), thickness across Y.

link = (
    bar_xz(LINK_LENGTH, 2.0 * LINK_END_RADIUS, LINK_THICKNESS)
    .union(disc_xz(LINK_END_RADIUS, 0.0, 0.0, LINK_THICKNESS))
    .union(disc_xz(LINK_END_RADIUS, LINK_LENGTH, 0.0, LINK_THICKNESS))
)
for x in (0.0, LINK_LENGTH):
    link = link.cut(cylinder_y(bolt_hole_radius, x, 0.0, -big, big))


# ============================================================
# LEG
# ============================================================

# Local frame: leg pin P0 at the origin, foot pin F at
# (LEG_LENGTH, 0, 0), link pin Q at (LINK_PIVOT, 0, 0); thickness
# LEG_WIDTH across Y.  Printed lying flat, so the pin holes are
# vertical.

print("Building leg ...")

leg = (
    bar_xz(LEG_LENGTH, LEG_DEPTH, LEG_WIDTH)
    .union(disc_xz(LEG_HUB_RADIUS, 0.0, 0.0, LEG_WIDTH))
    .union(disc_xz(LEG_HUB_RADIUS, LEG_LENGTH, 0.0, LEG_WIDTH))
    .union(disc_xz(LEG_DEPTH / 2.0 + 1.0, LINK_PIVOT, 0.0, LEG_WIDTH))
)
# Leg pin: plain bolt hole.  Link and foot pins: bushing holes.
leg = leg.cut(cylinder_y(bolt_hole_radius, 0.0, 0.0, -big, big))
for x in (LINK_PIVOT, LEG_LENGTH):
    leg = leg.cut(cylinder_y(bushing_hole_radius, x, 0.0, -big, big))

# Lightening slot between the link pin and the foot.
slot_start = LINK_PIVOT + LEG_DEPTH / 2.0 + 4.0
slot_end = LEG_LENGTH - LEG_HUB_RADIUS - 4.0
slot_width = LEG_DEPTH - 6.0
if slot_end - slot_start > 2.0 * slot_width and slot_width >= 3.0:
    leg = leg.cut(
        box(slot_start, slot_end, -big, big, -slot_width / 2.0, slot_width / 2.0)
        .union(cylinder_y(slot_width / 2.0, slot_start, 0.0, -big, big))
        .union(cylinder_y(slot_width / 2.0, slot_end, 0.0, -big, big))
    )


# ============================================================
# SLED FOOT
# ============================================================

print("Building foot ...")

# Built in print orientation: sled on the bed at z = 0.
#
# The sled runs along the rail (X) so the rifle can slide straight
# back under recoil instead of the foot digging in.  Both ends curl
# up like sledge runners so it rides over the bag or bench edge.
# It pivots on the end of the leg, between two cheeks, so it sits
# flat at any leg angle.
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

# Cheeks either side of the leg end, flared at the base.
pivot_z = foot_pivot_height
cheek_r = LEG_HUB_RADIUS
cheek = (
    cq.Workplane("XZ")
    .moveTo(-(cheek_r + 4.0), SLED_THICKNESS - 0.5)
    .lineTo(cheek_r + 4.0, SLED_THICKNESS - 0.5)
    .lineTo(cheek_r, pivot_z)
    .threePointArc((0.0, pivot_z + cheek_r), (-cheek_r, pivot_z))
    .close()
    .extrude(CHEEK_THICKNESS / 2.0, both=True)
)
for sign in (-1.0, 1.0):
    centre_y = sign * (gap_half + CHEEK_THICKNESS / 2.0)
    sled = sled.union(cheek.translate((0, centre_y, 0)))

foot = sled.cut(cylinder_y(bolt_hole_radius, 0.0, pivot_z, -big, big))


# ============================================================
# BUSHING (print three)
# ============================================================

# Clamped solid between the two outer parts of the slider, link and
# foot pins; the middle part turns on it.

bushing = cylinder_z(bushing_radius, 0.0, bushing_length).cut(
    cylinder_z(bolt_hole_radius, -1.0, bushing_length + 1.0)
)


# ============================================================
# ASSEMBLY POSES
# ============================================================

def leg_assembled(angle_deg):

    return leg.rotate((0, 0, 0), (0, 1, 0), angle_deg).translate(
        (leg_pivot_x, 0, leg_pivot_z)
    )


def links_assembled(angle_deg):

    p = pose(angle_deg)
    tilt = math.degrees(math.atan2(slider_pin_z - p["qz"], p["sx"] - p["qx"]))
    one = link.rotate((0, 0, 0), (0, 1, 0), -tilt).translate((p["qx"], 0, p["qz"]))
    return [one.translate((0, -link_y, 0)), one.translate((0, link_y, 0))]


def slider_assembled(angle_deg):

    return slider.translate((pose(angle_deg)["sx"], 0, 0))


def foot_assembled(angle_deg):

    p = pose(angle_deg)
    return foot.translate((p["fx"], 0, p["fz"] - foot_pivot_height))


# ============================================================
# CLEARANCE CHECK
# ============================================================

# Booleans the moving parts against each other at both ends and the
# middle of the travel.  Any overlap is reported, not fatal.

if CHECK_CLEARANCES:
    print("Checking clearances ...")

    jaw_closed = jaw.translate((0, -jaw_closed_shift, 0))
    clashes = []

    for angle in (LEG_ANGLE_MIN, angle_mid, LEG_ANGLE_MAX):
        link_a, link_b = links_assembled(angle)
        parts_at = {
            "body": body,
            "jaw": jaw_closed,
            "screw": screw_assembled(),
            "clip": clip_assembled(),
            "slider": slider_assembled(angle),
            "link": link_a,
            "link ": link_b,
            "leg": leg_assembled(angle),
            "foot": foot_assembled(angle),
        }
        # The screw and slider mesh on purpose.
        skip = {("screw", "slider"), ("screw", "clip")}
        names = list(parts_at)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if (a, b) in skip:
                    continue
                common = parts_at[a].intersect(parts_at[b])
                volume = sum(solid.Volume() for solid in common.solids().vals())
                if volume > 0.05:
                    clashes.append(f"{a.strip()} / {b.strip()} at {angle:.0f} deg: {volume:.1f} mm^3")

    for clash in clashes:
        print(f"WARNING: overlap {clash}")
    if not clashes:
        print("  no overlaps")


# ============================================================
# EXPORT (print orientation)
# ============================================================

# Body printed as assembled, open channel on the bed: the recoil
# lugs then stand up off the clamp floor and the rail lips overhang
# at 45 degrees.  The channel roof and the slider pin slots bridge.
body_print = body

# Moving jaw printed on its outer face (+Y down): the 45 degree lip
# then needs no support.
jaw_print = jaw.rotate((0, 0, 0), (1, 0, 0), -90)

# Slider standing on end, thread axis vertical.
slider_print = slider.rotate((0, 0, 0), (0, 1, 0), -90)

# Leg and link lying flat, pin holes vertical.
leg_print = leg.rotate((0, 0, 0), (1, 0, 0), 90)
link_print = link.rotate((0, 0, 0), (1, 0, 0), 90)

parts = {
    "body": to_bed(body_print),
    "jaw": to_bed(jaw_print),
    "screw": screw,
    "slider": to_bed(slider_print),
    "link": to_bed(link_print),
    "leg": to_bed(leg_print),
    "foot": foot,
    "bushing": bushing,
    "clip": clip,
}

out_dir = PARAMS_FILE.resolve().parent
written = []

for name, shape in parts.items():
    filename = out_dir / f"{OUTPUT_PREFIX}_{name}.stl"
    cq.exporters.export(
        shape, str(filename),
        tolerance=0.02, angularTolerance=0.1
    )
    written.append(filename.name + {"link": "  (print 2)", "bushing": "  (print 3)"}.get(name, ""))


# ============================================================
# PREVIEW IMAGE
# ============================================================

# Renders the assembly (retracted, extended, side views) and the
# parts to a PNG so the design can be checked without a slicer.
# Needs matplotlib; skipped if it is missing.


def rail_ghost():

    rail_length = max(CLAMP_LENGTH, body_length) + 3.0 * RAIL_SLOT_PITCH
    # Up to the rifle; the full rail is about 9.4 mm tall.
    rail_ghost_top = CLAMP_FLOOR + max(9.4, 2.0 * flank_height + 1.0)
    rail_points = [
        (-neck_half, CLAMP_FLOOR),
        (neck_half, CLAMP_FLOOR),
        (rail_half, CLAMP_FLOOR + flank_height),
        (neck_half, CLAMP_FLOOR + 2.0 * flank_height),
        (neck_half, rail_ghost_top),
        (-neck_half, rail_ghost_top),
        (-neck_half, CLAMP_FLOOR + 2.0 * flank_height),
        (-rail_half, CLAMP_FLOOR + flank_height),
    ]
    rail = profile_yz(rail_points, -rail_length / 2.0, rail_length / 2.0)

    # Slots lined up with the recoil lugs.
    offset = (lug_xs[0] if lug_xs else 0.0) % RAIL_SLOT_PITCH
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


def bolts_ghost(angle_deg):
    """Clamp bolts and nuts, and the four pivot bolts."""

    shapes = None

    def add(shape):
        nonlocal shapes
        shapes = shape if shapes is None else shapes.union(shape)

    def bolt(x, z, head_y, nut_y):
        """Bolt along -Y: washer below head_y, head above it, nut below nut_y."""
        add(
            cylinder_y(BOLT_DIAMETER / 2.0, x, z, head_y - BOLT_LENGTH, head_y)
            .union(cylinder_y(washer_radius, x, z, head_y - WASHER_THICKNESS, head_y))
            .union(cylinder_y(bolt_head_radius, x, z, head_y, head_y + BOLT_HEAD_HEIGHT))
            .union(hex_y(NUT_ACROSS_FLATS, x, z, nut_y - NUT_THICKNESS, nut_y))
        )

    for x in bolt_xs:
        bolt(x, bolt_z, clamp_head_y, nut_inner_y)

    p = pose(angle_deg)
    pin_half = bushing_length / 2.0 + LINK_THICKNESS
    foot_half = bushing_length / 2.0 + CHEEK_THICKNESS
    bolt(leg_pivot_x, leg_pivot_z, leg_pin_head_y + WASHER_THICKNESS, leg_pin_nut_y)
    bolt(p["sx"], slider_pin_z, pin_half + WASHER_THICKNESS, -pin_half)
    bolt(p["qx"], p["qz"], pin_half + WASHER_THICKNESS, -pin_half)
    bolt(p["fx"], p["fz"], foot_half + WASHER_THICKNESS, -foot_half)

    return shapes


COLORS = {
    "body": (0.30, 0.36, 0.42),
    "jaw": (0.85, 0.45, 0.20),
    "screw": (0.85, 0.45, 0.20),
    "slider": (0.85, 0.45, 0.20),
    "link": (0.85, 0.45, 0.20),
    "leg": (0.62, 0.72, 0.80),
    "foot": (0.25, 0.60, 0.45),
    "rail": (0.80, 0.80, 0.80),
    "bolt": (0.55, 0.55, 0.58),
}


def mesh(shape, color):

    import numpy as np

    vertices, triangles = cq.Compound.makeCompound(shape.vals()).tessellate(0.05, 0.2)
    if not triangles:
        return np.zeros((0, 3, 3)), np.zeros((0, 3))
    xyz = np.array([(v.x, v.y, v.z) for v in vertices])
    tris = xyz[np.array(triangles, dtype=int)]

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

    jaw_closed = jaw.translate((0, -jaw_closed_shift, 0))

    def assembly(angle_deg, with_rail=True):
        link_a, link_b = links_assembled(angle_deg)
        items = [
            (body, "body"),
            (jaw_closed, "jaw"),
            (screw_assembled(), "screw"),
            (clip_assembled(), "screw"),
            (slider_assembled(angle_deg), "slider"),
            (link_a, "link"),
            (link_b, "link"),
            (leg_assembled(angle_deg), "leg"),
            (foot_assembled(angle_deg), "foot"),
            (bolts_ghost(angle_deg), "bolt"),
        ]
        if with_rail and PREVIEW_RAIL:
            items.append((rail_ghost(), "rail"))
        return items

    # Side view with the near (+Y) wall cut away to show the linkage.
    keep = box(-400, 400, -400, 0.0, -400, 400)

    def cutaway(angle_deg):
        return [
            (shape.intersect(keep) if name in ("body", "jaw", "bolt") else shape, name)
            for shape, name in assembly(angle_deg, with_rail=False)
        ]

    low, high = height(LEG_ANGLE_MIN), height(LEG_ANGLE_MAX)
    slider_parts = [(slider, "slider")] + [
        (link.translate((0, offset, slider_pin_z - 12.0)), "link")
        for offset in (-link_y - 6.0, link_y + 6.0)
    ]

    views = [
        (f"Retracted - {low:.0f} mm", assembly(LEG_ANGLE_MIN), 20, -55),
        (f"Extended - {high:.0f} mm", assembly(LEG_ANGLE_MAX), 20, -55),
        ("Side cutaway - retracted", cutaway(LEG_ANGLE_MIN), 0, 90),
        ("Side cutaway - extended", cutaway(LEG_ANGLE_MAX), 0, 90),
        ("Body", [(body, "body")], 25, -60),
        ("Lead screw + slider + links", [(screw_assembled(), "screw"), (clip_assembled(), "screw")] + [
            (shape.translate((0, 0, -22.0)), name) for shape, name in slider_parts
        ], 25, -60),
        ("Leg + foot", [(leg_assembled(angle_mid), "leg"), (foot_assembled(angle_mid), "foot")], 20, -60),
        ("End view (along rail)", assembly(LEG_ANGLE_MAX), 0, 0),
    ]

    fig = plt.figure(figsize=(18, 10))

    for index, (title, items, elevation, azimuth) in enumerate(views):

        ax = fig.add_subplot(2, 4, index + 1, projection="3d")

        all_tris = []
        all_colors = []
        for shape, color_name in items:
            if not shape.vals():
                continue
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
        f"Picatinny monopod - rail top to ground {low:.0f}-{high:.0f} mm, "
        f"{turns:.1f} knob turns end to end",
        fontsize=12
    )

    fig.tight_layout()
    fig.savefig(out_dir / filename, dpi=130)


height_min = height(LEG_ANGLE_MIN)
height_max = height(LEG_ANGLE_MAX)
turns = slider_travel / SCREW_PITCH

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

def protrusion(head_y, nut_y):
    """
    How far the bolt end passes the nut's outer face (negative: it
    stops short, inside the nut).  Bolts point along -Y.
    """

    return (nut_y - NUT_THICKNESS) - (head_y - BOLT_LENGTH)


pin_half = bushing_length / 2.0 + LINK_THICKNESS
foot_half = bushing_length / 2.0 + CHEEK_THICKNESS
bolt_rows = [
    (f"{BOLT_COUNT} x", "rail clamp", protrusion(clamp_head_y, nut_inner_y)),
    ("1 x", "leg pin", protrusion(leg_pin_head_y + WASHER_THICKNESS, leg_pin_nut_y)),
    ("1 x", "slider pin", protrusion(pin_half + WASHER_THICKNESS, -pin_half)),
    ("1 x", "link pin", protrusion(pin_half + WASHER_THICKNESS, -pin_half)),
    ("1 x", "foot pin", protrusion(foot_half + WASHER_THICKNESS, -foot_half)),
]

rate_low = foot_rate(LEG_ANGLE_MIN + 0.5)
rate_high = foot_rate(LEG_ANGLE_MAX - 0.5)

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
print(f"  Body:           {body_length:.1f} long x {2.0 * body_half:.1f} wide, "
      f"{CLAMP_FLOOR - body_bottom:.1f} mm below the rail top")
print(f"  Clamp:          {CLAMP_LENGTH:.1f} long x {clamp_width:.1f} wide mm")
print(f"  Leg angle:      {LEG_ANGLE_MIN:g} - {LEG_ANGLE_MAX:g} deg below horizontal")
print(f"  Slider travel:  {slider_travel:.1f} mm ({turns:.1f} knob turns)")
print(f"  Per knob turn:  {rate_low * SCREW_PITCH:.1f} mm (retracted) - "
      f"{rate_high * SCREW_PITCH:.1f} mm (extended)")
print(f"  Rail to ground: {height_min:.1f} - {height_max:.1f} mm")
print()
print(f"Hardware: M{BOLT_DIAMETER:g} x {BOLT_LENGTH:g} socket head bolt, washer under the "
      "head, plain hex nut")
for count, name, poke in bolt_rows:
    if poke < -NUT_THICKNESS / 2.0:
        state = f"WARNING: only {NUT_THICKNESS + poke:.1f} mm into the nut"
    elif poke < 0.0:
        state = f"{NUT_THICKNESS + poke:.1f} mm into the nut"
    else:
        state = f"through the nut, {poke:.1f} mm spare"
    print(f"  {count} {name:11s} {state}")
print()
print("Turn the knob clockwise (seen from the knob end) to raise the rifle.")
print("=============================================================")
