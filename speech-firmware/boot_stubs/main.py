# Frozen main.py: runs an uploaded main.py when there is one, otherwise the
# built-in default program (examples/sdk_main.py).
import os
try:
    os.stat('main.py')
except OSError:
    import minibot_main
else:
    exec(compile(open('main.py').read(), 'main.py', 'exec'), {'__name__': '__main__'})
