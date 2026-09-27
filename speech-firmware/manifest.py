# Frozen modules for the StickS3 speech-commands firmware: board support
# for all on-board hardware (LCD, mic, speaker, IMU, power chip, buttons)
# and the robot SDK.
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
# The robot SDK (examples/sdk_*.py), staged by build.sh under build/sdk
# with the sdk_ prefix stripped, so a freshly flashed stick imports motor,
# motor_pair, screen, ... with nothing uploaded. A file of the same name
# on the device's filesystem takes precedence ('' comes before '.frozen'
# on sys.path), so uploading a newer SDK file from the IDE still works.
# boot.py is deliberately not frozen: boot/main scripts are looked up in
# the frozen set first, so a frozen boot.py could not be overridden.
freeze("build/sdk")
