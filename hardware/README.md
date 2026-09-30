# Hardware

```
hardware/
  kicad/     KiCad project (open CAN_ECU.kicad_pro) + project symbol/footprint libraries
  fab/       preview Gerbers, drill files, BOM.csv, CPL_top.csv (regenerate from KiCad for ordering)
  gen/       Python generators - the design "source code"
```

`gen/` is how every hardware file in this project was produced. KiCad itself was not available while the files were generated, so they were written by these scripts.

| Script | Purpose |
|---|---|
| `design.py` | parts, values, part numbers and the pin→net netlist (single source of truth) |
| `lib.py` | symbol and footprint definitions |
| `board.py` | board outline and component placement |
| `routing.py` | hand routes, plane fan-out and a constrained router for the low-speed nets |
| `write_kicad.py` | writes the `.kicad_sch/.kicad_pcb/.kicad_pro/.kicad_sym/.pretty` files |
| `checks.py` | independent DRC, connectivity and plane-continuity checks |
| `validate_files.py` | re-parses the written files: syntax, schematic↔PCB netlist, ERC subset, silkscreen |
| `fab.py` | Gerber/Excellon/BOM/CPL + Gerber re-render |
| `gen_docs.py` | pin map, component list, validation report, figures |

Regenerate everything (Python 3.10+, numpy, scipy, matplotlib): `cd hardware/gen && ./build_all.sh`

**Recommended workflow once you own the design:** open the project in KiCad and continue there. KiCad becomes the source of truth from that point, and the generators are then only a record of how rev A was made. Do not mix the two workflows: re-running the generators overwrites manual KiCad edits.
