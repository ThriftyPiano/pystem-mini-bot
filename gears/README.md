# GEARS (vendored) — the Virtual Mini Bot

This directory is a pruned copy of [GEARS](https://github.com/QuirkyCort/gears)
(Generic Educational Autonomous Robotics Simulator, GPL-3.0, see `LICENSE`),
upstream commit `ea03103` (2026-08-12), plus the PySTEM Mini Bot additions
below. It is served as-is by GitHub Pages and embedded by `../simulator.html`.

## What was pruned

Only what `index.html`, `configurator.html` and `builder.html` load: the
`models/` asset packs (124 MB), the duplicate Ace/Blockly versions, unused
Ace modes/themes, `samples/`, `genURL.html`, `arena*.html`, `privacy.html`.
The World Builder therefore has no model library; everything else works.

## PySTEM additions (grep for "PySTEM" to find them)

- `minibot/` — simulator builds of the robot SDK modules: `config.py`,
  `motor.py`, `orientation.py`, `color_sensor.py`, `head.py`,
  `wonder_echo.py`. Same public API as `../examples/sdk_*.py`, implemented on
  GEARS's `simPython` bridge. `motor_pair.py` is **not** duplicated: the
  simulator loads `../examples/sdk_motor_pair.py` itself. `machine.py` is a
  minimal MicroPython `machine` (virtual `Pin` shown on the page's LED
  indicator and console; inert `PWM`/`ADC`/`I2C`; `Timer` callbacks are not
  possible in Skulpt) so beginner programs such as `led_blink.py` run.
- `js/minibotSim.js` — Skulpt module `minibot_sim` (voice-command queue —
  no UI for it yet, fed via the `minibot-voice` message — head-angle and
  pin-change reporting).
- `js/skulpt.js` — the modules above are registered in `externalLibs`, and
  Skulpt's `time` module gains MicroPython's `ticks_ms / ticks_diff /
  sleep_ms` so on-device code runs unchanged.
- `js/Robot.js` — `modelURL` / `modelHidesBody` robot options: a glTF/GLB
  drawn over the physics box, parented to it.
- `robots/minibot.json` — the Mini Bot: dimensions measured from the
  Onshape assembly (wheel Ø 5.6 cm, 8.2 cm track tread-to-tread, caster 4.95 cm
  behind the axle, line sensor 1.84 cm ahead of it). `in1` = colour sensor, `in2` =
  gyro; `outA`/`outB` = left/right wheel.
- `robots/minibot.glb` — the Onshape export, re-rooted into the GEARS body
  frame (x right, y up, z forward, cm, origin at the body centre) and
  recoloured like the real robot (black wheels and battery box, green PCB,
  dark-grey StickS3, red printed parts). Regenerate from a fresh Onshape glTF
  export with `robots/build_minibot_glb.py <assembly.gltf>`; the body-centre
  constants at the top of the script are the only thing to re-measure if
  the chassis changes.
- `index.html` — the LED indicator, `?embed=1` (hides
  GEARS's header, tabs and menus so only the simulator view shows), and a
  `postMessage` API used by `../simulator.html` (`minibot-load / run / stop /
  voice / get-code`, `minibot-ready`).
- `js/main.js` — the "What's New" popup no longer auto-shows.
- `js/simPanel.js` — `stopSim()` also stops both wheels (upstream leaves a
  `run-forever` drive spinning after Python is interrupted). In embed mode
  the ruler, virtual joystick and hub-button widgets are hidden.

## Updating GEARS

Re-copy the upstream `public/` subset, then re-apply the additions above;
each is a small, commented block.
