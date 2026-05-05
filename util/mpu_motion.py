"""Sample the MPU-6050 for 10s and summarize detected motion.

Usage:
    python3 -m util.mpu_motion
"""
import sys
from util.repl import RawREPL

CODE = r"""
from machine import I2C, Pin
import time, math
i2c = I2C(1, sda=Pin(21), scl=Pin(22), freq=400000)
ADDR = 0x68
i2c.writeto(ADDR, bytes([0x6B, 0])); time.sleep_ms(50)

def s16(b, i):
    v = (b[i]<<8)|b[i+1]
    return v-65536 if v>32767 else v
def read():
    a = i2c.readfrom_mem(ADDR, 0x3B, 6)
    g = i2c.readfrom_mem(ADDR, 0x43, 6)
    return (s16(a,0),s16(a,2),s16(a,4),s16(g,0),s16(g,2),s16(g,4))

# Calibrate gyro bias for ~0.5s
gx_b=gy_b=gz_b=0; N=25
for _ in range(N):
    _,_,_,gx,gy,gz = read()
    gx_b+=gx; gy_b+=gy; gz_b+=gz
    time.sleep_ms(20)
gx_b/=N; gy_b/=N; gz_b/=N
for n in (3,2,1):
    print('starting in', n); time.sleep(1)
print('GO')

t0 = time.ticks_ms(); last = t0
yaw=pitch=roll=0.0
max_accel = 0.0
peak_gx=peak_gy=peak_gz=0.0
while time.ticks_diff(time.ticks_ms(), t0) < 10000:
    ax,ay,az,gx,gy,gz = read()
    now = time.ticks_ms()
    dt = time.ticks_diff(now, last)/1000.0
    last = now
    gxd = (gx-gx_b)/131.0
    gyd = (gy-gy_b)/131.0
    gzd = (gz-gz_b)/131.0
    roll += gxd*dt; pitch += gyd*dt; yaw += gzd*dt
    if abs(gxd)>abs(peak_gx): peak_gx=gxd
    if abs(gyd)>abs(peak_gy): peak_gy=gyd
    if abs(gzd)>abs(peak_gz): peak_gz=gzd
    mag = math.sqrt((ax/16384.0)**2 + (ay/16384.0)**2 + (az/16384.0)**2)
    dev = abs(mag-1.0)
    if dev>max_accel: max_accel=dev
    time.sleep_ms(20)

print('DONE')
print('roll_deg=%.1f pitch_deg=%.1f yaw_deg=%.1f' % (roll,pitch,yaw))
print('peak_gyro_dps gx=%.1f gy=%.1f gz=%.1f' % (peak_gx,peak_gy,peak_gz))
print('peak_linear_accel_g=%.2f' % max_accel)
"""

if __name__ == "__main__":
    print("--- 10s motion capture; move the robot when you see GO ---", flush=True)
    with RawREPL() as r:
        r.run(CODE, stream=True, timeout=20, end_marker=b"peak_linear_accel_g")
