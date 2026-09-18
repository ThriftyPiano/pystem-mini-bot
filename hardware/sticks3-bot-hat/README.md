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

1. Run `gen/export.sh` (needs KiCad 10) — it writes `fab/`:
   `sticks3-bot-hat-gerbers.zip`, `bom.csv`, `positions.csv`.
2. Upload the gerber zip at jlcpcb.com. 2-layer, 1.6 mm, any color.
3. Enable "PCB Assembly" (economy, top side). Upload `bom.csv` and
   `positions.csv`. U1 (C2071056) and L1 (C57254) are pre-matched; let the
   BOM matcher confirm the passives, and pick in-stock generics for the
   headers (J1 must be the **right-angle / 90-degree** 2x8; J8/J10 are 1x4,
   the rest 1x3), the 5.5x2.1 barrel jack (PJ-102A type), and the 470 uF
   radial cap. `fab/cpl-jlcpcb-corrected.csv` is the hand-corrected
   placement file (JLC's part rotations) that the v3 batch was built from;
   only R3 moved and R4/R5 were added since, so re-check those three.
   Mounting holes are M3 (3.2 mm); use screws with heads <= 5.5 mm, the
   two left holes sit close to the J1/J2 headers.

## First-article checklist (board #1, before servos)

1. Visual: no bridges around U1/L1.
2. Battery unplugged: no short between servo rail and GND.
3. Battery box plugged in and switched on: 5.0 V +-0.1 on J1 pin 15
   (5V_IN) vs GND, LED faintly lit (it runs at ~0.14 mA on purpose).
   Battery box must be wired center-positive.
   With an HC-SR04 on DIST and a 5 V level on its ECHO pin, J1 pin 9 (G8)
   must read ~3.3 V — that's the R4/R5 divider doing its job.
4. **Orientation check — the HAT2 socket is unkeyed**: plug the stick in
   unpowered and meter continuity from the stick's USB shell (GND) to J1
   pin 1 (the silkscreen-marked corner pin). If it beeps, orientation is
   right; if the stick faces screen-down, flip it 180 and re-check — then
   mark the correct side on the silk. A flipped stick would put 5 V on
   GPIO pins.
5. The stick cantilevers off the board edge on the header — support its far
   end with a foam pad or standoff on the chassis.

## Design sources

Everything is generated from `gen/design.py` (single source of truth for
connectivity) by `gen/gen_pcb.py` (board via KiCad's pcbnew API +
freerouting) and `gen/gen_sch.py` (schematic). The routed board was then
hand-finished, so later revisions edit `sticks3-bot-hat.kicad_pcb` in place
(`gen/tools/rework_v4.py` is the scripted v3 -> v4 edit) rather than
regenerating it. `gen/export.sh` runs ERC/DRC and writes the fab outputs; it
uses `kicad-cli` if installed, otherwise the `kicad/kicad:10.0` docker
image. DRC is clean apart from two courtyard warnings where the M3 holes'
screw-head circle grazes J1/J2.

- `sticks3-bot-hat.kicad_pcb` — routed 2-layer board, 48 x 33 mm, GND pours
- `sticks3-bot-hat.kicad_sch` / `sticks3-bot-hat-schematic.pdf`
- `sticks3-bot-hat.pretty/` — local footprint for the SS12D10 switch
- `render-top.png`, `render-bottom.png`, `render-3d.png` (regenerate with `gen/render.sh`)

HAT2 pinout reference: [M5Stack StickS3 docs](https://docs.m5stack.com/en/core/StickS3).
