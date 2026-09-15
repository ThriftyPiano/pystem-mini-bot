# filename: machine.py  (GEARS simulator build)
# Just enough of MicroPython's `machine` for beginner programs to run in
# the browser. Pins are virtual: writes are shown in the simulator console
# and on the page's LED indicator (via minibot_sim); reads return the last
# written value (0 for inputs). PWM / ADC / I2C are inert placeholders so
# that importing them does not fail; Timer callbacks cannot run because
# Skulpt has no threads, so Timer.init() warns and does nothing.
import minibot_sim

_pins = {}

class Pin:
    IN = 'IN'
    OUT = 'OUT'
    OPEN_DRAIN = 'OPEN_DRAIN'
    PULL_UP = 'PULL_UP'
    PULL_DOWN = 'PULL_DOWN'
    IRQ_RISING = 1
    IRQ_FALLING = 2

    def __init__(self, id, mode=None, pull=None, value=None):
        self.id = id
        self.mode = mode
        self.pull = pull
        self._value = 1 if pull == Pin.PULL_UP else 0
        _pins[id] = self
        if value is not None:
            self.value(value)

    def value(self, v=None):
        if v is None:
            return self._value
        v = 1 if v else 0
        if v != self._value:
            self._value = v
            minibot_sim.pin_changed(self.id, v)

    def on(self):
        self.value(1)

    def off(self):
        self.value(0)

    def toggle(self):
        self.value(0 if self._value else 1)

    def init(self, mode=None, pull=None, value=None):
        if mode is not None:
            self.mode = mode
        if pull is not None:
            self.pull = pull
        if value is not None:
            self.value(value)

    def irq(self, handler=None, trigger=None):
        # Nothing can raise an interrupt in the simulator; accepted so that
        # programs written for the robot still start.
        self.handler = handler

    def __call__(self, v=None):
        return self.value(v)


class PWM:
    def __init__(self, pin, freq=50, duty=None, duty_u16=None, duty_ns=None):
        self.pin = pin
        self._freq = freq
        self._duty = 0

    def freq(self, f=None):
        if f is None:
            return self._freq
        self._freq = f

    def duty(self, d=None):
        if d is None:
            return self._duty
        self._duty = d

    def duty_u16(self, d=None):
        return self.duty(d)

    def duty_ns(self, d=None):
        return self.duty(d)

    def deinit(self):
        pass


class ADC:
    ATTN_0DB = 0
    ATTN_2_5DB = 1
    ATTN_6DB = 2
    ATTN_11DB = 3
    WIDTH_12BIT = 12

    def __init__(self, pin):
        self.pin = pin

    def atten(self, a):
        pass

    def width(self, w):
        pass

    def read(self):
        return 0

    def read_u16(self):
        return 0


class I2C:
    def __init__(self, id=0, scl=None, sda=None, freq=400000):
        self.id = id

    def scan(self):
        return []

    def readfrom_mem(self, addr, reg, n):
        raise OSError("No I2C devices in the simulator")

    def writeto_mem(self, addr, reg, data):
        raise OSError("No I2C devices in the simulator")

    def writeto(self, addr, data):
        raise OSError("No I2C devices in the simulator")


class Timer:
    PERIODIC = 1
    ONE_SHOT = 0

    def __init__(self, id=-1):
        self.id = id

    def init(self, period=None, mode=None, callback=None):
        print("machine.Timer: callbacks are not supported in the simulator")

    def deinit(self):
        pass


def freq(hz=None):
    return 240000000

def reset():
    raise SystemExit("machine.reset()")

def soft_reset():
    raise SystemExit("machine.soft_reset()")

def unique_id():
    return b'simbot'

def idle():
    pass
