# filename: motor.py
# SPIKE Prime Compatible Motor Module for ESP32
# FIXES: Hard Stop, Proportional Control, Debouncing, Debug Prints

from machine import Pin, PWM, Timer
import time
import math
from config import MOTOR_PINS, MOTOR_CONFIG

# Port constants
PORT_A = 'A'
PORT_B = 'B'
PORT_C = 'C'
PORT_D = 'D'
PORT_E = 'E'
PORT_F = 'F'

# Motor direction constants
CLOCKWISE = 1
COUNTERCLOCKWISE = -1
SHORTEST_PATH = 0
LONGEST_PATH = 1

class Motor:
    """ESP32 Motor controller that mimics SPIKE Prime motor interface"""
    
    def __init__(self, port, servo_pin, encoder_pin):
        self.port = port
        self.servo_pin = servo_pin
        self.encoder_pin = encoder_pin
        
        # Setup servo PWM (50Hz)
        self.pwm = PWM(Pin(servo_pin))
        self.pwm.freq(50)
        
        # Setup encoder pin with Pull-Up (Stabilizes signal)
        self.encoder = Pin(encoder_pin, Pin.IN, Pin.PULL_UP)
        
        # Encoder state
        self.position = 0
        self.pulse_count = 0
        self.last_pulse_time = time.ticks_ms()
        self.velocity = 0
        self.direction = 1 
        
        # Motor state
        self.target_position = 0
        self.target_velocity = MOTOR_CONFIG['default_speed_dps']
        self.is_running = False
        self.current_speed = 0
        self.print_ticks = False  # Switch for debug printing
        # Closed-loop velocity control state
        self.control_mode = 'idle'   # 'idle' | 'velocity' | 'position'
        self.velocity_integral = 0.0
        self.measured_velocity = 0.0       # smoothed dps (used by controller)
        self.last_control_position = 0.0
        self.last_control_time = 0
        
        # Setup encoder interrupt
        self.encoder.irq(trigger=Pin.IRQ_RISING, handler=self._encoder_callback)
        
        # Timer for position control
        timer_id = ord(port) - ord('A')
        if timer_id < 0 or timer_id > 3:
            raise ValueError("Only ports A-D are supported.")
        self.control_timer = Timer(timer_id)
        
        # Stop motor initially
        self._set_servo_speed(0)
    
    def _encoder_callback(self, pin):
        """Handle encoder interrupts with DEBOUNCING"""
        current_time = time.ticks_ms()
        
        # 1. Debounce Filter: Ignore clicks faster than 5ms
        if time.ticks_diff(current_time, self.last_pulse_time) < 5:
            return
            
        # 2. Count pulses
        self.pulse_count += 1
        
        # 3. Optional Debug Print
        if self.print_ticks:
            print(f"TICK! Total: {self.pulse_count}")

        # 4. Update Position
        degrees_per_pulse = 360 / MOTOR_CONFIG['pulses_per_revolution']
        self.position += self.direction * degrees_per_pulse
        
        # 5. Calculate Velocity
        dt = time.ticks_diff(current_time, self.last_pulse_time) / 1000.0
        if dt > 0:
            self.velocity = degrees_per_pulse / dt * self.direction
        
        self.last_pulse_time = current_time
    
    def _set_servo_speed(self, speed):
        """Set servo speed. 0 = HARD STOP (Cut Power)"""
        
        # --- THE FIX: HARD STOP ---
        if speed == 0:
            self.direction = 0
            self.pwm.duty_u16(0)  # CUT SIGNAL COMPLETELY
            return
        # --------------------------

        self.pwm.freq(50)
        # Map speed to pulse width (1000-2000us)
        pulse_width = int(1500 + (speed * 5))
        pulse_width = max(1000, min(2000, pulse_width))
        
        # Track direction
        self.direction = 1 if speed > 0 else -1
        
        # Convert to duty cycle
        duty = int((pulse_width / 20000) * 1023)
        self.pwm.duty_u16(int(duty * 64))
        self.current_speed = speed
    
    def _position_control(self, timer):
        """Loop to check if we reached the target"""
        if not self.is_running:
            self._set_servo_speed(0)
            self.control_timer.deinit()
            return
            
        # 1. Take a Snapshot (Thread Safety)
        current_pos_snapshot = self.position
        error = self.target_position - current_pos_snapshot
        
        # Debug Print to see what is happening
        if self.print_ticks:
            print(f"Tgt: {self.target_position:.1f} | Cur: {current_pos_snapshot:.1f} | Err: {error:.1f}")
        
        # 2. Check Arrival (Tolerance check)
        # If within 1 tick (approx 20 deg), STOP.
        if abs(error) <= 30:  # Increased tolerance slightly to catch fast movements
            print(">>> TARGET REACHED! STOPPING. <<<")
            self.is_running = False
            self.print_ticks = False
            self._set_servo_speed(0)  # This triggers the Hard Stop
            self.control_timer.deinit()
            return
        
        # 3. Proportional Control (Slow down closer to target)
        kp = 0.8  # Aggressiveness
        speed_command = error * kp
        
        # 4. Limit Speed
        max_user_speed = abs(self.target_velocity / (MOTOR_CONFIG['max_speed_dps'] / 100))
        if speed_command > 0:
            final_speed = min(speed_command, max_user_speed)
        else:
            final_speed = max(speed_command, -max_user_speed)
            
        # 5. Minimum Power (Prevent Stalling)
        if abs(final_speed) < 15:
            final_speed = 15 if final_speed > 0 else -15
            
        self._set_servo_speed(final_speed)

    def _velocity_control(self, timer):
        """Closed-loop velocity controller. Drives PWM so encoder velocity
        tracks self.target_velocity. Uses feed-forward from the open-loop
        speed map plus a PI correction off encoder feedback."""
        if not self.is_running:
            self._set_servo_speed(0)
            self.control_timer.deinit()
            return

        target = self.target_velocity
        if target == 0:
            # Hard stop on zero target — no integral wind-down.
            self._set_servo_speed(0)
            self.velocity_integral = 0.0
            return

        # Measure velocity from position delta over the control tick. This
        # averages over the full 50 ms window and is much less noisy than the
        # per-pulse self.velocity (which at 180 dps target only sees ~1 pulse
        # per tick). Then EMA-smooth to absorb residual jitter.
        now = time.ticks_ms()
        dt_ctrl = time.ticks_diff(now, self.last_control_time) / 1000.0
        if dt_ctrl <= 0 or self.last_control_time == 0:
            inst = 0.0
        else:
            inst = (self.position - self.last_control_position) / dt_ctrl
        self.last_control_position = self.position
        self.last_control_time = now
        # EMA: alpha=0.5 means new sample is half-weight; quick response,
        # still kills single-tick spikes.
        self.measured_velocity = 0.5 * self.measured_velocity + 0.5 * inst
        measured = self.measured_velocity

        error = target - measured
        max_dps = MOTOR_CONFIG['max_speed_dps']
        ff_percent = target / (max_dps / 100.0)

        # PI correction in PWM-percent units. KP=0.05 means 1 dps of error
        # adjusts PWM by 0.05%; KI=0.4 over 50 ms = 0.02% per dps·tick.
        dt = MOTOR_CONFIG['control_loop_ms'] / 1000.0
        self.velocity_integral += error * dt
        # Anti-windup: clamp integral so a stalled motor can't ramp PWM forever.
        self.velocity_integral = max(-200, min(200, self.velocity_integral))

        kp = 0.05
        ki = 0.4
        correction = error * kp + self.velocity_integral * ki

        new_percent = ff_percent + correction
        # Clamp to same sign as target. The encoder is single-channel and
        # tracks direction from the commanded PWM sign — if we let the
        # controller dip past zero to brake, the next encoder pulse from a
        # still-rolling wheel would decrement position and read negative
        # velocity, which then poisons the next control cycle.
        if target > 0:
            new_percent = max(0.5, min(100, new_percent))
        else:
            new_percent = max(-100, min(-0.5, new_percent))
        self._set_servo_speed(new_percent)

    def stop(self):
        """Force Stop"""
        print(f'STOP command sent to Port {self.port}')
        self.is_running = False
        self.print_ticks = False
        self.control_mode = 'idle'
        self.velocity_integral = 0.0
        self.control_timer.deinit()
        self._set_servo_speed(0) # Triggers Hard Stop
        time.sleep_ms(50)
        self._set_servo_speed(0) # Triggers Hard Stop
        time.sleep_ms(50)
        self._set_servo_speed(0) # Triggers Hard Stop
        return

# Global motor instances
_motors = {}

def _get_motor(port):
    if port not in _motors:
        if port in MOTOR_PINS:
            pins = MOTOR_PINS[port]
            _motors[port] = Motor(port, pins['servo'], pins['encoder'])
        else:
            raise ValueError(f"Invalid port: {port}")
    return _motors[port]

# --- API Functions ---

def run(port, velocity, *, acceleration=1000):
    motor = _get_motor(port)
    motor.target_velocity = velocity
    if velocity == 0:
        motor.stop()
        return
    if motor.control_mode != 'velocity':
        # Switch into closed-loop velocity mode. Reset integral and the
        # per-tick velocity-tracking state so prior position-control work
        # can't bias the first measurement.
        motor.velocity_integral = 0.0
        motor.measured_velocity = 0.0
        motor.last_control_position = motor.position
        motor.last_control_time = time.ticks_ms()
        motor.control_timer.deinit()
        motor.control_mode = 'velocity'
        motor.is_running = True
        motor.control_timer.init(
            period=MOTOR_CONFIG['control_loop_ms'],
            mode=Timer.PERIODIC,
            callback=motor._velocity_control)
    else:
        motor.is_running = True

def run_for_degrees(port, degrees, velocity, *, stop=True, acceleration=1000, deceleration=1000):
    motor = _get_motor(port)
    
    # Enable Prints
    motor.print_ticks = True
    
    start_position = motor.position
    motor.target_position = start_position + degrees
    motor.target_velocity = velocity
    motor.is_running = True

    # Start the "Brain" loop
    motor.control_timer.deinit()
    motor.control_mode = 'position'
    motor.control_timer.init(period=MOTOR_CONFIG['control_loop_ms'], mode=Timer.PERIODIC, callback=motor._position_control)
    
    # Safety Timeout (Stop after 5 seconds if stuck)
    start_time = time.ticks_ms()
    
    if stop:
        while motor.is_running:
            time.sleep_ms(10)
            # Timeout protection
            if time.ticks_diff(time.ticks_ms(), start_time) > 5000:
                print("TIMEOUT: Forcing stop.")
                motor.stop()
                break

# Helper wrappers
def run_for_time(port, time_ms, velocity, *, stop=True, acceleration=1000, deceleration=1000):
    motor = _get_motor(port)
    speed_percent = max(-100, min(100, velocity / (MOTOR_CONFIG['max_speed_dps'] / 100)))
    motor._set_servo_speed(speed_percent)
    motor.is_running = True
    time.sleep_ms(time_ms)
    if stop:
        motor.stop()

def run_to_position(port, position, velocity, *, direction=SHORTEST_PATH, stop=True, acceleration=1000, deceleration=1000):
    motor = _get_motor(port)
    motor.print_ticks = True
    motor.target_position = position
    motor.target_velocity = velocity
    motor.is_running = True
    motor.control_timer.deinit()
    motor.control_mode = 'position'
    motor.control_timer.init(period=MOTOR_CONFIG['control_loop_ms'], mode=Timer.PERIODIC, callback=motor._position_control)
    
    start_time = time.ticks_ms()
    if stop:
        while motor.is_running:
            time.sleep_ms(10)
            if time.ticks_diff(time.ticks_ms(), start_time) > 5000:
                print("TIMEOUT: Forcing stop.")
                motor.stop()
                break

def run_to_degrees_counted(port, degrees, velocity, *, stop=True, acceleration=1000, deceleration=1000):
    run_to_position(port, degrees, velocity, stop=stop, acceleration=acceleration, deceleration=deceleration)

def stop(port, *, stop=True):
    motor = _get_motor(port)
    motor.stop()

def reset_relative_position(port, position):
    motor = _get_motor(port)
    motor.position = position

def get_position(port):
    motor = _get_motor(port)
    return motor.position

def get_degrees_counted(port):
    return get_position(port)

def get_velocity(port):
    motor = _get_motor(port)
    return motor.velocity

def get_default_velocity(port):
    return MOTOR_CONFIG['default_speed_dps']

def set_degrees_counted(port, degrees_counted):
    reset_relative_position(port, degrees_counted)

def was_interrupted(port): return False
def was_stalled(port): return False
def get_duty_cycle(port):
    motor = _get_motor(port)
    return motor.current_speed