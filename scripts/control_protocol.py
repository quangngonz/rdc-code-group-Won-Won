"""
Control Protocol for Robot Controller
Handles message formatting, parsing, and data conversion
"""


def clamp(val, lo, hi):
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, val))


def map_axis(value):
    """Convert from [-1, 1] range to [-100, 100] int."""
    return int(round(value * 100))


def map_trigger(value):
    """Convert trigger [0, 1] range to [0, 100] int."""
    return int(round(value * 100))


def format_message(lx, ly, rx, ry, lt, rt, buttons, dpad):
    """
    Format: LX LY RX RY LT RT ABXYLBRBBACKSTARTXBOX DPAD_UP DN LF RT CON\n
    """
    a, b, x, y, lb, rb, back, start, xbox = buttons
    dup, ddn, dlf, drt = dpad

    msg = f"{lx:+04d} {ly:+04d} {rx:+04d} {ry:+04d} "
    msg += f"{lt:03d} {rt:03d} "
    msg += f"{b}{a}{x}{y}{lb}{rb}{back}{start}{xbox} "
    msg += f"{dup} {ddn} {dlf} {drt} 1\n"
    return msg


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


def parse_incoming_message(msg):
    """
    Parse incoming message and determine type.
    Returns: (msg_type, data)
    - msg_type: "MODE", "TELEMETRY", or "MESSAGE"
    - data: parsed content

    Telemetry format: MOT[ID] vel cur ecn temp \t MOT[ID] vel cur ecn temp \t ... \t TOF distance \t PNEU state \n
    """
    msg = msg.strip()

    if '\t' in msg:
        # Telemetry data (tab-separated)
        parts = [p.strip() for p in msg.split('\t') if p.strip()]

        # Parse motor data, TOF sensor, and pneumatic state
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

        telemetry = {
            "motors": motors,
            "tof_distance": tof_distance,
            "pneu_state": pneu_state,
            "other": other_data
        }

        return "TELEMETRY", telemetry
    else:
        # Mode or status message
        if msg.startswith("MODE:"):
            mode = msg.split(":")[1].strip()
            return "MODE", mode
        elif msg.startswith("ESTOP:"):
            status = msg.split(":")[1].strip()
            if status == "ACTIVE":
                return "MODE", "ESTOP"
            else:
                return "MODE", "IDLE"
        else:
            # Unknown message type
            return "MESSAGE", msg
