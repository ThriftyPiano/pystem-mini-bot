# Frozen modules for the StickS3 speech-commands firmware: board support
# for all on-board hardware (LCD, mic, speaker, IMU, power chip, buttons).
include("$(PORT_DIR)/boards/manifest.py")
freeze(
    "device",
    (
        "sticks3.py",
        "es8311.py",
        "m5pm1.py",
        "st7789py.py",
        "vga1_16x32.py",
        "bmi270.py",
        "bmi270_i2c_helpers.py",
        "bmi270_config_file.py",
    ),
)
