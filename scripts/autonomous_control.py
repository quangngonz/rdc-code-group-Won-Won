"""
Autonomous Control Module
Handles autonomous driving sequences and operations
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

    msg = format_message(lx, ly, rx, ry, lt, rt, buttons, dpad)
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
    
    Returns a list of steps in format: (description, controls_tuple_or_None, duration)
    """
    default_steps = [
        ("Move forward", (0, +100, 0, 0, 0, 0), 10.0),
        ("Strafe right", (+100, 0, 0, 0, 0, 0), 1.5),
        ("Rotate clockwise", (0, 0, +100, 0, 0, 0), 1.2),
        ("Move backward", (0, -100, 0, 0, 0, 0), 2.0),
        ("Extend Pneumatic arm", None, 1.0),
        ("Retract Pneumatic arm", None, 1.0)
    ]
    
    try:
        if not os.path.exists(filename):
            # Create default file if it doesn't exist
            save_autonomous_sequence(default_steps, filename)
            return default_steps
        
        with open(filename, 'r') as f:
            data = json.load(f)
        
        steps = []
        for step in data:
            desc = step["description"]
            controls = tuple(step["controls"]) if step["controls"] is not None else None
            duration = step["duration"]
            steps.append((desc, controls, duration))
        
        print(f"Loaded {len(steps)} steps from {filename}")
        return steps
    except Exception as e:
        print(f"Error loading sequence file: {e}. Using default sequence.")
        return default_steps


def save_autonomous_sequence(steps, filename="autonomous_sequence.txt"):
    """Save autonomous sequence to a text file."""
    try:
        data = []
        for desc, controls, duration in steps:
            data.append({
                "description": desc,
                "controls": list(controls) if controls is not None else None,
                "duration": duration
            })
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved sequence to {filename}")
    except Exception as e:
        print(f"Error saving sequence file: {e}")


def drive_autonomous_sequence(bt, stop_event, status_callback=None):
    """Background autonomous sequence runner.

    Periodically checks stop_event and calls status_callback(message)
    to report progress to the main UI.
    
    Reads the sequence from autonomous_sequence.txt each time it runs.
    """
    
    # Load sequence from file every time this function is called
    steps = load_autonomous_sequence()

    # Send interval in seconds (controls how often we re-send the same command)
    # A small interval keeps the command present on the wire for the whole step.
    send_interval = 0.05  # 50 ms -> ~20 Hz

    try:
        for desc, controls, duration in steps:
            if stop_event.is_set():
                # send an immediate stop before returning
                send_control(bt, 0, 0, 0, 0)
                if status_callback:
                    status_callback("Autonomous stopped")
                return

            if status_callback:
                status_callback(f"Autonomous: {desc}")

            # Handle pneumatic commands (controls is None for pneumatic steps)
            if controls is None:
                if "Extend" in desc:
                    # Button A extends pneumatic
                    buttons = [1, 0, 0, 0, 0, 0, 0, 0, 0]
                elif "Retract" in desc:
                    # Button B retracts pneumatic
                    buttons = [0, 1, 0, 0, 0, 0, 0, 0, 0]
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
            else:
                # Movement command
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
