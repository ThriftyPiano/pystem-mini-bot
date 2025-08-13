# MicroPython time module stub
from typing import Optional, Tuple, Union

def sleep(seconds: Union[int, float]) -> None:
    """Sleep for the given number of seconds"""
    ...

def sleep_ms(ms: int) -> None:
    """Sleep for the given number of milliseconds"""
    ...

def sleep_us(us: int) -> None:
    """Sleep for the given number of microseconds"""
    ...

def ticks_ms() -> int:
    """Return millisecond counter with arbitrary reference point"""
    ...

def ticks_us() -> int:
    """Return microsecond counter with arbitrary reference point"""
    ...

def ticks_cpu() -> int:
    """Return CPU ticks counter"""
    ...

def ticks_add(ticks: int, delta: int) -> int:
    """Add delta to ticks value"""
    ...

def ticks_diff(ticks1: int, ticks2: int) -> int:
    """Compute difference between ticks values"""
    ...

def time() -> int:
    """Return current time in seconds since epoch"""
    ...

def gmtime(secs: Optional[int] = None) -> Tuple[int, int, int, int, int, int, int, int]:
    """Convert seconds since epoch to UTC time tuple"""
    ...

def localtime(secs: Optional[int] = None) -> Tuple[int, int, int, int, int, int, int, int]:
    """Convert seconds since epoch to local time tuple"""
    ...

def mktime(t: Tuple[int, int, int, int, int, int, int, int]) -> int:
    """Convert time tuple to seconds since epoch"""
    ...
