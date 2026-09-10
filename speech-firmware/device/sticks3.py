# M5StickS3 board support: one-stop access to the on-board hardware.
#
#   import sticks3
#   lcd = sticks3.display()        # st7789py driver, 135x240
#   imu = sticks3.imu()            # BMI270: .acceleration, .gyro
#   mic = sticks3.microphone()     # machine.I2S RX, 16 kHz 16-bit mono
#   spk = sticks3.speaker()        # machine.I2S TX, 16 kHz 16-bit mono
#   btn_a, btn_b = sticks3.buttons()
#
# Pin map:
#   LCD (ST7789):  MOSI=39 SCK=40 DC=45 CS=41 RST=21 BL=38
#   ES8311 codec:  BCLK=17 WS=15 mic-data=16 spk-data=14 (I2C 0x18)
#   BMI270 IMU:    I2C 0x68
#   M5PM1 power:   I2C 0x6E (gates LCD power and speaker amp)
#   I2C bus:       SDA=47 SCL=48 (codec + IMU + PM1)
#   Buttons:       A=11 B=12 (active low)
#   Grove:         13
from machine import I2C, I2S, Pin, SPI, PWM

_i2c = None
_pm1 = None
_codec = None
_i2s = None


def i2c():
    global _i2c
    if _i2c is None:
        # 100 kHz: the M5PM1 power chip NAKs at 400 kHz on this bus.
        _i2c = I2C(0, scl=Pin(48), sda=Pin(47), freq=100000)
    return _i2c


def pm1():
    global _pm1
    if _pm1 is None:
        import m5pm1
        _pm1 = m5pm1.M5PM1(i2c())
    return _pm1


def display(rotation=0):
    """Power up the LCD and return an st7789py.ST7789 driver."""
    import time
    import st7789py
    pm1().lcd_power(True)
    time.sleep_ms(100)
    spi = SPI(2, baudrate=40000000, polarity=0, phase=0,
        sck=Pin(40), mosi=Pin(39), miso=None)
    lcd = st7789py.ST7789(spi, 135, 240,
        reset=Pin(21, Pin.OUT),
        dc=Pin(45, Pin.OUT),
        cs=Pin(41, Pin.OUT),
        backlight=Pin(38, Pin.OUT),
        rotation=rotation)
    return lcd


def backlight_pwm(duty=512):
    """Optional dimmable backlight (replaces the on/off backlight Pin)."""
    return PWM(Pin(38), freq=1000, duty=duty)


def imu():
    """Return a BMI270 driver (.acceleration in m/s^2, .gyro in rad/s)."""
    import time
    import bmi270
    dev = bmi270.BMI270(i2c())
    # Right after the config-file load the first range writes can be lost
    # (the chip silently stays at its power-on defaults), so re-assert
    # them with read-back until they stick.
    for _ in range(10):
        dev.acceleration_range = bmi270.ACCEL_RANGE_2G
        dev.gyro_range = bmi270.GYRO_RANGE_250
        time.sleep_ms(10)
        if (i2c().readfrom_mem(0x68, 0x41, 1)[0] & 0x03) == bmi270.ACCEL_RANGE_2G \
                and (i2c().readfrom_mem(0x68, 0x43, 1)[0] & 0x07) == bmi270.GYRO_RANGE_250:
            break
    return dev


def codec():
    global _codec
    if _codec is None:
        import es8311
        _codec = es8311.ES8311(i2c())
        _codec.init_mic()
    return _codec


def _audio(mode, sd_pin, buf):
    # The codec shares one BCLK/WS bus; only one direction can be active
    # at a time with machine.I2S, so tear down any previous instance.
    global _i2s
    if _i2s is not None:
        _i2s.deinit()
    codec()
    _i2s = I2S(0, sck=Pin(17), ws=Pin(15), sd=Pin(sd_pin), mode=mode,
        bits=16, format=I2S.MONO, rate=16000, ibuf=buf)
    return _i2s


def microphone(ibuf=32768):
    """16 kHz 16-bit mono I2S RX stream from the on-board mic.

    The I2S ring stores raw 32-bit stereo frames, so effective mono-16
    backlog is ibuf/4: 32 KB buffers ~256 ms while the CPU is busy.
    """
    return _audio(I2S.RX, 16, ibuf)


def speaker(ibuf=8192, volume=0xBF):
    """16 kHz 16-bit mono I2S TX stream to the on-board speaker."""
    s = _audio(I2S.TX, 14, ibuf)
    codec().enable_dac(volume)
    pm1().speaker_enable(True)
    return s


def speaker_off():
    global _i2s
    pm1().speaker_enable(False)
    if _i2s is not None:
        _i2s.deinit()
        _i2s = None


def buttons():
    """(button_a, button_b) as input Pins; pressed reads 0."""
    return Pin(11, Pin.IN, Pin.PULL_UP), Pin(12, Pin.IN, Pin.PULL_UP)
