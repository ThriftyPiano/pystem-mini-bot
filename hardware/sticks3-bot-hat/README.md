# PySTEM Mini Bot — StickS3 HAT

A 48 x 33 mm carrier PCB (4 servo + 4 sensor headers in two rows) that turns an M5StickS3 into the Mini Bot's
brain. The stick plugs into a right-angle HAT2 header and **lies flat** on
the robot (screen up, body overhanging the board edge); everything else is
solderless connectors, so a batch of bots assembles with a screwdriver.

```
4xAA box (6V, own switch) -> 5.5x2.1 barrel jack (center +)
    +-> servo rail (6V, 4x 3-pin headers, bottom row)
    +-> AP63205 buck (5.0V) -> StickS3 5V_IN
StickS3 3V3 -> encoder / color-sensor headers (S3 pins are NOT 5V-tolerant)
    +-> buck 5V -> DIST header (HC-SR04); its 5V ECHO is divided to 3.3V by R4/R5
```

Never feed the 6 V pack into the stick directly: fresh alkalines sit at
6.4 V and the stick's internal power chips are 5 V parts — that's what the
buck (U1 + L1 + C1/C3/C4/C5) is for. C7 (470 uF) rides through servo-stall
sag so the stick doesn't brown out. The IMU is the stick's internal BMI270
(`sticks3.imu()`), so there is no IMU connector; I2C pull-up resistors were
dropped with it.

## Connectors

| Connector | For | Signals |
|-----------|-----|---------|
| J1 (2x8 right-angle) | StickS3 HAT2 socket | all of the below |
| WHEEL A / WHEEL B | continuous-rotation wheel servos | G5 / G4, 6 V rail |
| PAN / TILT | head positional servos | G6 / G7, 6 V rail |
| ENC A / ENC B (1x3: `V G D`) | LM393 photo-interrupter wheel encoders, D0 output | G43 / G44, 3V3 |
| COLOR (1x4: `V G - A`) | TCRT5000 reflection / line sensor module, A0 output | G1 (ADC1), 3V3 |
| DIST (1x4: `5 T E G`) | HC-SR04 ultrasonic distance sensor | TRIG G2, ECHO G8 (via 1k/2k divider), 5 V |
| 6V IN (5.5x2.1 barrel jack, top entry, next to the stick) | 4xAA battery box with barrel plug + switch | center = +6 V |

Sensor header pin order follows the common LM393-based modules (`VCC GND
D0 A0`), so a straight 3- or 4-wire Dupont cable connects the encoder or
reflection module pin-for-pin; the COLOR header's third pin is unconnected
(the module's D0). DIST matches the HC-SR04's own `VCC TRIG ECHO GND`.
The power LED (D1, 22k series resistor) is deliberately dim: it only shows
that the 5 V rail is up.

The stick's own Grove port (G9/G10) stays free — the WonderEcho voice
module plugs in there directly.

### Header rows

With the stick screen up, its socket has the GPIO row (G5 G4 G6 G7 G43 G44
G2 G3) on top and the power row (GND EXT_5V BOOT G1 G8 BAT 3V3 5V_IN)
underneath, GND in the column nearest J1's square pad. A right-angle header
feeds its upper pins from the pad row farther from the board edge (J1's odd
pads), so odd pads carry the GPIOs and even pads the power row. **v3 and v4
boards were built with the rows the other way round** (M5Stack's pinout
table numbers the socket from the power row, which was copied into J1). On
those boards nothing is powered and the buck's 5 V lands on G3. Fix in the
field: 11 female-female Dupont wires from the stick's socket to the J1 pads,
same column, other row (GND→2, 3V3→14, 5V_IN→16, G1→8, G8→10, G5→1, G4→3,
G6→5, G7→7, G43→9, G44→11); tested on a v3 board with all sensors and
servos. v5 swaps the rows in the design (`gen/tools/rework_v5_j1rows.py`).

## GPIO map (for the firmware port)

| Role | GPIO | Notes |
|------|------|-------|
| Servo A (left wheel) | G5 | LEDC PWM, 50 Hz |
| Servo B (right wheel) | G4 | LEDC PWM, 50 Hz |
| Head pan | G6 | LEDC PWM, 50 Hz |
| Head tilt | G7 | LEDC PWM, 50 Hz |
| Encoder A | G43 | input, pull-up (UART0 TX pin — free with native USB) |
| Encoder B | G44 | input, pull-up (UART0 RX pin — free with native USB) |
| Color / reflection sensor (port C) | G1 | ADC1_CH0 |
| Distance sensor TRIG (port D) | G2 | output, 10 us pulse |
| Distance sensor ECHO (port D) | G8 | input, 5 V pulse divided to 3.3 V on the HAT; `machine.time_pulse_us` |
| IMU | internal BMI270 | via `sticks3.imu()` |

## Ordering a batch (JLCPCB)

1. The committed `fab/` outputs (`sticks3-bot-hat-gerbers.zip`, `bom.csv`,
   `positions.csv`) are the v5 exports. To regenerate, run `gen/export.sh`
   (needs KiCad 10) — it refills the zones itself before exporting, since
   `kicad-cli` exports whatever fill is stored in the board file.
2. Upload the gerber zip at jlcpcb.com. 2-layer, 1.6 mm, any color.
3. Enable "PCB Assembly" (economy, top side). Upload `bom.csv` and
   `cpl-jlcpcb-corrected.csv` (not `positions.csv`, see below). Every BOM
   row carries an LCSC number that was matched for the v5 order, so the
   matcher should resolve all of them without a manual search; just check
   nothing shows as out of stock (backups are listed above the `BOM` table
   in `gen/design.py`). Two numbers in older BOMs were wrong: C4190 is 2.2k
   (not 22k) and C4109 is the 0402 2k — R3 is C31850 and R5 is C22975 now.
   `positions.csv` is kicad-cli's raw placement export (KiCad rotations);
   `fab/cpl-jlcpcb-corrected.csv` is the same placement in JLC's column
   format with the part rotations hand-corrected in JLC's preview, and is
   what the boards were built from. `export.sh` regenerates `positions.csv`
   so a moved part shows up as a diff; carry that change into the CPL by
   hand and re-check the rotation in JLC's preview.
   Mounting holes are M3 (3.2 mm); use screws with heads <= 5.5 mm, the
   two left holes sit close to the J1/J2 headers.

## First-article checklist (board #1, before servos)

1. Visual: no bridges around U1/L1.
2. Battery unplugged: no short between servo rail and GND.
3. Battery box plugged in and switched on (stick removed): 5.0 V +-0.1 on
   J1 pin 16 (5V_IN, even row, last column) vs GND, LED faintly lit (it runs at ~0.14 mA on purpose).
   Battery box must be wired center-positive.
   With an HC-SR04 on DIST and a 5 V level on its ECHO pin, J1 pin 10 (G8)
   must read ~3.3 V — that's the R4/R5 divider doing its job.
4. **Orientation check — the HAT2 socket is unkeyed**: plug the stick in
   screen up, power it from USB only, and meter from the stick's USB-C
   shell (GND) to the J1 pads: pin 2 (the round pad beside the square
   pin 1) must read 0 V and pin 14 (same row, seventh column) 3.3 V. If
   those voltages show up on the square-pad row instead, the header rows
   are swapped (the v3/v4 boards) — see "Header rows" below. Never power
   the battery box with the stick plugged in until this check passes: a
   mis-seated stick gets the buck's 5 V on a GPIO or on its GND.
5. The stick cantilevers off the board edge on the header — support its far
   end with a foam pad or standoff on the chassis.

## Design sources

Everything is generated from `gen/design.py` (single source of truth for
connectivity) by `gen/gen_pcb.py` (board via KiCad's pcbnew API +
freerouting) and `gen/gen_sch.py` (schematic). The routed board was then
hand-finished, so later revisions edit `sticks3-bot-hat.kicad_pcb` in place
(`gen/tools/rework_v4.py` is the scripted v3 -> v4 edit, run in the KiCad
docker image; `gen/tools/rework_v5_j1rows.py` is the v4 -> v5 J1 row swap,
plain text edit, no pcbnew needed) rather than regenerating it. `gen/export.sh` runs ERC/DRC and writes the fab outputs; it
uses `kicad-cli` if installed, otherwise the `kicad/kicad:10.0` docker
image. DRC is clean apart from two courtyard warnings where the M3 holes'
screw-head circle grazes J1/J2.

- `sticks3-bot-hat.kicad_pcb` — routed 2-layer board, 48 x 33 mm, GND pours
- `sticks3-bot-hat.kicad_sch` / `sticks3-bot-hat-schematic.pdf`
- `sticks3-bot-hat.pretty/` — local footprint for the SS12D10 switch
- `render-top.png`, `render-bottom.png`, `render-3d.png` (regenerate with `gen/render.sh`)

### Finishing v5 — done

The v5 row swap was made without KiCad (text edits, `gen/tools/rework_v5_j1rows.py`);
the finishing pass was run with KiCad 10.0.6 on the Mac: zones refilled and
saved into the board file, DRC clean apart from the two known M3 courtyard
grazes, ERC clean, `fab/` regenerated by `gen/export.sh` and the render PNGs
refreshed by `gen/render.sh` (on macOS pass
`KICAD_3DMODELS=~/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels`).
v5 is ready to order at JLCPCB per "Ordering a batch";
`fab/cpl-jlcpcb-corrected.csv` is unchanged (no part moved in v5).

HAT2 pinout reference: [M5Stack StickS3 docs](https://docs.m5stack.com/en/core/StickS3).
