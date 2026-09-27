# Frozen modules for the StickS3 speech-commands firmware: board support
# for all on-board hardware (LCD, mic, speaker, IMU, power chip, buttons),
# the robot SDK, and a default boot.py / main.py.
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
# build/sdk is staged by build.sh: examples/sdk_*.py with the sdk_ prefix
# stripped (sdk_boot.py and sdk_main.py become minibot_boot / minibot_main),
# plus boot_stubs/boot.py and main.py. A same-named file uploaded to the
# device's filesystem takes precedence over every one of them: modules
# because '' precedes '.frozen' on sys.path, boot.py / main.py because the
# frozen stubs exec the uploaded file when it exists.
freeze("build/sdk")
