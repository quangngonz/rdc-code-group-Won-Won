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

    if not test_mode:
        # Connect to Bluetooth UART (RFCOMM socket)
        try:
            bt = socket.socket(socket.AF_BLUETOOTH,
                               socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

            bt.connect((BT_ADDR, 1))
            # Use non-blocking reads and manage our own receive buffer
            bt.setblocking(False)

        except Exception as e:
            # socket operations raise OSError/Exception on failure
            print(f"Failed to open Bluetooth port: {e}")
            return
    else:
        print("Running in TEST MODE — data will not be sent over Bluetooth.")

    delay = 1.0 / UPDATE_HZ
    print("Streaming controller data... Press Ctrl+C to stop.")

    input("Press Enter to begin...")

    # Text of the last completed line received (decoded)
    received_msg = ""

    # A growable buffer for incoming raw bytes; we accumulate until we see b"\n"
    recv_buffer = bytearray()
    # Temporary buffer used with recv_into to avoid per-recv allocations
    temp_buf = bytearray(1024)

    try:
        while True:
            pygame.event.pump()

            # Read incoming data from Bluetooth if available (non-blocking)
            if not test_mode:
                try:
                    # recv_into returns number of bytes read; may raise BlockingIOError
                    n = bt.recv_into(temp_buf)
                    if n:
                        recv_buffer.extend(temp_buf[:n])
                        # Check for newline terminator and extract completed lines
                        idx = recv_buffer.find(b"\n")
                        if idx != -1:
                            line = bytes(recv_buffer[:idx])
                            # remove line + newline from buffer
                            del recv_buffer[:idx+1]
                            try:
                                received_msg = line.decode('utf-8', errors='replace').strip()
                            except Exception as e:
                                received_msg = f"Error decoding line: {e}"
                except BlockingIOError:
                    # No data available on non-blocking socket
                    pass
                except Exception as e:
                    received_msg = f"Error reading: {e}"

            # Read sticks (Invert Y axes) - using config
            lx = map_axis(get_axis(joy, config, "left_stick_x"))
            ly = -map_axis(get_axis(joy, config, "left_stick_y"))
            rx = map_axis(get_axis(joy, config, "right_stick_x"))
            ry = -map_axis(get_axis(joy, config, "right_stick_y"))

            # Triggers (pressed=1 → released=-1) - using config
            lt = map_trigger(get_axis(joy, config, "left_trigger"))
            rt = map_trigger(get_axis(joy, config, "right_trigger"))

            # Buttons - using config
            a = get_button(joy, config, "a")
            b = get_button(joy, config, "b")
            x = get_button(joy, config, "x")
            y = get_button(joy, config, "y")
            lb = get_button(joy, config, "lb")
            rb = get_button(joy, config, "rb")
            back = get_button(joy, config, "back")
            start = get_button(joy, config, "start")
            xbox = get_button(joy, config, "xbox")

            # D-pad - using config
            dup, ddn, dlf, drt = get_dpad(joy, config)

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
                # Use sendall on sockets to ensure the full message is sent
                bt.sendall(msg.encode("utf-8"))
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
            # Ensure stop command is delivered before closing
            try:
                bt.sendall(b"ESTOP\n")
            except Exception:
                pass
            print("Sent STOP command to Bluetooth device.")

    finally:
        if not test_mode:
            bt.close()
        pygame.quit()


if __name__ == "__main__":
    main()
