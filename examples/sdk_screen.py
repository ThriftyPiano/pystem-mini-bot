# filename: screen.py
# The robot's screen as four lines of text (StickS3 LCD, 16x32 font, 15
# characters per line). Line 1 is the status line used by ble_repl;
# lines 2-4 belong to the program via show(). show() also prints, and
# without a screen it only prints.
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
    """Set line 1."""
    global _status
    _status = str(text)
    _redraw()


def show(*lines):
    """Print the lines and draw them centred on lines 2-4."""
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
    _draw(lcd, font, _status, 0, 0x07FF)
    for i, s in enumerate(_lines):
        _draw(lcd, font, s, row * (i + 1), 0xFFFF)


def _draw(lcd, font, s, y, color):
    s = s[:COLUMNS]
    x = max(0, (lcd.width - len(s) * font.WIDTH) // 2)
    lcd.text(font, s, x, y + (lcd.height // 4 - font.HEIGHT) // 2, color)
