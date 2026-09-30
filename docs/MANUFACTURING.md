# Manufacturing notes

## PCB fabrication spec (give this to the PCB fab)

| Parameter | Value |
|---|---|
| Dimensions | 80.0 × 60.0 mm, rounded corners R2 |
| Layers | 4 (F.Cu, In1.Cu GND, In2.Cu +3V3, B.Cu) |
| Thickness | 1.6 mm FR-4, Tg ≥ 135 °C (standard) |
| Copper | 1 oz outer, 0.5 oz (or 1 oz) inner |
| Min track / space | 0.20 / 0.20 mm (design uses ≥ 0.25 mm tracks) |
| Min drill | 0.30 mm (vias 0.3 / 0.6 mm) |
| Solder mask | both sides, any colour; vias tented |
| Silkscreen | top only |
| Surface finish | ENIG recommended (flat pads for LGA-14 / LQFP); HASL lead-free acceptable |
| Impedance control | not required |

## Output files

### A. Preferred: re-plot from KiCad

In KiCad (7/8/9) with `hardware/kicad/CAN_ECU.kicad_pcb` open:

1. Press **B** to fill zones, then run DRC.
2. **File → Fabrication Outputs → Gerbers (.gbr)**.
   * Layers: F.Cu, In1.Cu, In2.Cu, B.Cu, F.Paste, F.Silkscreen, F.Mask, B.Mask, Edge.Cuts.
   * Check *Use Protel filename extensions* if your fab asks for it.
   * Click **Generate Drill Files…** (Excellon, PTH and NPTH in separate files, mm).
3. **File → Fabrication Outputs → Component Placement (.pos)** (CSV, mm, top side) and **BOM**.
4. Zip the folder and upload it to the fab.

### B. Pre-generated preview outputs (`hardware/fab/`)

Generated without KiCad by `hardware/gen/fab.py` from the same design data:

| File | Content |
|---|---|
| `gerber/CAN_ECU-F_Cu.gtl`, `-In1_Cu.g2`, `-In2_Cu.g3`, `-B_Cu.gbl` | Copper incl. poured planes (solid pad connections, no thermal reliefs, isolated islands not removed) |
| `gerber/CAN_ECU-F_Mask.gts`, `-B_Mask.gbs`, `-F_Paste.gtp`, `-F_Silkscreen.gto`, `-Edge_Cuts.gm1` | Mask (0.05 mm expansion), paste, legend, outline |
| `drill/CAN_ECU-PTH.drl`, `drill/CAN_ECU-NPTH.drl` | Excellon, metric, Y-axis matches the Gerbers |
| `BOM.csv` | Grouped BOM with rough cost estimates |
| `CPL_top.csv` | Pick-and-place, origin = bottom-left board corner, Y up, rotation CCW |

The Gerbers were re-rendered by an independent parser (`docs/img/gerber_*.png`) for a visual check. **They are review previews:** use them to inspect the design in any Gerber viewer. **Order from the KiCad re-plot (A)**, which also adds thermal reliefs and removes copper islands.

## Assembly notes

* **U5 (LSM6DS3TR-C, LGA-14, 2.5 × 3 mm, no leads):** needs stencil + reflow or hot air. Pin 1 marking is on the package top. The board has a silk dot at pin 1. Keep reflow profile peak ≤ 260 °C, as specified by ST for the LGA.
* **U3 (LQFP48 0.5 mm):** hand-solderable with drag soldering + flux. Check for bridges under magnification.
* **THT parts (hand-soldered after reflow):** J1-J5, JP2, SW1, SW2, C2, U1 (R-78E). Mount the R-78E upright with the label side as shown on the silk.
* **Rotation offsets:** pick-and-place rotations follow KiCad's convention. Many assembly services apply their own per-footprint offsets (especially for SOT-23, SOIC and diodes), so review the assembler's placement preview.
* **Shunts:** JP2 needs **2 jumper shunts** (2.54 mm) on end-of-bus boards. JP1/JP3/JP4 are solder jumpers: close them with a solder blob.

## Cost estimate (rough)

| Item | Estimate |
|---|---|
| Components per board (qty-10 distributor pricing, see `BOM.csv`) | ≈ USD 19 |
| 4-layer PCB 80 × 60 mm, qty 5 at a low-cost prototype fab | ≈ USD 2-8 per board + shipping |
| Stencil (optional, recommended for the LGA) | ≈ USD 8-15 |

These are **estimates only** (2025/2026 price levels). Check current distributor and fab prices.
