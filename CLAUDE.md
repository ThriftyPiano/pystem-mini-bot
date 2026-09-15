# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PySTEM Mini Bot — a browser-based programming environment for an ESP32-based educational robot, plus a voice-command controller built on the M5StickS3. The site is deployed as a static GitHub Pages site at `robot.pystem.com` (see `CNAME`); there is no backend and no package manager. For the website, editing an HTML/JS file and reloading the page is the full dev loop. The only thing with a real build step is the StickS3 speech firmware (`speech-firmware/build.sh`).

## Architecture

The repo has six more-or-less independent layers; understanding the split is essential before making changes:

1. **Static site (root `*.html`, `*.js`, `images/`)** — multi-page site. `index.html` is the landing page; `assembly.html`, `firmware.html` are docs; `ide.html` is the Monaco-based Python IDE; `scratch.html` is a Blockly visual-programming front end that generates Python; `speech-commands.html` is the browser-side speech-model trainer (see layer 4). The navbar is copy-pasted into every page by hand — adding a page means editing all of them. Both IDEs share the same set of JS modules loaded as plain `<script>` tags (no bundler):
   - `robot.js` — `RobotController` class. Owns the WebSerial connection to the ESP32, the background read loop / serial buffer, and the **hex-encoded chunked upload protocol** (code → hex string → 512-byte chunks → MicroPython commands that reconstruct bytes on-device, with `gc.collect()` between chunks). When changing how files are sent to the device, this is the file to touch.
   - `file.js` — `FileManager`. Persists user files in `localStorage` under key `esp32-robot-files`. The IDE has no server-side storage.
   - `terminal.js` — `SerialTerminal`. Renders the serial monitor pane.
   - `example.js` — `exampleManager`. Loads `examples/*.py` via `fetch()` so they can be opened in the IDE. **When adding a new example, also add its filename to the `exampleFiles` array in `example.js`** — it is hard-coded, not auto-discovered.
   - `monaco-micropython-v2.js` — Monaco language config and autocomplete data for MicroPython, derived from the `.pyi` files in `stubs/`.

2. **Robot firmware (`firmware/ESP32_GENERIC-20250415-v1.25.0.bin`)** — prebuilt MicroPython 1.25 image flashed to the robot's ESP32 at offset `0x1000`. Source for this `.bin` is not in the repo; only the binary is shipped (used by `firmware.html` flash flow).

3. **Robot Python SDK (`examples/sdk_*.py`)** — the on-device library that user programs `import`. It is shipped to students *as example files* rather than as a separate package; `sdk_boot.py` is the entry point and the other `sdk_*` modules implement a SPIKE Prime-compatible API (`motor`, `motor_pair`, `color_sensor`, `orientation`). Compatibility with the SPIKE Prime function signatures is a deliberate design constraint — preserve it when editing these files. The same SDK runs on both robots: `sdk_config.py` detects the board at import (`BOARD = 'maxv1'` for the original ESP32 Max V1, `'sticks3'` for the StickS3 on the Bot HAT, keyed on `sys.implementation._machine`) and every pin, bus and IMU choice is looked up there — never hard-code a pin in another `sdk_*` file. `sdk_orientation.py` has two IMU backends behind one `read()` interface (accel in g, gyro in deg/s): `MPU6050` on the Max V1's external I2C bus, `BMI270` via the frozen `sticks3` module on the StickS3. The StickS3 robot has no WonderEcho — voice input comes from the on-device `speech_commands` module, driven by a separate `main.py`.

4. **StickS3 speech-commands stack** — on-device keyword spotting for the M5StickS3 (ESP32-S3-PICO-1, 8 MB flash / 8 MB octal PSRAM). Two halves that must agree with each other:
   - **Browser trainer (`speech-commands.html` + `speech-commands/`)** — records 1 s clips, runs them through an MFCC front end compiled to WASM (`mfcc.js`/`mfcc.wasm`) and a frozen TF.js keyword-spotting base model (`model.json` + `group1-shard1of1.bin`) to get a 576-dim feature vector, then trains a dense+softmax classifier in the browser. Samples live in `localStorage` under `ss-<isoTime>` keys. `noise*.wav`/`music*.wav` are background-augmentation audio. Output is a generated `speech_model.py` (base64 classifier weights + `labels` + `predict/snapshot/save` helpers) that the student uploads to the stick with the IDE. **`mfcc.wasm` is prebuilt (Emscripten); its source is not in the repo.**
   - **Firmware (`speech-firmware/`)** — a custom MicroPython v1.25 build for `ESP32_GENERIC_S3` / `SPIRAM_OCT` with a user C module `speech_commands` (`modules/speech_commands/`: `nnom_module.c` bindings, `kws.c` inference, `weights.h` base model) built on NNoM, plus frozen board drivers in `device/` (`sticks3.py` board module, `es8311.py` codec, `m5pm1.py` power chip, `st7789py.py` LCD, `bmi270*.py` IMU — see `manifest.py`). `device/main.py` is the demo (not frozen; uploaded via the IDE): speech recognition in a `_thread` on the second core, robot control loop on the main thread. The prebuilt `speech-commands-sticks3.bin` is what `firmware.html` serves; `build.sh` regenerates it (pinned ESP-IDF v5.4.1, MicroPython v1.25.0, NNoM commit; downloads everything into gitignored `build/`). `README.md` there has the pin map and the Python API.

5. **Bot HAT hardware (`hardware/sticks3-bot-hat/`)** — KiCad design for the carrier PCB that turns a StickS3 into the Mini Bot's brain (buck converter, 4 servo + 4 sensor headers). `gen/design.py` is the single source of truth for connectivity; `gen_pcb.py`/`gen_sch.py` generate the board and schematic from it, `export.sh` writes the JLCPCB `fab/` outputs. Its `README.md` GPIO table is the authoritative pin map for any StickS3 robot code (wheels G5/G4, pan/tilt G6/G7, encoders G43/G44, color sensors G1/G8).

6. **Virtual robot (`simulator.html` + `gears/`)** — a vendored, pruned copy of [GEARS](https://github.com/QuirkyCort/gears) (GPL-3.0; Babylon.js + Ammo.js physics + Skulpt running Python in the browser) with the Mini Bot bolted on. `gears/README.md` lists every local modification (grep `PySTEM`). The design goal is that **a student's `main.py` runs unchanged in the simulator and on the robot**:
   - `gears/minibot/` holds simulator builds of the SDK modules (`config`, `motor`, `orientation`, `color_sensor`, `head`, `wonder_echo`) with the same public API, written in Python against GEARS's `simPython` bridge. **`motor_pair.py` is not duplicated** — `gears/js/skulpt.js` loads `../examples/sdk_motor_pair.py` itself, so the pairing/turning logic has one source. Keep the shim's signatures in lockstep with `examples/sdk_*.py`.
   - `gears/js/skulpt.js` registers those modules, deletes Skulpt's placeholder `config` package (it would shadow ours), and extends Skulpt's `time` with MicroPython's `ticks_ms / ticks_diff / sleep_ms`.
   - `gears/robots/minibot.json` is the robot (dimensions measured from the Onshape assembly; `outA/outB` wheels, `in1` colour sensor, `in2` gyro); `gears/robots/minibot.glb` is the Onshape export re-rooted into GEARS's body frame (x right, y up, z forward, cm, origin at the body centre) and drawn over the physics box via the `modelURL` option added to `gears/js/Robot.js`.
   - `simulator.html` embeds `gears/index.html` in an iframe and drives it with `postMessage` (`minibot-load / run / stop / voice`); `ide.html`'s "Run in Simulator" hands the editor contents over through `localStorage['minibot-sim-code']`.

### Cross-cutting concerns worth knowing before editing

- **WebSerial USB filter**: `robot.js` filters on CH340 (`vendorId 0x1A86, productId 0x7523`) for the robot and on Espressif native USB (`0x303A, 0x832B`) for the StickS3. Other USB-serial chips will not show up in the connect dialog unless added here.
- **Hex upload protocol** is the workaround for ESP32 filesystem fragility (`OSError 28`) and special-character corruption — don't replace it with a naive `f.write(code)` without understanding why it exists (see README "Technical Challenges" §3).
- **Encoder/motor control tuning constants** in `examples/sdk_motor*.py` (5ms encoder debounce, 200ms button debounce, 15% min power, 30° tolerance band) were tuned against real hardware; treat them as load-bearing magic numbers, not arbitrary defaults.
- **Two different flash procedures**: the robot's ESP32 flashes at `0x1000`; the StickS3 (ESP32-S3) flashes at `0x0` with `--chip esp32s3`. Flashing the speech firmware replaces the factory UiFlow2 image (restorable with M5Burner).
- **The speech model is split across three artifacts that must match**: the base model in the firmware (`weights.h`), the same base model in the browser (`model.json` + `mfcc.wasm`), and the per-student classifier (`speech_model.py`, 576 features → N labels). Changing the MFCC parameters (61 frames × 12 coefficients, 732-byte snapshot) or the base model means regenerating all of them together. `sp.predict()` packs its result as `label_index * 1000 + probability`.
- **`build.sh` patches MicroPython in place**: it pins tinyusb `<0.18`, un-pins `_thread` tasks from the MicroPython core (`tskNO_AFFINITY`), releases the GIL around blocking I2S DMA reads/writes, and enlarges the S3 caches. The dual-core demo depends on these; a stock MicroPython build will stall the control loop ~120 ms per inference. `-Ofast` is applied per-source to the model code only — note the `DIRECTORY ${CMAKE_SOURCE_DIR}` scoping in `micropython.cmake`, without which the objects silently build at `-O0` (4x slower).
- **A running `_thread` blocks soft reset**, which locks out the IDE / mpremote. `device/main.py` sleeps 2 s before starting the speech thread so tools can Ctrl-C at boot, and clears `running` in a `finally` so the thread exits cleanly. Keep that pattern in any StickS3 program that uses threads.
- **StickS3 I2C bus runs at 100 kHz** (`sticks3.i2c()`): the M5PM1 power chip NAKs at 400 kHz. S3 GPIOs are not 5 V-tolerant — sensor headers on the HAT are 3V3.
- **Yaw is clockwise-positive as far as `motor_pair.py` is concerned**: its straight-line correction speeds the left wheel up when yaw drops, and `move_tank_for_degrees(+90)` spins clockwise. An IMU backend with the opposite sign turns that correction into positive feedback and the robot spirals — that is what `config.IMU_AXES` is for (flip `z` for a board whose gyro reads counter-clockwise-positive). The simulator's gyro is clockwise-positive natively.
- **GEARS component meshes are physics bodies**: the colour sensor is a 2×2×3 cm box, so placing it at the real sensor's 1 cm height pushes it through the floor and lifts the front wheels. Keep sensor components clear of the ground in `minibot.json`; the mesh overlay is purely visual.

## Type checking (the only host-side check)

`pyrightconfig.json` configures Pyright for all `**/*.py` — the on-device Python in `examples/` and `speech-firmware/device/`, and the KiCad generator scripts in `hardware/`. The `stubs/` directory holds hand-written `.pyi` files for MicroPython modules (`machine`, `esp32`, `network`, `time`, `math`) — these stubs are also the source of truth that `monaco-micropython-v2.js` autocomplete is generated from, so keep them in sync when adding new APIs. There are no stubs for `speech_commands` or the frozen `sticks3` drivers yet; missing-import reports are suppressed, so those imports don't error.

Run: `pyright` (from repo root).

## Building the speech firmware

```bash
cd speech-firmware && ./build.sh
```

Clones ESP-IDF, MicroPython and NNoM into `speech-firmware/build/` on first run (slow; needs the S3 toolchain installed via `install.sh esp32s3`), applies the patches above, and writes `speech-commands-sticks3.bin`. The script refuses to run inside an active virtualenv and re-execs itself with the venv stripped. Commit the resulting `.bin` — it is what the website serves.

## Testing

There is no test suite. Behavior is validated by loading a page in a browser, connecting to a physical robot over WebSerial, and running the relevant example. When changing IDE/serial code, exercise the connect → upload → run path end-to-end; static analysis alone will not catch the protocol-level bugs this code is most prone to.

The simulator can be tested headless: serve the repo root with `python3 -m http.server`, drive `gears/index.html?robotJSON=robots/minibot.json` with Playwright on the system Chromium (`--use-gl=swiftshader`), load a program via `window.postMessage({type: 'minibot-load', code, run: true})` and read `simPanel.$consoleContent.text()` and `robot.body.absolutePosition`. Headless frame rates are ~6–15 fps, so expect larger position overshoot than in a real browser; it proves the chain works, not the tuning.

For the speech stack, the equivalent loop is: train a model on `speech-commands.html` → download `speech_model.py` → upload it and `device/main.py` to a flashed StickS3 through the IDE → speak the commands and watch the LCD / serial output. `main.py` prints the worst observed control-loop delay; a jump from single-digit ms to ~120 ms means the GIL/affinity patches didn't take.
