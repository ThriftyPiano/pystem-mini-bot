# Driver for the M5PM1 power-management chip on the M5StickS3 (I2C 0x6E).
#
# The PM1's GPIO expander gates two rails/controls used here:
#   - PM1 GPIO2: LCD power (must be on before the ST7789 responds)
#   - PM1 GPIO3: speaker amplifier (AW8737) enable

_ADDR = 0x6E

_REG_I2C_CFG = 0x09
_REG_GPIO_MODE = 0x10   # bit=1: output
_REG_GPIO_OUT = 0x11    # output level
_REG_GPIO_PULL = 0x13   # bit=0: push-pull
_REG_GPIO_FUNC = 0x16   # per-pin function select bits


class M5PM1:
    def __init__(self, i2c, addr=_ADDR):
        self.i2c = i2c
        self.addr = addr
        # Disable I2C idle sleep so the PM1 keeps responding; it is
        # always-on powered so this may hold a stale value from a
        # previous boot.
        self._w(_REG_I2C_CFG, 0x00)

    def _r(self, reg):
        return self.i2c.readfrom_mem(self.addr, reg, 1)[0]

    def _w(self, reg, val):
        self.i2c.writeto_mem(self.addr, reg, bytes([val & 0xFF]))

    def _update(self, reg, mask, on):
        v = self._r(reg)
        v = (v | mask) if on else (v & ~mask)
        self._w(reg, v)

    def _gpio_out(self, pin, on, func_mask):
        self._update(_REG_GPIO_FUNC, func_mask, False)  # gpio function
        self._update(_REG_GPIO_MODE, 1 << pin, True)    # output mode
        self._update(_REG_GPIO_PULL, 1 << pin, False)   # push-pull
        self._update(_REG_GPIO_OUT, 1 << pin, on)

    def lcd_power(self, on=True):
        self._gpio_out(2, on, 1 << 2)

    def speaker_enable(self, on=True):
        self._gpio_out(3, on, 0b11000000)
