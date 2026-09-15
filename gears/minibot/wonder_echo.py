# filename: wonder_echo.py  (GEARS simulator build)
# Same command ids and read_command()/speak() API as examples/sdk_wonder_echo.py.
# There is no microphone: commands come from the "Voice command" box on the
# simulator page (queued by minibot_sim), so voice_drive.py runs unchanged.
import minibot_sim

DEFAULT_ADDRESS = 0x34
TYPE_COMMAND   = 0x00
TYPE_BROADCAST = 0xFF

CMD_NONE     = 0x00
CMD_FORWARD  = 0x01
CMD_BACKWARD = 0x02
CMD_LEFT     = 0x03
CMD_RIGHT    = 0x04
CMD_STOP     = 0x09
CMD_DANCE    = 0x6C

# What the page's text box accepts (case-insensitive).
COMMAND_WORDS = {
    'forward': CMD_FORWARD, 'go': CMD_FORWARD,
    'backward': CMD_BACKWARD, 'back': CMD_BACKWARD,
    'left': CMD_LEFT,
    'right': CMD_RIGHT,
    'stop': CMD_STOP,
    'dance': CMD_DANCE,
}

class WonderEcho:
    def __init__(self, sda_pin=None, scl_pin=None, address=DEFAULT_ADDRESS, i2c=None):
        self.address = address
        print("WonderEcho (simulated): type a command in the Voice box")

    def read_command(self):
        word = minibot_sim.voice_command()
        if not word:
            return CMD_NONE
        return COMMAND_WORDS.get(word.strip().lower(), CMD_NONE)

    def speak(self, type_byte, phrase_id):
        print("WonderEcho says: [type %d, phrase %d]" % (type_byte, phrase_id))

    def set_address(self, new_address):
        if new_address not in (0x33, 0x34):
            raise ValueError("WonderEcho address must be 0x33 or 0x34")
        self.address = new_address

_default = None

def _get():
    global _default
    if _default is None:
        _default = WonderEcho()
    return _default

def read_command():
    return _get().read_command()

def speak(type_byte, phrase_id):
    _get().speak(type_byte, phrase_id)
