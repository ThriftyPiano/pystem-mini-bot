"""One-shot MPU-6050 sanity check: WHO_AM_I, temperature, 5 raw samples.

Usage:
    python3 -m util.mpu_health
"""
from util.repl import RawREPL

CODE = r"""
from machine import I2C, Pin
import time
i2c = I2C(1, sda=Pin(21), scl=Pin(22), freq=400000)
print('scan:', [hex(d) for d in i2c.scan()])
ADDR = 0x68
i2c.writeto(ADDR, bytes([0x6B, 0]))
time.sleep_ms(50)
who = i2c.readfrom_mem(ADDR, 0x75, 1)[0]
print('WHO_AM_I:', hex(who))

def s16(b, i):
    v = (b[i]<<8)|b[i+1]
    return v-65536 if v>32767 else v
def rd():
    a = i2c.readfrom_mem(ADDR, 0x3B, 6)
    g = i2c.readfrom_mem(ADDR, 0x43, 6)
    return (s16(a,0),s16(a,2),s16(a,4),s16(g,0),s16(g,2),s16(g,4))

t_raw = i2c.readfrom_mem(ADDR, 0x41, 2)
t = ((t_raw[0]<<8)|t_raw[1])
if t>32767: t-=65536
print('temp_c:', round(t/340.0 + 36.53, 2))

print('--- 5 samples (raw) ---')
for _ in range(5):
    print(rd())
    time.sleep_ms(100)

ax,ay,az,gx,gy,gz = rd()
print('ax_g=%.2f ay_g=%.2f az_g=%.2f' % (ax/16384.0, ay/16384.0, az/16384.0))
print('gx_dps=%.2f gy_dps=%.2f gz_dps=%.2f' % (gx/131.0, gy/131.0, gz/131.0))
"""

if __name__ == "__main__":
    with RawREPL() as r:
        print(r.run(CODE, settle=2.5))
