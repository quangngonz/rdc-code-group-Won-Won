import time
import socket
import threading
import time as _time

# Bluetooth Configuration
BT_ADDR = "98:d3:02:96:be:1b"  # Same as controller_uart_windows.py
BT_PORT = 1  # RFCOMM channel

# Telemetry storage
latest_telemetry = {
    "motors": [],
    "tof_distance": None,
    "pneu_state": None,
    "other": [],
    "raw_message": ""
}


def format_message(lx, ly, rx, ry, lt, rt, buttons, dpad):
    """
    Format: LX LY RX RY LT RT ABXYLBRBBACKSTARTXBOX DPAD_UP DN LF RT CON\n
    """
    a, b, x, y, lb, rb, back, start, xbox = buttons
    dup, ddn, dlf, drt = dpad

    msg = f"{lx:+04d} {ly:+04d} {rx:+04d} {ry:+04d} "
    msg += f"{lt:03d} {rt:03d} "
    msg += f"{a}{b}{x}{y}{lb}{rb}{back}{start}{xbox} "
    msg += f"{dup} {ddn} {dlf} {drt} 1\n"
    return msg


def send(bt, lx, ly, rx, ry, lt=0, rt=0, buttons=None, dpad=None):
    """Sends one formatted control message via Bluetooth."""
    if buttons is None:
        buttons = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # A,B,X,Y,LB,RB,Back,Start,Xbox
    if dpad is None:
        dpad = [0, 0, 0, 0]               # UP, DOWN, LEFT, RIGHT

    msg = format_message(lx, ly, rx, ry, lt, rt, buttons, dpad)
    bt.sendall(msg.encode('utf-8'))
    print(f"> Sent: {msg.strip()}", flush=True)


def stop(bt):
    """Stops all motion."""
    send(bt, 0, 0, 0, 0)


def parse_motor_data(motor_str):
    """
    Parse motor data string: "MOT[ID] vel cur ecn temp"
    Returns dict with motor info or None if parsing fails
    """
    try:
        parts = motor_str.strip().split()
        if len(parts) < 5 or not parts[0].startswith("MOT"):
            return None

        motor_id = parts[0][3:]  # Extract ID from MOT[ID]
        velocity = int(parts[1])
        current = int(parts[2])
        encoder = int(parts[3])
        temperature = int(parts[4])

        return {
            "id": motor_id,
            "velocity_rpm": velocity,
            "current": current,
            "encoder": encoder,
            "temperature": temperature
        }
    except (ValueError, IndexError):
        return None


def parse_telemetry(msg):
    """
    Parse incoming telemetry message.
    Format: MOT[ID] vel cur ecn temp \t MOT[ID] vel cur ecn temp \t ... \t TOF distance \t PNEU state \n
    Returns dict with parsed telemetry data
    """
    msg = msg.strip()

    if '\t' not in msg:
        # Not telemetry, just a message
        return None

    parts = [p.strip() for p in msg.split('\t') if p.strip()]

    motors = []
    tof_distance = None
    pneu_state = None
    other_data = []

    for part in parts:
        if part.startswith("MOT"):
            motor_info = parse_motor_data(part)
            if motor_info:
                motors.append(motor_info)
        elif part.startswith("TOF"):
            # Parse TOF distance: "TOF distance"
            tof_parts = part.split()
            if len(tof_parts) >= 2:
                try:
                    tof_distance = int(tof_parts[1])
                except ValueError:
                    pass
        elif part.startswith("PNEU"):
            # Parse pneumatic state: "PNEU state" (0=retracted, 1=extended)
            pneu_parts = part.split()
            if len(pneu_parts) >= 2:
                try:
                    pneu_state = int(pneu_parts[1])
                except ValueError:
                    pass
        else:
            other_data.append(part)

    return {
        "motors": motors,
        "tof_distance": tof_distance,
        "pneu_state": pneu_state,
        "other": other_data,
        "raw_message": msg
    }


def print_telemetry(telemetry):
    """Print telemetry data in a readable format."""
    if not telemetry:
        return

    print("\n" + "="*60)
    print("TELEMETRY DATA")
    print("="*60)

    # Motor data
    if telemetry["motors"]:
        print("\nMotors:")
        for motor in telemetry["motors"]:
            print(f"  Motor {motor['id']}:")
            print(f"    Velocity: {motor['velocity_rpm']:4d} RPM")
            print(f"    Current:  {motor['current']:4d}")
            print(f"    Encoder:  {motor['encoder']:5d}")
            print(f"    Temp:     {motor['temperature']:2d}°C")

    # ToF sensor
    if telemetry["tof_distance"] is not None:
        print(f"\nToF Distance: {telemetry['tof_distance']} mm")

    # Pneumatic state
    if telemetry["pneu_state"] is not None:
        state_str = "EXTENDED" if telemetry["pneu_state"] == 1 else "RETRACTED"
        print(f"Pneumatic:    {state_str}")

    # Other data
    if telemetry["other"]:
        print(f"\nOther: {telemetry['other']}")

    print("="*60 + "\n")


def print_telemetry_live(telemetry):
    """Print a concise, single-line live telemetry summary (always flush output).

    This prints a compact summary so the output can be scanned quickly.
    """
    if not telemetry:
        print("No telemetry yet", flush=True)
        return

    ts = _time.time()
    motors = telemetry.get("motors", [])
    motor_strs = []
    for m in motors:
        try:
            motor_strs.append(f"M{m['id']}:{m['velocity_rpm']}rpm")
        except Exception:
            pass

    tof = telemetry.get("tof_distance")
    pneu = telemetry.get("pneu_state")
    pneu_str = "?"
    if pneu is not None:
        pneu_str = "EXT" if pneu == 1 else "RET"

    other = telemetry.get("other")
    raw = telemetry.get("raw_message", "")

    line = (f"[{ts:.1f}] TOF:{tof}mm PNEU:{pneu_str} "
            f"MOTORS:{' '.join(motor_strs)} OTHER:{other} RAW:{raw}")
    print(line, flush=True)


def telemetry_printer(stop_event, interval=0.5):
    """Background thread that prints the latest telemetry periodically.

    Keeps printing the latest known telemetry even if no new packets arrive,
    so the console always shows a live update.
    """
    global latest_telemetry
    while not stop_event.is_set():
        try:
            print_telemetry_live(latest_telemetry)
        except Exception as e:
            print(f"Telemetry printer error: {e}", flush=True)
        # Sleep in small chunks to be responsive to stop_event
        _time.sleep(interval)


def telemetry_listener(bt, stop_event):
    """
    Background thread to continuously listen for telemetry data.
    Updates the global latest_telemetry dictionary.
    """
    global latest_telemetry

    recv_buffer = bytearray()
    temp_buf = bytearray(1024)

    while not stop_event.is_set():
        try:
            n = bt.recv_into(temp_buf)
            if n:
                recv_buffer.extend(temp_buf[:n])

                # Check for newline terminator
                idx = recv_buffer.find(b"\n")
                if idx != -1:
                    line = bytes(recv_buffer[:idx])
                    del recv_buffer[:idx + 1]

                    try:
                        msg = line.decode('utf-8', errors='replace')
                        telemetry = parse_telemetry(msg)

                        if telemetry:
                            # Update global telemetry storage
                            latest_telemetry = telemetry
                            # Optionally print it (comment out if too verbose)
                            # immediate detailed print is commented out to avoid flooding
                            # print_telemetry(telemetry)
                        else:
                            # Non-telemetry message
                            print(f"< Received: {msg.strip()}", flush=True)
                    except Exception as e:
                        print(f"< Error decoding: {e}", flush=True)
        except BlockingIOError:
            # No data available
            time.sleep(0.01)
        except Exception as e:
            if not stop_event.is_set():
                print(f"< Read error: {e}", flush=True)
            break

    print("Telemetry listener stopped.", flush=True)


def drive_autonomous_sequence(bt):
    """
    Sends a sequence of controller-equivalent commands to the robot autonomously.
    """
    print("Step 1: Move forward", flush=True)
    send(bt, 0, +100, 0, 0)  # LY=+100 forward
    time.sleep(2.0)

    print("Step 2: Strafe right", flush=True)
    send(bt, +100, 0, 0, 0)  # LX=+100 right
    time.sleep(1.5)

    print("Step 3: Rotate clockwise", flush=True)
    send(bt, 0, 0, +100, 0)  # RX=+100 rotate CW
    time.sleep(1.2)

    print("Step 4: Move backward", flush=True)
    send(bt, 0, -100, 0, 0)  # LY=-100 backward
    time.sleep(2.0)

    print("Step 5: Pneumatic extend (A)", flush=True)
    send(bt, 0, 0, 0, 0, buttons=[1, 0, 0, 0, 0, 0, 0, 0, 0])  # A=1
    time.sleep(1.0)

    print("Step 6: Pneumatic retract (B)", flush=True)
    send(bt, 0, 0, 0, 0, buttons=[0, 1, 0, 0, 0, 0, 0, 0, 0])  # B=1
    time.sleep(1.0)

    print("Step 7: Stop all", flush=True)
    stop(bt)
    print("Autonomous sequence complete!", flush=True)


if __name__ == "__main__":
    # Connect to Bluetooth using socket (RFCOMM)
    print(f"Connecting to Bluetooth device at {BT_ADDR}...", flush=True)
    try:
        bt = socket.socket(socket.AF_BLUETOOTH,
                           socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        bt.connect((BT_ADDR, BT_PORT))
        bt.setblocking(False)  # Set to non-blocking for background listener
        print("Connected successfully!", flush=True)
        time.sleep(1)  # allow connection to stabilize
    except Exception as e:
        print(f"Failed to connect to Bluetooth: {e}", flush=True)
        exit(1)

    # Start telemetry listener thread
    stop_event = threading.Event()
    listener_thread = threading.Thread(
        target=telemetry_listener, args=(bt, stop_event), daemon=True)
    listener_thread.start()
    print("Telemetry listener started.\n", flush=True)

    # Start a background printer thread that always prints the latest telemetry
    printer_thread = threading.Thread(
        target=telemetry_printer, args=(stop_event, 0.5), daemon=True)
    printer_thread.start()
    print("Telemetry printer started (updates every 0.5s).\n", flush=True)

    try:
        # Run autonomous sequence
        drive_autonomous_sequence(bt)

        # Wait a bit to receive final telemetry
        print("\nWaiting for final telemetry...", flush=True)
        time.sleep(2.0)

        # Print final telemetry state
        print("\n" + "="*60, flush=True)
        print("FINAL TELEMETRY STATE", flush=True)
        print("="*60, flush=True)
        print_telemetry(latest_telemetry)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.", flush=True)
    finally:
        # Stop telemetry listener
        stop_event.set()
        listener_thread.join(timeout=2.0)
        # Join the printer thread as well
        try:
            printer_thread.join(timeout=2.0)
        except Exception:
            pass

        # Send stop command
        stop(bt)
    bt.close()
    print("Bluetooth connection closed.", flush=True)
