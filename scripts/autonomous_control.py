"""
Autonomous Control Module
Handles autonomous driving sequences and operations

ToF-Based Movement:
- Simple mode: Bang-bang control (full speed until target)
- PID mode: Smooth speed adjustment based on distance from target
  * Automatically slows down as it approaches target
  * Reduces overshoot and provides smoother motion
  * Tunable via pid_kp, pid_ki, pid_kd parameters
"""
import time
import json
import os
from control_protocol import format_message


def send_control(bt, lx, ly, rx, ry, lt=0, rt=0, buttons=None, dpad=None):
    """Send a formatted control message over the Bluetooth socket if available.

    This is a thin wrapper around format_message that guards against missing
    socket and reports errors via printing.
    """
    if buttons is None:
        buttons = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    if dpad is None:
        dpad = [0, 0, 0, 0]

    # Invert ly to fix forward/backward direction
    msg = format_message(lx, -ly, rx, ry, lt, rt, buttons, dpad)
    try:
        if bt:
            bt.sendall(msg.encode("utf-8"))
        else:
            # Offline/test mode: print the message
            print(f"[AUTO-SIM] Would send: {msg.strip()}")
    except Exception as e:
        print(f"Auto send error: {e}")


def extend_pneumatic(bt, duration=1.0, status_callback=None):
    """Extend pneumatic arm by holding button A for specified duration.
    
    Args:
        bt: Bluetooth socket connection
        duration: How long to hold button A (seconds)
        status_callback: Optional callback for status updates
    """
    if status_callback:
        status_callback(f"Extending pneumatic arm for {duration}s")
    
    buttons_a = [1, 0, 0, 0, 0, 0, 0, 0, 0]  # A button pressed
    dpad = [0, 0, 0, 0]
    send_interval = 0.05  # 50ms -> 20Hz
    
    end_time = time.monotonic() + duration
    next_send = time.monotonic()
    
    while time.monotonic() < end_time:
        now = time.monotonic()
        if now >= next_send:
            send_control(bt, 0, 0, 0, 0, 0, 0, buttons_a, dpad)
            next_send += send_interval
            if next_send < now:
                next_send = now + send_interval
        else:
            time.sleep(min(next_send - now, 0.005))
    
    # Send neutral state to release button
    send_control(bt, 0, 0, 0, 0)
    if status_callback:
        status_callback("Pneumatic extended")


def retract_pneumatic(bt, duration=1.0, status_callback=None):
    """Retract pneumatic arm by holding button B for specified duration.
    
    Args:
        bt: Bluetooth socket connection
        duration: How long to hold button B (seconds)
        status_callback: Optional callback for status updates
    """
    if status_callback:
        status_callback(f"Retracting pneumatic arm for {duration}s")
    
    buttons_b = [0, 1, 0, 0, 0, 0, 0, 0, 0]  # B button pressed
    dpad = [0, 0, 0, 0]
    send_interval = 0.05  # 50ms -> 20Hz
    
    end_time = time.monotonic() + duration
    next_send = time.monotonic()
    
    while time.monotonic() < end_time:
        now = time.monotonic()
        if now >= next_send:
            send_control(bt, 0, 0, 0, 0, 0, 0, buttons_b, dpad)
            next_send += send_interval
            if next_send < now:
                next_send = now + send_interval
        else:
            time.sleep(min(next_send - now, 0.005))
    
    # Send neutral state to release button
    send_control(bt, 0, 0, 0, 0)
    if status_callback:
        status_callback("Pneumatic retracted")


def load_autonomous_sequence(filename="autonomous_sequence.json"):
    """Load autonomous sequence from a text file.
    
    Returns a list of steps. Each step is a dict with:
    - description: str - Description of the step
    - controls: list or None - [lx, ly, rx, ry, lt, rt] or None for pneumatic
    - duration: float or None - Duration in seconds (for time-based movement)
    
    For ToF-based movement:
    - tof_target: int - Target distance in mm (stop when ToF reaches this)
    - tof_timeout: float - Maximum time to try (default 10s)
    - tof_tolerance: int - Tolerance in mm (default 5mm)
    - use_pid: bool - Use PID control (default False for bang-bang)
    
    For PID control (when use_pid=True):
    - pid_kp: float - Proportional gain (default 0.5)
    - pid_ki: float - Integral gain (default 0.0)
    - pid_kd: float - Derivative gain (default 0.1)
    - min_speed: int - Minimum speed to overcome friction (default 20)
    """
    default_steps = [
        {"description": "Move forward", "controls": [0, 100, 0, 0, 0, 0], "duration": 10.0},
        {"description": "Strafe right", "controls": [100, 0, 0, 0, 0, 0], "duration": 1.5},
        {"description": "Rotate clockwise", "controls": [0, 0, 100, 0, 0, 0], "duration": 1.2},
        {"description": "Move backward", "controls": [0, -100, 0, 0, 0, 0], "duration": 2.0},
        {"description": "Extend Pneumatic arm", "controls": None, "duration": 1.0},
        {"description": "Retract Pneumatic arm", "controls": None, "duration": 1.0}
    ]
    
    try:
        if not os.path.exists(filename):
            # Create default file if it doesn't exist
            save_autonomous_sequence(default_steps, filename)
            return default_steps
        
        with open(filename, 'r') as f:
            content = f.read()
            # Remove JavaScript-style comments
            lines = []
            for line in content.split('\n'):
                comment_idx = line.find('//')
                if comment_idx != -1:
                    line = line[:comment_idx]
                if line.strip():
                    lines.append(line)
            clean_content = '\n'.join(lines)
            data = json.loads(clean_content)
        
        steps = []
        for step in data:
            if not step:  # Skip empty objects
                continue
            steps.append(step)
        
        print(f"Loaded {len(steps)} steps from {filename}")
        return steps
    except Exception as e:
        print(f"Error loading sequence file: {e}. Using default sequence.")
        return default_steps


def save_autonomous_sequence(steps, filename="autonomous_sequence.txt"):
    """Save autonomous sequence to a text file."""
    try:
        with open(filename, 'w') as f:
            json.dump(steps, f, indent=2)
        
        print(f"Saved sequence to {filename}")
    except Exception as e:
        print(f"Error saving sequence file: {e}")


def get_tof_distance(bt):
    """
    Try to read current ToF distance from robot telemetry.
    Returns distance in mm or None if unavailable.
    """
    if not bt:
        return None
    
    try:
        # Import here to avoid circular dependency
        from control_protocol import parse_incoming_message
        
        # Try to read a line (non-blocking)
        from bluetooth_manager import BluetoothManager
        if isinstance(bt, BluetoothManager):
            msg = bt.receive_line()
        else:
            # If bt is a socket directly
            try:
                data = bt.recv(1024)
                if data:
                    msg = data.decode('utf-8', errors='replace')
                else:
                    return None
            except BlockingIOError:
                return None
        
        if msg:
            msg_type, data = parse_incoming_message(msg)
            if msg_type == "TELEMETRY" and isinstance(data, dict):
                return data.get("tof_distance")
    except Exception as e:
        print(f"Error reading ToF: {e}")
    
    return None


class SimplePID:
    """Simple PID controller for ToF-based movement."""
    
    def __init__(self, kp=1.0, ki=0.0, kd=0.0, setpoint=0, output_limits=(-100, 100)):
        """
        Initialize PID controller.
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            setpoint: Target value
            output_limits: (min, max) tuple for output clamping
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_limits = output_limits
        
        self._integral = 0
        self._last_error = 0
        self._last_time = None
    
    def reset(self):
        """Reset PID state."""
        self._integral = 0
        self._last_error = 0
        self._last_time = None
    
    def update(self, current_value, current_time=None):
        """
        Calculate PID output based on current value.
        
        Args:
            current_value: Current measurement
            current_time: Current time (monotonic), or None to use time.monotonic()
        
        Returns:
            Control output (clamped to output_limits)
        """
        if current_time is None:
            current_time = time.monotonic()
        
        # Calculate error
        error = self.setpoint - current_value
        
        # Calculate time delta
        if self._last_time is None:
            dt = 0.0
        else:
            dt = current_time - self._last_time
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term (with anti-windup)
        if dt > 0:
            self._integral += error * dt
            # Clamp integral to prevent windup
            max_integral = self.output_limits[1] / max(self.ki, 0.001)
            min_integral = self.output_limits[0] / max(self.ki, 0.001)
            self._integral = max(min_integral, min(max_integral, self._integral))
        i_term = self.ki * self._integral
        
        # Derivative term
        if dt > 0:
            d_term = self.kd * (error - self._last_error) / dt
        else:
            d_term = 0
        
        # Calculate output
        output = p_term + i_term + d_term
        
        # Clamp output
        output = max(self.output_limits[0], min(self.output_limits[1], output))
        
        # Update state
        self._last_error = error
        self._last_time = current_time
        
        return output


def drive_autonomous_sequence(bt, stop_event, status_callback=None):
    """Background autonomous sequence runner.

    Periodically checks stop_event and calls status_callback(message)
    to report progress to the main UI.
    
    Reads the sequence from autonomous_sequence.txt each time it runs.
    
    Each step can be:
    - Time-based: has "duration" field
    - ToF-based: has "tof_target" and "tof_timeout" fields
    - Pneumatic: "controls" is None
    """
    
    # Load sequence from file every time this function is called
    steps = load_autonomous_sequence()

    # Send interval in seconds (controls how often we re-send the same command)
    # A small interval keeps the command present on the wire for the whole step.
    send_interval = 0.05  # 50 ms -> ~20 Hz

    try:
        for step in steps:
            if stop_event.is_set():
                # send an immediate stop before returning
                send_control(bt, 0, 0, 0, 0)
                if status_callback:
                    status_callback("Autonomous stopped")
                return

            desc = step.get("description", "Unknown step")
            controls = step.get("controls")
            duration = step.get("duration")
            tof_target = step.get("tof_target")
            tof_timeout = step.get("tof_timeout", 10.0)  # Default 10s timeout

            print(f"Autonomous step: {desc}")

            if status_callback:
                status_callback(f"Autonomous: {desc}")

            # Handle pneumatic commands (controls is None for pneumatic steps)
            if controls is None:
                if "Extend" in desc:
                    # Button B extends pneumatic
                    buttons = [0, 1, 0, 0, 0, 0, 0, 0, 0]
                elif "Retract" in desc:
                    # Button A retracts pneumatic
                    buttons = [1, 0, 0, 0, 0, 0, 0, 0, 0]
                else:
                    buttons = [0, 0, 0, 0, 0, 0, 0, 0, 0]
                
                dpad = [0, 0, 0, 0]
                end_time = time.monotonic() + duration
                next_send = time.monotonic()
                
                while time.monotonic() < end_time:
                    if stop_event.is_set():
                        send_control(bt, 0, 0, 0, 0)
                        if status_callback:
                            status_callback("Autonomous stopped")
                        return
                    
                    now = time.monotonic()
                    if now >= next_send:
                        send_control(bt, 0, 0, 0, 0, 0, 0, buttons, dpad)
                        next_send += send_interval
                        if next_send < now:
                            next_send = now + send_interval
                    else:
                        time.sleep(min(next_send - now, 0.005))
            
            elif tof_target is not None:
                # ToF-based movement: move until ToF distance reaches target
                # Support both simple bang-bang and PID control
                use_pid = step.get("use_pid", False)
                
                buttons = [0, 0, 0, 0, 0, 0, 0, 0, 0]
                dpad = [0, 0, 0, 0]

                start_time = time.monotonic()
                end_time = start_time + tof_timeout
                next_send = time.monotonic()
                last_tof_check = time.monotonic()
                tof_check_interval = 0.05  # Check ToF every 50ms for faster response
                
                tolerance = step.get("tof_tolerance", 5)  # mm tolerance for "reached"
                
                if use_pid:
                    # PID control mode
                    kp = step.get("pid_kp", 0.5)  # Proportional gain
                    ki = step.get("pid_ki", 0.0)  # Integral gain
                    kd = step.get("pid_kd", 0.1)  # Derivative gain
                    min_speed = step.get("min_speed", 20)  # Minimum speed to overcome friction
                    
                    pid = SimplePID(kp=kp, ki=ki, kd=kd, setpoint=tof_target, output_limits=(-100, 100))
                    
                    if status_callback:
                        status_callback(f"{desc} (PID mode, target: {tof_target}mm)")
                    
                    # Determine which axis to control based on original controls
                    lx, ly, rx, ry, lt, rt = controls
                    control_axis = None
                    if abs(lx) > 0:
                        control_axis = 'lx'
                        direction = 1 if lx > 0 else -1
                    elif abs(ly) > 0:
                        control_axis = 'ly'
                        direction = 1 if ly > 0 else -1
                    elif abs(rx) > 0:
                        control_axis = 'rx'
                        direction = 1 if rx > 0 else -1
                    elif abs(ry) > 0:
                        control_axis = 'ry'
                        direction = 1 if ry > 0 else -1
                    else:
                        if status_callback:
                            status_callback(f"{desc} - Error: No movement axis specified!")
                        break
                    
                    tof_dist = None
                    consecutive_at_target = 0
                    
                    while time.monotonic() < end_time:
                        if stop_event.is_set():
                            send_control(bt, 0, 0, 0, 0)
                            if status_callback:
                                status_callback("Autonomous stopped")
                            return

                        now = time.monotonic()

                        # Check ToF sensor and update PID
                        if now >= last_tof_check + tof_check_interval:
                            new_tof = get_tof_distance(bt)
                            if new_tof is not None:
                                tof_dist = new_tof
                                
                                # Calculate PID output
                                pid_output = pid.update(tof_dist, now)
                                
                                # Apply minimum speed and direction
                                if abs(pid_output) > 0:
                                    if abs(pid_output) < min_speed:
                                        pid_output = min_speed if pid_output > 0 else -min_speed
                                    pid_output *= direction
                                
                                # Update controls based on axis
                                if control_axis == 'lx':
                                    lx = int(pid_output)
                                elif control_axis == 'ly':
                                    ly = int(pid_output)
                                elif control_axis == 'rx':
                                    rx = int(pid_output)
                                elif control_axis == 'ry':
                                    ry = int(pid_output)
                                
                                # Check if at target
                                error = abs(tof_dist - tof_target)
                                if error <= tolerance:
                                    consecutive_at_target += 1
                                    if consecutive_at_target >= 3:  # Stable for 3 readings
                                        if status_callback:
                                            status_callback(f"{desc} - Target reached! (ToF: {tof_dist}mm)")
                                        break
                                else:
                                    consecutive_at_target = 0
                                
                                if status_callback:
                                    status_callback(f"{desc} (ToF: {tof_dist}mm / target: {tof_target}mm, speed: {int(pid_output)})")
                            
                            last_tof_check = now

                        # Send control command
                        if now >= next_send:
                            send_control(bt, lx, ly, rx, ry, lt, rt, buttons, dpad)
                            next_send += send_interval
                            if next_send < now:
                                next_send = now + send_interval
                        else:
                            time.sleep(min(next_send - now, 0.005))
                
                else:
                    # Simple bang-bang control mode (original behavior)
                    lx, ly, rx, ry, lt, rt = controls
                    
                    if status_callback:
                        status_callback(f"{desc} (Bang-bang mode, target: {tof_target}mm)")

                    while time.monotonic() < end_time:
                        if stop_event.is_set():
                            send_control(bt, 0, 0, 0, 0)
                            if status_callback:
                                status_callback("Autonomous stopped")
                            return

                        now = time.monotonic()

                        # Check ToF sensor periodically
                        if now >= last_tof_check + tof_check_interval:
                            tof_dist = get_tof_distance(bt)
                            if tof_dist is not None:
                                if status_callback:
                                    status_callback(f"{desc} (ToF: {tof_dist}mm / target: {tof_target}mm)")
                                
                                if tof_dist <= tof_target + tolerance:
                                    if status_callback:
                                        status_callback(f"{desc} - ToF target reached!")
                                    break
                            last_tof_check = now

                        # Send control command
                        if now >= next_send:
                            send_control(bt, lx, ly, rx, ry, lt, rt, buttons, dpad)
                            next_send += send_interval
                            if next_send < now:
                                next_send = now + send_interval
                        else:
                            time.sleep(min(next_send - now, 0.005))
                
                # Stop movement after reaching target or timeout
                send_control(bt, 0, 0, 0, 0)
                
                if time.monotonic() >= end_time:
                    if status_callback:
                        status_callback(f"{desc} - Timeout reached")
            
            else:
                # Time-based movement command
                lx, ly, rx, ry, lt, rt = controls
                buttons = [0, 0, 0, 0, 0, 0, 0, 0, 0]
                dpad = [0, 0, 0, 0]

                # Use monotonic clock for timing accuracy
                end_time = time.monotonic() + duration
                next_send = time.monotonic()

                # Continuously send the same command at `send_interval` until duration elapses
                while time.monotonic() < end_time:
                    if stop_event.is_set():
                        send_control(bt, 0, 0, 0, 0)
                        if status_callback:
                            status_callback("Autonomous stopped")
                        return

                    now = time.monotonic()
                    if now >= next_send:
                        # Always use send_control so both BT and offline modes behave identically
                        send_control(bt, lx, ly, rx, ry, lt, rt, buttons, dpad)
                        next_send += send_interval
                        # catch up if behind
                        if next_send < now:
                            next_send = now + send_interval
                    else:
                        # Sleep a short time until next scheduled send to remain responsive
                        time.sleep(min(next_send - now, 0.005))

        # Final stop to ensure motors are commanded to 0
        send_control(bt, 0, 0, 0, 0)
        if status_callback:
            status_callback("Autonomous complete - stopped")
    except Exception as e:
        # On unexpected errors, ensure we stop the robot
        try:
            send_control(bt, 0, 0, 0, 0)
        except Exception:
            pass
        if status_callback:
            status_callback(f"Autonomous error: {e}")
        print(f"drive_autonomous_sequence error: {e}")
