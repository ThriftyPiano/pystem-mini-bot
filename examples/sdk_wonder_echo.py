# filename: wonder_echo.py
# Hiwonder WonderEcho voice module (I2C, wake word "Hello Hiwonder").
# Protocol reference: https://docs.hiwonder.com/projects/WonderEcho/

from machine import I2C, Pin
import time
from config import EXT_I2C

DEFAULT_ADDRESS = 0x34   # alternate is 0x33

REG_ADDRESS = 0x03    # write 1 byte: 0x33 or 0x34
REG_RESULT  = 0x64    # read 1 byte: last command id, clears on read
REG_BROADCAST = 0x6E  # write 2 bytes: [type, id]

TYPE_COMMAND   = 0x00
TYPE_BROADCAST = 0xFF

CMD_NONE     = 0x00
CMD_FORWARD  = 0x01
CMD_BACKWARD = 0x02
CMD_LEFT     = 0x03
CMD_RIGHT    = 0x04
CMD_STOP     = 0x09
CMD_DANCE    = 0x6C

class WonderEcho:
    def __init__(self, sda_pin=None, scl_pin=None, address=DEFAULT_ADDRESS, i2c=None):
        if i2c is None:
            if EXT_I2C is None:
                raise OSError("This board has no WonderEcho bus (config.EXT_I2C is None)")
            self.i2c = I2C(EXT_I2C['id'],
                           sda=Pin(EXT_I2C['sda'] if sda_pin is None else sda_pin),
                           scl=Pin(EXT_I2C['scl'] if scl_pin is None else scl_pin),
                           freq=EXT_I2C['freq'])
        else:
            self.i2c = i2c
        self.address = address

        if address not in self.i2c.scan():
            raise OSError("WonderEcho not found at I2C address {}. Check wiring.".format(hex(address)))
        print("WonderEcho found at I2C address: {}".format(hex(address)))

    def read_command(self):
        """Most recent voice command id (CMD_NONE if nothing new)."""
        try:
            return self.i2c.readfrom_mem(self.address, REG_RESULT, 1)[0]
        except OSError:
            return CMD_NONE

    def speak(self, type_byte, phrase_id):
        """Play a built-in phrase: TYPE_COMMAND or TYPE_BROADCAST, phrase id."""
        self.i2c.writeto_mem(self.address, REG_BROADCAST, bytes([type_byte, phrase_id]))

    def set_address(self, new_address):
        """Persistently change the module's I2C address (0x33 or 0x34)."""
        if new_address not in (0x33, 0x34):
            raise ValueError("WonderEcho address must be 0x33 or 0x34")
        self.i2c.writeto_mem(self.address, REG_ADDRESS, bytes([new_address]))
        self.address = new_address
        time.sleep_ms(150)


_default = None

def _get():
    global _default
    if _default is None:
        _default = WonderEcho()
    return _default

def read_command():
    """Most recent voice command id (CMD_NONE if nothing new)."""
    return _get().read_command()

def speak(type_byte, phrase_id):
    """Play a built-in phrase by [type_byte, phrase_id]."""
    _get().speak(type_byte, phrase_id)
