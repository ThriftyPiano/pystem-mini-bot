# filename: screen.py
# The robot's screen as four lines of text.
#
# On the StickS3 the LCD is used in landscape (the stick lies sideways on
# the robot, see config.LCD_ROTATION) with the firmware's 16x32 font: 15
# characters per line, four lines (4 x 32 px fills the 135 px height,
# the largest text that still gives four lines). Line 1 is the status line - the
# Bluetooth link keeps it at "XXXX: available" / "XXXX: connected" (XXXX
# is the robot's name suffix, so you connect to the right robot). Lines
# 2-4 belong to the program:
#
#   import screen
#   screen.show("Ready!", "Say a command")   # lines 2-4, centred
#
# show() also prints the lines, so the same program is readable on the
# Max V1 (no screen) and in the simulator, where this module is a no-op
# apart from the print.
LINES = 3          # program lines (2-4)
COLUMNS = 15

_lcd = None
_font = None
_status = ''
_lines = ()

try:
    from config import BOARD, LCD_ROTATION
    if BOARD == 'sticks3':
        import sticks3
        import vga1_16x32 as _font
        _lcd = sticks3.display(LCD_ROTATION)
except Exception as e:
    print("screen unavailable:", e)


def status(text):
    """Set line 1 (used by ble_repl for the Bluetooth state)."""
    global _status
    _status = str(text)
    _redraw()


def show(*lines):
    """Print the lines and draw them on lines 2-4 of the screen, centred."""
    global _lines
    print(*lines)
    _lines = tuple(str(s) for s in lines[:LINES])
    _redraw()


def clear():
    show()


def _redraw():
    lcd, font = _lcd, _font
    if lcd is None or font is None:
        return
    lcd.fill(0)
    row = lcd.height // 4
    _draw(lcd, font, _status, 0, 0x07FF)          # cyan status line
    for i, s in enumerate(_lines):
        _draw(lcd, font, s, row * (i + 1), 0xFFFF)


def _draw(lcd, font, s, y, color):
    s = s[:COLUMNS]
    x = max(0, (lcd.width - len(s) * font.WIDTH) // 2)
    lcd.text(font, s, x, y + (lcd.height // 4 - font.HEIGHT) // 2, color)
