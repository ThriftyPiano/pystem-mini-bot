# Frozen boot.py: MicroPython runs the frozen copy in preference to one on
# the filesystem, so this stub hands over to an uploaded boot.py when there
# is one and runs the built-in default (examples/sdk_boot.py) otherwise.
import os
try:
    os.stat('boot.py')
except OSError:
    import minibot_boot
else:
    exec(compile(open('boot.py').read(), 'boot.py', 'exec'), {'__name__': '__main__'})
