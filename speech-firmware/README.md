# Speech-commands firmware for M5StickS3

MicroPython firmware for the M5StickS3 with on-device speech-command
recognition, exposed to Python as the `speech_commands` module.

## How it works

- Audio pipeline (in C, built on [NNoM](https://github.com/majianjia/nnom)):
  16 kHz PCM → MFCC (61 frames × 12 coefficients) → small convolutional
  keyword-spotting base model → 576-dim feature vector → user-trained
  dense + softmax classifier.
- The base model is compiled into the firmware (`weights.h`). The final
  classifier layer is trained in the browser and loaded at runtime from a
  generated `speech_model.py` via `speech_commands.init(data)`.
- `speech_commands.predict(audio, bias, gain)` returns
  `label_index * 1000 + probability`; `speech_commands.export_mfcc(buf)`
  exports the current 732-byte MFCC snapshot so misclassified samples can
  be saved on-device and used for fine-tuning in the browser.

## Layout

- `modules/speech_commands/` — the user C module (`nnom_module.c` bindings,
  `kws.c` model assembly/inference, `weights.h` base model).
- `device/` — board drivers, all frozen into the firmware (see
  `manifest.py`) so every piece of StickS3 hardware is usable out of the
  box:
  - `sticks3.py` — board module: `display()`, `imu()`, `microphone()`,
    `speaker()`, `buttons()`.
  - `es8311.py` — ES8311 codec driver (I2S slave, internal MCLK derived
    from BCLK, 16 kHz 16-bit mono ADC + DAC).
  - `m5pm1.py` — M5PM1 power chip (gates LCD power and the speaker amp).
  - `st7789py.py` + `vga1_16x32.py` — LCD driver and bitmap font.
  - `bmi270*.py` — BMI270 IMU driver.
  - `main.py` — demo: continuous recognition loop with LCD feedback plus
    on-device training-sample capture via the two buttons (not frozen;
    upload via the IDE).
- `build.sh` — reproducible build (pinned ESP-IDF v5.4.1, MicroPython
  v1.25.0, NNoM), targeting `ESP32_GENERIC_S3` with octal PSRAM. The
  recognition sources are compiled `-Ofast` (scoped to the model code
  only, so `-ffast-math` cannot affect the MicroPython core).

## StickS3 wiring facts used here

- ES8311 codec: I2C addr 0x18 on SDA=G47 / SCL=G48 (shared with the IMU).
- I2S: BCLK=G17, WS=G15, mic data (codec→ESP)=G16, speaker data=G14,
  MCLK=G18 (unused — the codec is clocked from BCLK).
- Buttons: KEY1=G11, KEY2=G12. Grove connector: G13.

## Build

```bash
./build.sh
```

Output: `speech-commands-sticks3.bin`. Flash at offset **0x0** (ESP32-S3,
unlike the original ESP32 which flashes at 0x1000).

## Credits

Neural-network inference is powered by [NNoM](https://github.com/majianjia/nnom)
(Neural Network on Microcontroller) by Jianjia Ma, licensed under Apache-2.0.
The MFCC front end and the keyword-spotting model architecture are derived from
NNoM's `keyword_spotting` example, trained on the Google Speech Commands
dataset.

Bundled drivers: `st7789py.py` and `vga1_16x32.py` from
[st7789py_mpy](https://github.com/russhughes/st7789py_mpy) by Russ Hughes
(MIT); `bmi270*.py` from
[MicroPython_BMI270](https://github.com/jposada202020/MicroPython_BMI270)
(MIT).
