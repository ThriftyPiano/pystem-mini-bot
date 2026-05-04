# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PySTEM Mini Bot — a browser-based programming environment for an ESP32-based educational robot. The site is deployed as a static GitHub Pages site at `robot.pystem.com` (see `CNAME`); there is no backend, no build step, and no package manager. Editing an HTML/JS file and reloading the page is the full dev loop.

## Architecture

The repo has three more-or-less independent layers; understanding the split is essential before making changes:

1. **Static site (root `*.html`, `*.js`, `images/`)** — multi-page site. `index.html` is the landing page; `assembly.html`, `firmware.html` are docs; `ide.html` is the Monaco-based Python IDE; `scratch.html` is a Blockly visual-programming front end that generates Python. Both IDEs share the same set of JS modules loaded as plain `<script>` tags (no bundler):
   - `robot.js` — `RobotController` class. Owns the WebSerial connection to the ESP32, the background read loop / serial buffer, and the **hex-encoded chunked upload protocol** (code → hex string → 512-byte chunks → MicroPython commands that reconstruct bytes on-device, with `gc.collect()` between chunks). When changing how files are sent to the device, this is the file to touch.
   - `file.js` — `FileManager`. Persists user files in `localStorage` under key `esp32-robot-files`. The IDE has no server-side storage.
   - `terminal.js` — `SerialTerminal`. Renders the serial monitor pane.
   - `example.js` — `exampleManager`. Loads `examples/*.py` via `fetch()` so they can be opened in the IDE. **When adding a new example, also add its filename to the `exampleFiles` array in `example.js`** — it is hard-coded, not auto-discovered.
   - `monaco-micropython-v2.js` — Monaco language config and autocomplete data for MicroPython, derived from the `.pyi` files in `stubs/`.

2. **On-device firmware (`firmware/ESP32_GENERIC-20250415-v1.25.0.bin`)** — prebuilt MicroPython 1.25 image flashed to the ESP32. Source for this `.bin` is not in the repo; only the binary is shipped (used by `firmware.html` flash flow).

3. **Robot Python SDK (`examples/sdk_*.py`)** — the on-device library that user programs `import`. It is shipped to students *as example files* rather than as a separate package; `sdk_boot.py` is the entry point and the other `sdk_*` modules implement a SPIKE Prime-compatible API (`motor`, `motor_pair`, `color_sensor`, `orientation`). Compatibility with the SPIKE Prime function signatures is a deliberate design constraint — preserve it when editing these files.

### Cross-cutting concerns worth knowing before editing

- **WebSerial USB filter**: `robot.js` filters on CH340 (`vendorId 0x1A86, productId 0x7523`). Other USB-serial chips will not show up in the connect dialog unless added here.
- **Hex upload protocol** is the workaround for ESP32 filesystem fragility (`OSError 28`) and special-character corruption — don't replace it with a naive `f.write(code)` without understanding why it exists (see README "Technical Challenges" §3).
- **Encoder/motor control tuning constants** in `examples/sdk_motor*.py` (5ms encoder debounce, 200ms button debounce, 15% min power, 30° tolerance band) were tuned against real hardware; treat them as load-bearing magic numbers, not arbitrary defaults.

## Type checking (the only "build" tool)

`pyrightconfig.json` configures Pyright for the on-device Python in `examples/`. The `stubs/` directory holds hand-written `.pyi` files for MicroPython modules (`machine`, `esp32`, `network`, `time`, `math`) — these stubs are also the source of truth that `monaco-micropython-v2.js` autocomplete is generated from, so keep them in sync when adding new APIs.

Run: `pyright` (from repo root).

## Testing

There is no test suite. Behavior is validated by loading a page in a browser, connecting to a physical robot over WebSerial, and running the relevant example. When changing IDE/serial code, exercise the connect → upload → run path end-to-end; static analysis alone will not catch the protocol-level bugs this code is most prone to.
