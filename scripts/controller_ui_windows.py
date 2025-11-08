import pygame
import serial
import serial.tools.list_ports
import time
import sys
import socket
from utils.controller_config_loader import load_config, get_axis, get_button, get_dpad, verify_config

# ================= CONFIG =================
BT_ADDR = "98:d3:02:96:be:1b"
BT_BAUD = 115200
UPDATE_HZ = 50  # Update rate in Hz
# ==========================================

# UI Colors
COLOR_BG = (20, 20, 30)
COLOR_TEXT = (220, 220, 220)
COLOR_ACCENT = (0, 200, 255)
COLOR_WARNING = (255, 165, 0)
COLOR_ERROR = (255, 50, 50)
COLOR_SUCCESS = (50, 255, 100)
COLOR_BUTTON_ON = (100, 255, 100)
COLOR_BUTTON_OFF = (60, 60, 80)
COLOR_STICK_BG = (40, 40, 60)
COLOR_STICK_DOT = (255, 100, 100)


def clamp(val, lo, hi):
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
    msg += f"{a}{b}{x}{y}{lb}{rb}{back}{start}{xbox} "
    msg += f"{dup} {ddn} {dlf} {drt} 1\n"
    return msg


def draw_text(surface, text, pos, font, color=COLOR_TEXT, align="left"):
    """Draw text on surface with alignment."""
    text_surface = font.render(text, True, color)
    rect = text_surface.get_rect()

    if align == "center":
        rect.center = pos
    elif align == "right":
        rect.topright = pos
    else:  # left
        rect.topleft = pos

    surface.blit(text_surface, rect)
    return rect


def draw_button_indicator(surface, pos, label, state, font):
    """Draw a button indicator (on/off)."""
    size = 40
    color = COLOR_BUTTON_ON if state else COLOR_BUTTON_OFF
    pygame.draw.circle(surface, color, pos, size // 2)
    pygame.draw.circle(surface, COLOR_TEXT, pos, size // 2, 2)
    draw_text(surface, label, pos, font, COLOR_TEXT, "center")


def draw_stick_indicator(surface, pos, x_val, y_val, label, font_small):
    """Draw a joystick position indicator."""
    size = 100
    center = (pos[0] + size // 2, pos[1] + size // 2)

    # Background circle
    pygame.draw.circle(surface, COLOR_STICK_BG, center, size // 2)
    pygame.draw.circle(surface, COLOR_TEXT, center, size // 2, 2)

    # Draw crosshair
    pygame.draw.line(surface, (80, 80, 100), (center[0] - size // 2, center[1]),
                     (center[0] + size // 2, center[1]), 1)
    pygame.draw.line(surface, (80, 80, 100), (center[0], center[1] - size // 2),
                     (center[0], center[1] + size // 2), 1)

    # Calculate stick position (normalized -100 to 100 maps to radius)
    stick_x = center[0] + (x_val / 100.0) * (size // 2 - 10)
    stick_y = center[1] + (y_val / 100.0) * (size // 2 - 10)

    # Draw stick position
    pygame.draw.circle(surface, COLOR_STICK_DOT,
                       (int(stick_x), int(stick_y)), 8)
    pygame.draw.circle(surface, COLOR_TEXT, (int(stick_x), int(stick_y)), 8, 2)

    # Label
    draw_text(surface, label, (pos[0] + size // 2, pos[1] + size + 10),
              font_small, COLOR_TEXT, "center")

    # Values
    draw_text(surface, f"X:{x_val:+04d}", (pos[0] + size // 2, pos[1] + size + 30),
              font_small, COLOR_ACCENT, "center")
    draw_text(surface, f"Y:{y_val:+04d}", (pos[0] + size // 2, pos[1] + size + 45),
              font_small, COLOR_ACCENT, "center")


def draw_trigger_bar(surface, pos, value, label, font_small):
    """Draw a trigger indicator bar."""
    width = 30
    height = 100

    # Background
    pygame.draw.rect(surface, COLOR_STICK_BG, (pos[0], pos[1], width, height))
    pygame.draw.rect(surface, COLOR_TEXT, (pos[0], pos[1], width, height), 2)

    # Fill based on value (0-100)
    fill_height = int((value / 100.0) * height)
    if fill_height > 0:
        pygame.draw.rect(surface, COLOR_ACCENT,
                         (pos[0], pos[1] + height - fill_height, width, fill_height))

    # Label and value
    draw_text(surface, label, (pos[0] + width // 2, pos[1] + height + 10),
              font_small, COLOR_TEXT, "center")
    draw_text(surface, f"{value:03d}", (pos[0] + width // 2, pos[1] + height + 30),
              font_small, COLOR_ACCENT, "center")


def draw_status_box(surface, pos, robot_mode, bt_status, telemetry, font, font_small):
    """Draw robot status information box."""
    box_width = 350
    box_height = 150

    # Background
    pygame.draw.rect(surface, (30, 30, 50),
                     (pos[0], pos[1], box_width, box_height))
    pygame.draw.rect(surface, COLOR_ACCENT,
                     (pos[0], pos[1], box_width, box_height), 2)

    y_offset = pos[1] + 15

    # Title
    draw_text(surface, "ROBOT STATUS", (pos[0] + box_width // 2, y_offset),
              font, COLOR_ACCENT, "center")
    y_offset += 35

    # Connection status
    conn_color = COLOR_SUCCESS if bt_status == "CONNECTED" else COLOR_ERROR
    draw_text(surface, f"Connection: {bt_status}", (pos[0] + 15, y_offset),
              font_small, conn_color)
    y_offset += 25

    # Robot mode
    mode_colors = {
        "IDLE": COLOR_TEXT,
        "MANUAL": COLOR_SUCCESS,
        "AUTO": COLOR_WARNING,
        "ESTOP": COLOR_ERROR
    }
    mode_color = mode_colors.get(robot_mode, COLOR_TEXT)
    draw_text(surface, f"Mode: {robot_mode}", (pos[0] + 15, y_offset),
              font, mode_color)
    y_offset += 30

    # ToF sensor distance (if available)
    if telemetry:
        tof_distance = telemetry.get("tof_distance")
        if tof_distance is not None:
            draw_text(surface, f"ToF Distance: {tof_distance} mm", (pos[0] + 15, y_offset),
                      font_small, COLOR_ACCENT)
            y_offset += 25

    # Pneumatic state (if available)
    if telemetry:
        pneu_state = telemetry.get("pneu_state")
        if pneu_state is not None:
            pneu_text = "EXTENDED" if pneu_state == 1 else "RETRACTED"
            pneu_color = COLOR_SUCCESS if pneu_state == 1 else COLOR_WARNING
            draw_text(surface, f"Pneumatic: {pneu_text}", (pos[0] + 15, y_offset),
                      font_small, pneu_color)
            y_offset += 25

    # Telemetry data (if available)
    if telemetry:
        motor_data = telemetry.get("motors", [])
        # motor_data = [
        #     {"id": "1", "velocity_rpm": 1500,
        #         "current": 1200, "encoder": 34567, "temperature": 45},
        #     {"id": "2", "velocity_rpm": 1450,
        #         "current": 1150, "encoder": 34000, "temperature": 47},
        #     {"id": "3", "velocity_rpm": 1520, "current": 1250,
        #         "encoder": 35000, "temperature": 46}
        # ]
        if motor_data:
            draw_motor_telemetry_with_box(
                surface, (pos[0], y_offset + 25), motor_data, font_small)

        gpio_data = telemetry.get("other", [])
        if gpio_data:
            print("GPIO Data:", gpio_data)


def draw_motor_telemetry_with_box(surface, pos, motor_data, font_small):
    """
    Draw motor telemetry data.
    In a box under the status box.
    Args: Take in the surface to draw on, position (x,y), motor_data list, and font.
    """
    box_width = 350
    # Dynamic height based on number of motors
    box_height = 30 + len(motor_data) * 75

    font_size = pygame.font.Font(None, font_small.get_height() + 10)

    # Background
    pygame.draw.rect(surface, (30, 30, 50),
                     (pos[0], pos[1], box_width, box_height))
    pygame.draw.rect(surface, COLOR_ACCENT,
                     (pos[0], pos[1], box_width, box_height), 2)

    y_offset = pos[1] + 15

    # Title
    draw_text(surface, "MOTOR TELEMETRY", (pos[0] + box_width // 2, y_offset),
              pygame.font.Font(None, 28), COLOR_ACCENT, "center")
    y_offset += 30

    # Draw each motor's data
    for motor in motor_data:
        motor_id = motor.get("id", "?")
        velocity = motor.get("velocity_rpm", 0)
        current = motor.get("current", 0)
        encoder = motor.get("encoder", 0)
        temperature = motor.get("temperature", 0)

        # Motor ID header
        draw_text(surface, f"Motor {motor_id}", (pos[0] + 10, y_offset),
                  font_size, COLOR_SUCCESS)
        y_offset += 20

        # Motor data (compact 2-column layout)
        draw_text(surface, f"RPM: {velocity:4d}", (pos[0] + 15, y_offset),
                  font_size, COLOR_TEXT)
        draw_text(surface, f"Cur: {current:4d}", (pos[0] + 180, y_offset),
                  font_size, COLOR_TEXT)
        y_offset += 18

        draw_text(surface, f"Enc: {encoder:5d}", (pos[0] + 15, y_offset),
                  font_size, COLOR_TEXT)

        # Temperature warning color
        temp_color = COLOR_ERROR if temperature > 60 else COLOR_WARNING if temperature > 50 else COLOR_TEXT
        draw_text(surface, f"Tmp: {temperature:2d}°C", (pos[0] + 180, y_offset),
                  font_size, temp_color)
        y_offset += 30


def draw_gpio_status(surface, pos, gpio_data, font_small):
    # TODO: Implement GPIO status drawing if needed
    pass


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


def main():
    # Check if running in test mode
    test_mode = "--test" in sys.argv

    # Load controller configuration
    config = load_config()

    # Initialize pygame and controller
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller detected.")
        return

    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f"Connected to controller: {joy.get_name()}")

    # Verify configuration matches controller
    if not verify_config(joy, config):
        print("Exiting...")
        return

    # Setup display
    screen_width = 1024
    screen_height = 575
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Robot Controller UI")
    clock = pygame.time.Clock()

    # Fonts
    font_large = pygame.font.Font(None, 36)
    font_medium = pygame.font.Font(None, 28)
    font_small = pygame.font.Font(None, 20)

    # Robot state
    robot_mode = "DISCONNECTED"
    bt_status = "DISCONNECTED"
    telemetry_data = []
    last_message = ""

    if not test_mode:
        # Connect to Bluetooth UART (RFCOMM socket)
        try:
            bt = socket.socket(socket.AF_BLUETOOTH,
                               socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            bt.connect((BT_ADDR, 1))
            bt.setblocking(False)
            bt_status = "CONNECTED"
            print(f"Connected to Bluetooth device: {BT_ADDR}")
        except Exception as e:
            print(f"Failed to connect to Bluetooth: {e}")
            print("Running in OFFLINE mode")
            bt = None
    else:
        print("Running in TEST MODE")
        bt = None
        bt_status = "TEST MODE"

    # Receive buffer for incoming data
    recv_buffer = bytearray()
    temp_buf = bytearray(1024)

    delay = 1.0 / UPDATE_HZ
    running = True

    print("\nController UI started. Press ESC or close window to exit.")

    try:
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            pygame.event.pump()

            # Read incoming data from Bluetooth if available
            if bt:
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
                                msg_type, data = parse_incoming_message(msg)

                                if msg_type == "MODE":
                                    robot_mode = data
                                    last_message = f"Mode changed to: {data}"
                                elif msg_type == "TELEMETRY":
                                    telemetry_data = data
                                    last_message = "Telemetry received"
                                else:
                                    last_message = data

                            except Exception as e:
                                last_message = f"Error: {e}"
                except BlockingIOError:
                    pass
                except Exception as e:
                    last_message = f"Read error: {e}"
                    bt_status = "ERROR"

            # Read controller inputs
            def deadzone(val):
                return 0 if abs(val) <= 1 else val

            lx = deadzone(map_axis(get_axis(joy, config, "left_stick_x")))
            ly = deadzone(map_axis(get_axis(joy, config, "left_stick_y")))
            rx = deadzone(map_axis(get_axis(joy, config, "right_stick_x")))
            ry = deadzone(map_axis(get_axis(joy, config, "right_stick_y")))

            lt = map_trigger(get_axis(joy, config, "left_trigger"))
            rt = map_trigger(get_axis(joy, config, "right_trigger"))

            a = get_button(joy, config, "a")
            b = get_button(joy, config, "b")
            x = get_button(joy, config, "x")
            y = get_button(joy, config, "y")
            lb = get_button(joy, config, "lb")
            rb = get_button(joy, config, "rb")
            back = get_button(joy, config, "back")
            start = get_button(joy, config, "start")
            xbox = get_button(joy, config, "xbox")

            dup, ddn, dlf, drt = get_dpad(joy, config)

            # Send data
            msg = format_message(lx, ly, rx, ry, lt, rt,
                                 (a, b, x, y, lb, rb, back, start, xbox),
                                 (dup, ddn, dlf, drt))

            if bt and not test_mode:
                try:
                    bt.sendall(msg.encode("utf-8"))
                except Exception as e:
                    last_message = f"Send error: {e}"
                    bt_status = "ERROR"

            # ========== RENDER UI ==========
            screen.fill(COLOR_BG)

            # Title
            draw_text(screen, "Robot Controller Interface",
                      (screen_width // 2, 20), font_large, COLOR_ACCENT, "center")

            # Left stick
            draw_stick_indicator(screen, (50, 100), lx, ly,
                                 "LEFT STICK", font_small)

            # Right stick
            draw_stick_indicator(screen, (250, 100), rx,
                                 ry, "RIGHT STICK", font_small)

            # Triggers
            draw_trigger_bar(screen, (160, 200), lt, "LT", font_small)
            draw_trigger_bar(screen, (210, 200), rt, "RT", font_small)

            # Face buttons (A, B, X, Y)
            button_center_x = 300
            button_center_y = 380
            button_spacing = 40

            draw_button_indicator(screen, (button_center_x, button_center_y - button_spacing),
                                  "Y", y, font_small)
            draw_button_indicator(screen, (button_center_x, button_center_y + button_spacing),
                                  "A", a, font_small)
            draw_button_indicator(screen, (button_center_x - button_spacing, button_center_y),
                                  "X", x, font_small)
            draw_button_indicator(screen, (button_center_x + button_spacing, button_center_y),
                                  "B", b, font_small)

            # Shoulder buttons
            shoulder_y = 80
            draw_button_indicator(
                screen, (30, shoulder_y), "LB", lb, font_small)
            draw_button_indicator(
                screen, (360, shoulder_y), "RB", rb, font_small)

            # System buttons
            system_y = 500
            draw_button_indicator(screen, (100, system_y),
                                  "_", back, font_small)
            draw_button_indicator(screen, (200, system_y),
                                  "XBOX", xbox, font_small)
            draw_button_indicator(screen, (300, system_y),
                                  "MODE", start, font_small)

            # D-pad
            dpad_center_x = 100
            dpad_center_y = 380
            dpad_size = 25
            dpad_spacing = 40

            draw_button_indicator(screen, (dpad_center_x, dpad_center_y - dpad_spacing),
                                  "↑", dup, font_small)
            draw_button_indicator(screen, (dpad_center_x, dpad_center_y + dpad_spacing),
                                  "↓", ddn, font_small)
            draw_button_indicator(screen, (dpad_center_x - dpad_spacing, dpad_center_y),
                                  "←", dlf, font_small)
            draw_button_indicator(screen, (dpad_center_x + dpad_spacing, dpad_center_y),
                                  "→", drt, font_small)

            # Status box
            draw_status_box(screen, (420, 75), robot_mode, bt_status,
                            telemetry_data, font_medium, font_small)

            # Last message footer
            if last_message:
                draw_text(screen, f"Last: {last_message}", (10, screen_height - 25),
                          font_small, COLOR_TEXT)

            # E-STOP warning (if both LB+RB pressed)
            if lb and rb:
                draw_text(screen, "⚠ E-STOP TRIGGER ⚠",
                          (screen_width // 2, screen_height - 25),
                          font_medium, COLOR_ERROR, "center")

            # Update display
            pygame.display.flip()
            clock.tick(UPDATE_HZ)

    except KeyboardInterrupt:
        print("\nStopped by user.")

    finally:
        if bt:
            try:
                # Send stop command before closing
                bt.sendall(
                    b"+000 +000 +000 +000 000 000 000000000 0 0 0 0 1\n")
            except Exception:
                pass
            bt.close()
        pygame.quit()
        print("Controller UI closed.")


if __name__ == "__main__":
    main()
