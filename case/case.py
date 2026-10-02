"""
Keychain case: 1.28" round GC9A01 screen + Raspberry Pi Pico 2 (with headers)
+ KM803040 1000mAh LiPo (8x30x40) + TP4056 Type-C charger (26x17x4) + mini slide switch.
Two parts: front shell (print screen-side down) and snap-in back lid.
All units mm.  Coordinates: x = width, y = length (+y = keyring end), z = depth (+z = screen side).
"""
import numpy as np, trimesh
from manifold3d import Manifold, CrossSection, JoinType

# ---------- tweakable dimensions ----------
WALL   = 2.0      # side wall
FRONT  = 1.6      # front wall (screen side)
LID_T  = 1.6      # back lid plate
IN_W, IN_L = 42.0, 61.0          # interior footprint
R_IN   = 3.0                     # interior corner radius
BATT_Z, PICO_Z, SCREEN_Z = 8.3, 9.5, 4.6   # stack heights (battery, Pico+headers, screen module)
IN_H   = BATT_Z + PICO_Z + SCREEN_Z         # 22.4 interior depth
WIN_D  = 33.5     # screen window (glass ~35.6 rests behind the lip; active area 32.4)
SCR_Y  = IN_L/2 - 37.5/2 - 0.5             # screen centre (top of interior)
CLR    = 0.25     # lid lip clearance per side
LIP_H, LIP_T = 2.0, 1.2
SEG = 96
CHG_Y = -IN_L/2 + 10.2   # charger centre (bottom-right corner, port faces +x)

def rrect(w, l, r):
    return CrossSection.square([w - 2*r, l - 2*r], center=True).offset(r, JoinType.Round, circular_segments=SEG)

def box(sx, sy, sz, cx, cy, z0):
    return Manifold.cube([sx, sy, sz]).translate([cx - sx/2, cy - sy/2, z0])

def cyl(r, h, cx, cy, z0):
    return Manifold.cylinder(h, r, circular_segments=SEG).translate([cx, cy, z0])

OUT_W, OUT_L, R_OUT = IN_W + 2*WALL, IN_L + 2*WALL, R_IN + WALL
SHELL_H = IN_H + FRONT

# ---------- port / switch cut-outs (shell coords, z=0 at open back rim) ----------
cuts = [
    # Pico micro-USB, bottom edge (Pico USB end faces -y). Big enough for the plug's moulding.
    box(12.0, 6*WALL, 7.2, 0, -IN_L/2, 12.6),
    # TP4056 USB-C, right wall, charger lies on the lid in the bottom-right corner
    box(6*WALL, 10.5, 5.0, IN_W/2, CHG_Y, 0.0),
    # slide-switch knob slot, left wall
    box(6*WALL, 7.0, 3.6, -IN_W/2, 0.0, 2.5),
]

# ---------- front shell ----------
outer = Manifold.extrude(rrect(OUT_W, OUT_L, R_OUT), SHELL_H)
inner = Manifold.extrude(rrect(IN_W, IN_L, R_IN), IN_H).translate([0, 0, -0.01])
shell = outer - inner
shell = shell - cyl(WIN_D/2, FRONT + 1, 0, SCR_Y, IN_H - 0.5)
# small chamfer-ish recess around the window so it looks like a bezel
shell = shell - cyl(WIN_D/2 + 1.2, 0.6, 0, SCR_Y, SHELL_H - 0.6)
for c in cuts:
    shell = shell - c
# keyring loop on the top edge, flush with the screen face
ring_y = OUT_L/2 + 5.0
loop = cyl(6.0, 5.0, 0, ring_y, SHELL_H - 5.0) + box(12.0, 6.0, 5.0, 0, OUT_L/2 + 2.5, SHELL_H - 5.0)
loop = loop - cyl(2.5, 7.0, 0, ring_y, SHELL_H - 6.0)
shell = shell + loop
# friction bumps inside rim that the lid lip clicks past
for sx in (-1, 1):
    shell = shell + box(0.5, 14, 0.8, sx*(IN_W/2 - 0.25), 16, LIP_H - 0.2)

# ---------- back lid (modelled in place: plate below z=0, lip going up into shell) ----------
plate = Manifold.extrude(rrect(OUT_W, OUT_L, R_OUT), LID_T).translate([0, 0, -LID_T])
lw, ll = IN_W - 2*CLR, IN_L - 2*CLR
lip = Manifold.extrude(rrect(lw, ll, R_IN - CLR), LIP_H) - \
      Manifold.extrude(rrect(lw - 2*LIP_T, ll - 2*LIP_T, R_IN - CLR - LIP_T), LIP_H + 1).translate([0, 0, -0.5])
# matching notches in the lip so it doesn't block the charger port / switch
lip = lip - box(8, 19.0, 10, lw/2, CHG_Y, -1) - box(8, 10.0, 10, -lw/2, 0, -1)
# a fingernail notch to pry the lid off
lid = plate + lip
lid = lid - box(8, 2.5, 1.0, 0, OUT_L/2 - 0.6, -LID_T - 0.5)

def export(m, path):
    mesh = m.to_mesh()
    tm = trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts, process=True)
    assert tm.is_watertight, path
    tm.export(path)
    return tm

# ---------- part envelopes (for fit check / preview), shell coords ----------
PARTS = {
  "battery 30x40x8":   box(30, 40, 8.0, -2.0, 9.05, 0.0),
  "TP4056 26x17x4.8":  box(26, 17, 4.8, IN_W/2 - 13.4, CHG_Y, 0.0),
  "switch 8.6x3.5x6":  box(3.5, 8.6, 4.0, -IN_W/2 + 1.75, 0.0, 2.2),
  "Pico 21x51 (pins trimmed)": box(21, 51, 8.1, 0, -IN_L/2 + 0.5 + 25.5, 9.3),
  "screen module": cyl(37.5/2, SCREEN_Z, 0, SCR_Y, BATT_Z + PICO_Z),
}

if __name__ == "__main__":
    import json, sys
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    s = export(shell, f"{out}/keychain_case_front.stl")
    # lid printed plate-down: flip so lip points up and sits on z=0
    l = export(lid.translate([0, 0, LID_T]), f"{out}/keychain_case_back_lid.stl")
    print(json.dumps({"front_bbox": np.round(s.extents, 2).tolist(), "lid_bbox": np.round(l.extents, 2).tolist(),
                      "assembled_thickness": SHELL_H + LID_T, "outer": [OUT_W, OUT_L]}))
