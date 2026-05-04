# filename: wonder_echo.py
# Hiwonder WonderEcho voice interaction module (offline voice recognition + TTS broadcast).
# I2C slave at 0x34 by default. Wake word: "Hello Hiwonder".
# Protocol reference: https://docs.hiwonder.com/projects/WonderEcho/

from machine import I2C, Pin
import time

# Default I2C address (alternate is 0x33)
DEFAULT_ADDRESS = 0x34

# Registers
REG_ADDRESS = 0x03  # write 1 byte: 0x33 or 0x34 (then wait >=100ms before reusing bus)
REG_RESULT  = 0x64  # read  1 byte: last recognized command id (auto-clears to 0 after read)
REG_BROADCAST = 0x6E  # write 2 bytes: [type, id]

# Broadcast type bytes for REG_BROADCAST
TYPE_COMMAND   = 0x00  # command-word phrase set
TYPE_BROADCAST = 0xFF  # general broadcast phrase set

# Recognized command ids (returned from REG_RESULT)
CMD_NONE     = 0x00
CMD_FORWARD  = 0x01
CMD_BACKWARD = 0x02
CMD_LEFT     = 0x03
CMD_RIGHT    = 0x04
CMD_STOP     = 0x09

class WonderEcho:
    """
    Driver for the Hiwonder WonderEcho voice module.
    """
    def __init__(self, sda_pin=21, scl_pin=22, address=DEFAULT_ADDRESS, i2c=None):
        if i2c is None:
            # Match the freq used by sdk_orientation.py so the two modules
            # can share I2C bus 1 (sda=21, scl=22) without re-init churn.
            self.i2c = I2C(1, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)
        else:
            self.i2c = i2c
        self.address = address

        if address not in self.i2c.scan():
            raise OSError("WonderEcho not found at I2C address {}. Check wiring.".format(hex(address)))
        print("WonderEcho found at I2C address: {}".format(hex(address)))

    def read_command(self):
        """
        Return the most recent voice command id (0x00 if nothing new).
        Reading clears the register, so call this once per poll cycle.
        """
        try:
            return self.i2c.readfrom_mem(self.address, REG_RESULT, 1)[0]
        except OSError:
            return CMD_NONE

    def speak(self, type_byte, phrase_id):
        """
        Trigger the module to play a built-in phrase.
        type_byte: TYPE_COMMAND (0x00) or TYPE_BROADCAST (0xFF)
        phrase_id: 1-byte phrase id within that set
        """
        self.i2c.writeto_mem(self.address, REG_BROADCAST, bytes([type_byte, phrase_id]))

    def set_address(self, new_address):
        """
        Persistently change the module's I2C address (0x33 or 0x34).
        Blocks 150ms after the write so the bus is safe to reuse.
        """
        if new_address not in (0x33, 0x34):
            raise ValueError("WonderEcho address must be 0x33 or 0x34")
        self.i2c.writeto_mem(self.address, REG_ADDRESS, bytes([new_address]))
        self.address = new_address
        time.sleep_ms(150)


# Module-level singleton convenience API (mirrors style of motor.py / motor_pair.py)
_default = None

def _get():
    global _default
    if _default is None:
        _default = WonderEcho()
    return _default

def read_command():
    """Return the most recent voice command id (0x00 if nothing new)."""
    return _get().read_command()

def speak(type_byte, phrase_id):
    """Trigger a built-in phrase by [type_byte, phrase_id]."""
    _get().speak(type_byte, phrase_id)
