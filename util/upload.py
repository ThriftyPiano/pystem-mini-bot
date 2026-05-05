"""Upload a file to the robot using the hex-chunked protocol.

Mirrors what robot.js does in the browser: hex-encode the file, send it in
512-byte chunks via raw REPL, reconstruct on-device, and gc.collect() to keep
the ESP32 filesystem from fragmenting.

Usage:
    python3 -m util.upload examples/sdk_orientation.py orientation.py
"""
import binascii
import sys

from util.repl import RawREPL

CHUNK = 512


def upload_file(src_path, dest_name=None, repl=None):
    """Upload local `src_path` to on-device `dest_name`.

    If `repl` is None, opens its own RawREPL session.
    """
    if dest_name is None:
        dest_name = src_path.split("/")[-1]
    with open(src_path, "rb") as f:
        payload = f.read()
    hex_str = binascii.hexlify(payload).decode()

    lines = ["import binascii", "buf=b''"]
    for i in range(0, len(hex_str), CHUNK):
        lines.append("buf+=binascii.unhexlify(%r)" % hex_str[i:i + CHUNK])
    lines.append("f=open(%r,'wb'); f.write(buf); f.close()" % dest_name)
    lines.append("import gc; gc.collect()")
    lines.append("print('UPLOADED', len(buf), %r)" % dest_name)
    code = "\n".join(lines)

    if repl is None:
        with RawREPL() as r:
            return r.run(code, settle=2.0)
    return repl.run(code, settle=2.0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python3 -m util.upload <src> [dest_name]")
        sys.exit(1)
    src = sys.argv[1]
    dest = sys.argv[2] if len(sys.argv) > 2 else None
    print(upload_file(src, dest))
