"""Raw-REPL helper for the AceBott ESP32 over USB serial.

Handles the two annoying parts of talking to a running robot:
  1. boot.py blocks on the start button, so we send Ctrl-C twice to break out.
  2. raw REPL framing (Ctrl-A enter, Ctrl-D execute, Ctrl-B exit).

Usage:
    from util.repl import RawREPL
    with RawREPL() as r:
        print(r.run("print(1+1)"))
"""
import os
import sys
import time
import serial

DEFAULT_PORT = os.environ.get("ROBOT_PORT", "/dev/cu.usbserial-14110")
DEFAULT_BAUD = 115200


class RawREPL:
    def __init__(self, port=DEFAULT_PORT, baud=DEFAULT_BAUD):
        self.port = port
        self.baud = baud
        self.s = None

    def __enter__(self):
        self.s = serial.Serial(self.port, self.baud, timeout=0.2)
        time.sleep(0.3)
        # Break out of the boot.py button-wait loop
        self.s.write(b"\x03\x03")
        time.sleep(0.2)
        self._drain()
        # Enter raw REPL
        self.s.write(b"\x01")
        time.sleep(0.3)
        self._drain()
        return self

    def __exit__(self, *exc):
        try:
            self.s.write(b"\x02")  # exit raw REPL
        finally:
            self.s.close()

    def _drain(self):
        return self.s.read(self.s.in_waiting or 1)

    def run(self, code, settle=1.5, stream=False, timeout=20.0, end_marker=None):
        """Send `code` to raw REPL and return collected stdout.

        - settle: how long to wait for one-shot output before returning.
        - stream: if True, mirror output to stdout as it arrives.
        - timeout: max seconds to wait when streaming.
        - end_marker: bytes that, once seen, ends the read early (streaming mode).
        """
        self.s.write(code.encode() + b"\x04")
        if not stream:
            time.sleep(settle)
            return self._drain().decode(errors="replace")

        deadline = time.time() + timeout
        buf = b""
        while time.time() < deadline:
            chunk = self.s.read(self.s.in_waiting or 1)
            if chunk:
                buf += chunk
                if stream:
                    sys.stdout.write(chunk.decode(errors="replace"))
                    sys.stdout.flush()
                if end_marker and end_marker in buf:
                    time.sleep(0.2)
                    tail = self.s.read(self.s.in_waiting or 1)
                    if tail:
                        buf += tail
                        if stream:
                            sys.stdout.write(tail.decode(errors="replace"))
                            sys.stdout.flush()
                    break
            else:
                time.sleep(0.05)
        return buf.decode(errors="replace")

    def soft_reset(self):
        """Soft-reset the device and re-enter raw REPL with a clean module cache."""
        self.s.write(b"\x02")  # exit raw -> friendly REPL
        time.sleep(0.3)
        self.s.write(b"\x04")  # Ctrl-D in friendly = soft reset
        time.sleep(1.5)
        self._drain()
        self.s.write(b"\x03\x03")  # break out of boot button-wait
        time.sleep(0.2)
        self._drain()
        self.s.write(b"\x01")  # back into raw REPL
        time.sleep(0.3)
        self._drain()
