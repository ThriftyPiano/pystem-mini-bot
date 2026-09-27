# filename: ble_repl.py
# The REPL over Bluetooth LE (Nordic UART Service) so the IDE can connect
# without a cable. Started by boot.py (config.BLE_REPL); interrupt-driven,
# no thread. Advertises as "Mini Bot XXXX" (XXXX from the address).
#
#   ble_repl.start()          # returns the advertised name
#   ble_repl.connected()      # True while the IDE is attached
import io
import os
import sys
import time
import select
import machine
import bluetooth

_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GATTS_WRITE = 3
_IRQ_MTU_EXCHANGED = 21
_FLAG_READ = 0x0002
_FLAG_WRITE_NO_RESPONSE = 0x0004
_FLAG_WRITE = 0x0008
_FLAG_NOTIFY = 0x0010

_UART_UUID = bluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
_TX_UUID = bluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')   # robot -> IDE (notify)
_RX_UUID = bluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E')   # IDE -> robot (write)
_NAME = 'Mini Bot'
# Output is batched into MTU-sized notifications; one notification per
# echoed character floods the radio.
_FLUSH_MS = 20
_TX_TIMER_ID = 3
_RX_TIMER_ID = 2
# Input is paced: os.dupterm_notify() drops whatever does not fit in the
# console's 260-byte ring buffer, so pushes are capped and only made once
# the ring is empty.
_PUMP_MS = 2
_PUMP_BYTES = 250

_repl = None


class BLEREPL(io.IOBase):
    def __init__(self, ble, name):
        self._ble = ble
        self._name = name
        self._conn = None
        self._mtu = 23
        # Buffers are extended and trimmed in place, never rebound: the IRQ
        # handler can run between any two bytecodes of the reader.
        self._rxbuf = bytearray()
        self._rxpos = 0
        self._budget = 0
        self._txbuf = bytearray()
        self._flush_pending = False
        self._timer = machine.Timer(_TX_TIMER_ID)
        self._rx_timer = machine.Timer(_RX_TIMER_ID)
        self._pumping = False
        self._stdin_poll = select.poll()
        self._stdin_poll.register(sys.stdin, select.POLLIN)
        ble.config(gap_name=name, mtu=517)
        ble.irq(self._irq)
        ((self._tx, self._rx),) = ble.gatts_register_services((
            (_UART_UUID, (
                (_TX_UUID, _FLAG_NOTIFY | _FLAG_READ),
                (_RX_UUID, _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE),
            )),
        ))
        # Append mode, large enough for a whole upload piece (~3.2 KB) to
        # land before the IRQ drains it.
        ble.gatts_set_buffer(self._rx, 16384, True)
        self._advertise()

    def _advertise(self):
        adv = b'\x02\x01\x06' + b'\x11\x07' + bytes(_UART_UUID)
        name = self._name.encode()
        resp = bytes([len(name) + 1, 0x09]) + name
        self._ble.gap_advertise(100000, adv_data=adv, resp_data=resp)

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            self._conn = data[0]
            self._mtu = 23
            self._txbuf[:] = b''
            _show_status(self._name, 'connected')
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self._conn = None
            self._advertise()
            _show_status(self._name, 'available')
        elif event == _IRQ_MTU_EXCHANGED:
            self._mtu = data[1]
        elif event == _IRQ_GATTS_WRITE and data[1] == self._rx:
            self._rxbuf.extend(self._ble.gatts_read(self._rx))
            self._pump()
            if not self._pumping and len(self._rxbuf) > self._rxpos:
                self._pumping = True
                self._rx_timer.init(period=_PUMP_MS, mode=machine.Timer.PERIODIC,
                                    callback=self._pump)

    def _pump(self, _timer=None):
        if len(self._rxbuf) <= self._rxpos:
            if self._pumping:
                self._pumping = False
                self._rx_timer.deinit()
            return
        if self._stdin_poll.poll(0):
            return
        self._budget = _PUMP_BYTES
        os.dupterm_notify(None)  # type: ignore[attr-defined]

    # ---- stream interface used by os.dupterm

    def read(self, sz=None):
        buf = self._rxbuf
        pos = self._rxpos
        avail = min(len(buf) - pos, self._budget)
        if avail <= 0:
            return None
        n = avail if sz is None else min(sz, avail)
        self._budget -= n
        data = bytes(buf[pos:pos + n])
        pos += n
        if pos >= len(buf):
            buf[:pos] = b''   # slice assignment; MicroPython bytearray has no del
            pos = 0
        self._rxpos = pos
        return data

    def readinto(self, buf):
        data = self.read(len(buf))
        if not data:
            return None
        buf[:len(data)] = data
        return len(data)

    def ioctl(self, op, arg):
        # Never report readable: sys.stdin's poll must reflect the ring
        # buffer alone (see _pump).
        return 0

    def write(self, buf):
        # Must never raise: an exception here silently detaches the stream.
        if self._conn is None:
            return len(buf)
        self._txbuf.extend(buf)
        if not self._flush_pending:
            self._flush_pending = True
            self._timer.init(period=_FLUSH_MS, mode=machine.Timer.ONE_SHOT,
                             callback=self._flush)
        return len(buf)

    def _flush(self, _timer=None):
        data = bytes(self._txbuf)
        self._txbuf[:len(data)] = b''
        self._flush_pending = False
        if self._conn is None or not data:
            return
        step = max(self._mtu - 3, 20)
        mv = memoryview(data)
        for i in range(0, len(data), step):
            chunk = mv[i:i + step]
            # ENOMEM means the radio's queue is full: retry briefly, then drop.
            for _ in range(40):
                try:
                    self._ble.gatts_notify(self._conn, self._tx, chunk)
                    break
                except OSError:
                    time.sleep_ms(5)
            else:
                return


def start():
    """Bring up Bluetooth, mirror the REPL onto it, return the advertised name."""
    global _repl
    if _repl is not None:
        return _repl._name
    ble = bluetooth.BLE()
    ble.active(True)
    mac = ble.config('mac')[1]
    name = '%s %02X%02X' % (_NAME, mac[-2], mac[-1])
    _repl = BLEREPL(ble, name)
    os.dupterm(_repl, 0)  # type: ignore[attr-defined]
    print('Bluetooth: IDE can connect to "%s"' % name)
    _show_status(name, 'available')
    return name


def _show_status(name, state):
    try:
        import screen
        screen.status('%s: %s' % (name[-4:], state))
    except Exception:
        pass


def stop():
    global _repl
    if _repl is None:
        return
    os.dupterm(None, 0)  # type: ignore[attr-defined]
    _repl._timer.deinit()
    _repl._rx_timer.deinit()
    _repl._ble.active(False)
    _repl = None


def name():
    return _repl._name if _repl else None


def connected():
    return _repl is not None and _repl._conn is not None
