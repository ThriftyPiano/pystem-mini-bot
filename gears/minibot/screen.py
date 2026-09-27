# filename: screen.py  (GEARS simulator build)
# Same API as examples/sdk_screen.py. The virtual robot has no screen, so
# show() just prints, like it does on the Max V1.
LINES = 3
COLUMNS = 30

def status(text):
    pass

def show(*lines):
    print(*lines)

def clear():
    pass
