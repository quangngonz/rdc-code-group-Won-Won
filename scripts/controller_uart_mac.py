import pygame
import serial
import serial.tools.list_ports
import time
import sys

# ================= CONFIG =================
BT_PORT = "/dev/tty.usbserial-2140"          # UART Port
BT_BAUD = 115200
UPDATE_HZ = 50                          # Update rate in Hz
# ==========================================


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

    if xbox == 1:
        return "ESTOP\n"

    msg = f"{lx:+04d} {ly:+04d} {rx:+04d} {ry:+04d} "
    msg += f"{lt:03d} {rt:03d} "
    msg += f"{a}{b}{x}{y}{lb}{rb}{back}{start}{xbox} "
    msg += f"{dup} {ddn} {dlf} {drt} 1\n"
    return msg


def print_controller_output(lx, ly, rx, ry, lt, rt, buttons, dpad, msg=None, verbose=False, received_msg=""):
    """
    Pretty-print controller data in a consistent table format using sys.stdout.flush().
    """
    a, b, x, y, lb, rb, back, start, xbox = buttons
    dup, ddn, dlf, drt = dpad

    lines = [
        "Controller Output:",
        " LX   LY   RX   RY   LT   RT  |  A B X Y LB RB BK ST XB  | UP DN LF RT CON",
        "-------------------------------------------------------------",
        f"{lx:+04d} {ly:+04d} {rx:+04d} {ry:+04d} {lt:+04d} {rt:+04d} |  "
        f"{a} {b} {x} {y}  {lb}  {rb}  {back}  {start}  {xbox}  |  "
        f"{dup}  {ddn}  {dlf}  {drt}   1",
        "",
        f"Received Message: {received_msg}",
    ]

    if msg and verbose:
        lines.append(f"\nFormatted Message:\n{msg.strip()}")
        lines.append(f"msg length: {len(msg.strip())} characters")

    msg = "\n".join(lines) + "\n"
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write(msg)
    sys.stdout.flush()


def main():
    # Check if running in test mode
    test_mode = "--test" in sys.argv
    verbose = "--verbose" in sys.argv

    # Initialize pygame and controller
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller detected.")
        return

    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f"Connected to controller: {joy.get_name()}")

    if not test_mode:
        # Connect to Bluetooth UART
        try:
            bt = serial.Serial(BT_PORT, BT_BAUD, timeout=1)
            print(f"Connected to Bluetooth at {BT_PORT} ({BT_BAUD} baud)")
        except serial.SerialException as e:
            print(f"Failed to open Bluetooth port: {e}")
            return
    else:
        print("Running in TEST MODE — data will not be sent over Bluetooth.")

    delay = 1.0 / UPDATE_HZ
    print("Streaming controller data... Press Ctrl+C to stop.")

    input("Press Enter to begin...")

    received_msg = ""

    try:
        while True:
            pygame.event.pump()

            # Read incoming data from Bluetooth if available
            if not test_mode and bt.in_waiting > 0:
                try:
                    received_msg = bt.readline().decode('utf-8').strip()
                except Exception as e:
                    received_msg = f"Error reading: {e}"

            # Read sticks (Invert Y axes)
            lx = map_axis(joy.get_axis(0))
            ly = -map_axis(joy.get_axis(1))
            rx = map_axis(joy.get_axis(2))
            ry = -map_axis(joy.get_axis(3))

            # Triggers (pressed=1 → released=-1)
            lt = map_trigger(joy.get_axis(5))   # left trigger
            rt = map_trigger(joy.get_axis(4))   # right trigger

            # Buttons
            a = joy.get_button(0)
            b = joy.get_button(1)
            x = joy.get_button(3)
            y = joy.get_button(4)
            lb = joy.get_button(6)
            rb = joy.get_button(7)
            back = joy.get_button(10)
            start = joy.get_button(11)
            xbox = joy.get_button(12)

            # D-pad
            hat = joy.get_hat(0)
            dup = 1 if hat[1] == 1 else 0
            ddn = 1 if hat[1] == -1 else 0
            dlf = 1 if hat[0] == -1 else 0
            drt = 1 if hat[0] == 1 else 0

            msg = format_message(lx, ly, rx, ry, lt, rt,
                                 (a, b, x, y, lb, rb, back, start, xbox),
                                 (dup, ddn, dlf, drt))

            if test_mode:
                print_controller_output(
                    lx, ly, rx, ry, lt, rt,
                    (a, b, x, y, lb, rb, back, start, xbox),
                    (dup, ddn, dlf, drt),
                    msg, verbose, ""
                )
            else:
                bt.write(msg.encode("utf-8"))
                print_controller_output(
                    lx, ly, rx, ry, lt, rt,
                    (a, b, x, y, lb, rb, back, start, xbox),
                    (dup, ddn, dlf, drt),
                    msg, verbose, received_msg
                )

            time.sleep(delay)

    except KeyboardInterrupt:
        print("\nStopped by user.")

        if not test_mode:
            bt.write(b"ESTOP\n")
            print("Sent STOP command to Bluetooth device.")

    finally:
        if not test_mode:
            bt.close()
        pygame.quit()


if __name__ == "__main__":
    main()
