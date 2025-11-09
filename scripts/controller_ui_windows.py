"""
Robot Controller UI - Main Application
Simplified main loop using modular components
"""
import pygame
import time
import sys
import threading

from utils.controller_config_loader import load_config, get_axis, get_button, get_dpad, verify_config
from ui_components import *
from control_protocol import map_axis, map_trigger, format_message, parse_incoming_message
from autonomous_control import drive_autonomous_sequence
from bluetooth_manager import BluetoothManager

# ================= CONFIG =================
BT_ADDR = "98:d3:02:96:be:1b"
BT_BAUD = 115200
UPDATE_HZ = 50  # Update rate in Hz
# ==========================================




def deadzone(val):
    """Apply deadzone to controller input."""
    return 0 if abs(val) <= 1 else val


def get_auto_button_rects():
    """Return the rectangles for autonomous control buttons."""
    # These positions match where buttons are drawn in render_ui
    start_rect = pygame.Rect(820 - 20, 320 - 20, 40, 40)
    stop_rect = pygame.Rect(920 - 20, 320 - 20, 40, 40)
    return start_rect, stop_rect


def render_ui(screen, screen_width, screen_height, font_large, font_medium, font_small,
             lx, ly, rx, ry, lt, rt, a, b, x, y, lb, rb, back, start_btn, xbox,
             dup, ddn, dlf, drt, start_override, system_button_pos_x, system_button_pos_y,
             robot_mode, bt_status, telemetry_data, last_message, autonomous_running):
    """Render all UI components."""
    screen.fill(COLOR_BG)

    # Title
    draw_text(screen, "Robot Controller Interface",
              (screen_width // 2, 20), font_large, COLOR_ACCENT, "center")

    # Left stick
    draw_stick_indicator(screen, (50, 100), lx, ly, "LEFT STICK", font_small)

    # Right stick
    draw_stick_indicator(screen, (250, 100), rx, ry, "RIGHT STICK", font_small)

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
    draw_button_indicator(screen, (30, shoulder_y), "LB", lb, font_small)
    draw_button_indicator(screen, (360, shoulder_y), "RB", rb, font_small)

    # System buttons
    draw_button_indicator(screen, (100, system_button_pos_y), "_", back, font_small)
    draw_button_indicator(screen, (200, system_button_pos_y), "XBOX", xbox, font_small)
    draw_button_indicator(screen, (system_button_pos_x, system_button_pos_y),
                          "MODE", (start_btn or start_override), font_small)

    # D-pad
    dpad_center_x = 100
    dpad_center_y = 380
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

    # Autonomous running warning (controller input blocked)
    if autonomous_running:
        draw_text(screen, "🤖 AUTONOMOUS MODE - Controller Input Blocked",
                  (screen_width // 2, screen_height - 50),
                  font_medium, COLOR_WARNING, "center")

    # Draw Autonomous Start/Stop buttons
    draw_button_indicator(screen, (820, 320), "AUTO\nSTART", not autonomous_running, font_small)
    draw_button_indicator(screen, (920, 320), "AUTO\nSTOP", autonomous_running, font_small)


def handle_mouse_click(event, start_button_rect, stop_button_rect,
                      system_button_pos_x, system_button_pos_y, system_button_radius,
                      bt_manager, auto_thread, auto_stop_event, autonomous_running,
                      start_override, last_message, last_message_time):
    """Handle mouse button clicks for UI buttons."""
    if event.button != 1:  # Only handle left click
        return autonomous_running, start_override, last_message, last_message_time, auto_thread, auto_stop_event
    
    mx, my = event.pos
    
    # Check MODE button area
    rect_start_click = pygame.Rect(
        system_button_pos_x - system_button_radius,
        system_button_pos_y - system_button_radius,
        system_button_radius * 2,
        system_button_radius * 2,
    )
    if rect_start_click.collidepoint(mx, my):
        start_override = True
        last_message = "MODE button clicked (sent start=1)"
        last_message_time = time.time()
    
    # Autonomous START button
    if start_button_rect and start_button_rect.collidepoint(mx, my):
        if not autonomous_running:
            auto_stop_event = threading.Event()
            
            def status_callback(msg):
                nonlocal last_message, last_message_time
                last_message = msg
                last_message_time = time.time()
            
            bt_socket = bt_manager.socket if bt_manager else None
            auto_thread = threading.Thread(
                target=drive_autonomous_sequence,
                args=(bt_socket, auto_stop_event, status_callback),
                daemon=True,
            )
            auto_thread.start()
            autonomous_running = True
            last_message = "Autonomous started"
            last_message_time = time.time()
    
    # Autonomous STOP button
    if stop_button_rect and stop_button_rect.collidepoint(mx, my):
        if autonomous_running and auto_stop_event:
            auto_stop_event.set()
            # Send immediate stop command
            if bt_manager and bt_manager.is_connected():
                bt_manager.send(b"+000 +000 +000 +000 000 000 000000000 0 0 0 0 1\n")
            last_message = "Autonomous stop requested"
            last_message_time = time.time()
    
    return autonomous_running, start_override, last_message, last_message_time, auto_thread, auto_stop_event


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

    # On-screen MODE/START button override (momentary)
    start_override = False
    # Predefined coordinates for system buttons so events can reference them
    system_button_pos_x = 300
    system_button_pos_y = 500
    system_button_radius = 20

    # Robot state
    robot_mode = "DISCONNECTED"
    telemetry_data = {}
    last_message = ""
    last_message_time = None

    # Autonomous control state
    auto_thread = None
    auto_stop_event = None
    autonomous_running = False

    # Button rectangles for click detection (updated each frame)
    start_button_rect = None
    stop_button_rect = None

    # Initialize Bluetooth connection
    bt_manager = None
    if not test_mode:
        bt_manager = BluetoothManager(BT_ADDR, BT_BAUD)
        if not bt_manager.connect():
            print("Running in OFFLINE mode")
            bt_manager = None
    else:
        print("Running in TEST MODE")

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
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    result = handle_mouse_click(event, start_button_rect, stop_button_rect,
                                               system_button_pos_x, system_button_pos_y, system_button_radius,
                                               bt_manager, auto_thread, auto_stop_event, autonomous_running,
                                               start_override, last_message, last_message_time)
                    autonomous_running, start_override, last_message, last_message_time, auto_thread, auto_stop_event = result

            pygame.event.pump()

            # Read incoming data from Bluetooth if available
            if bt_manager and bt_manager.is_connected():
                msg = bt_manager.receive_line()
                if msg:
                    msg_type, data = parse_incoming_message(msg)
                    if msg_type == "MODE":
                        robot_mode = data
                        last_message = f"Mode changed to: {data}"
                    elif msg_type == "TELEMETRY":
                        telemetry_data = data
                        last_message = "Telemetry received"
                    else:
                        last_message = data

            # Read controller inputs (but don't send if autonomous is running)
            if not autonomous_running:
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
                start_btn = get_button(joy, config, "start")
                xbox = get_button(joy, config, "xbox")

                dup, ddn, dlf, drt = get_dpad(joy, config)

                # Combine joystick start with on-screen override for a momentary press
                start_to_send = 1 if (start_btn or start_override) else 0

                # Send data
                msg = format_message(lx, ly, rx, ry, lt, rt,
                                     (a, b, x, y, lb, rb, back, start_to_send, xbox),
                                     (dup, ddn, dlf, drt))

                if bt_manager and bt_manager.is_connected() and not test_mode:
                    if not bt_manager.send(msg):
                        last_message = "Send error"
            else:
                # When autonomous is running, set all inputs to zero for UI display
                lx = ly = rx = ry = lt = rt = 0
                a = b = x = y = lb = rb = back = start_btn = xbox = 0
                dup = ddn = dlf = drt = 0

            # If autonomous thread finished, clear running flag
            if autonomous_running and auto_thread is not None and not auto_thread.is_alive():
                autonomous_running = False
                auto_thread = None
                auto_stop_event = None
                if isinstance(telemetry_data, dict):
                    telemetry_data["auto_running"] = False

            # Clear momentary override (only send once)
            if start_override:
                start_override = False

            # Clear last_message after a short timeout (2 seconds)
            if last_message_time is not None and time.time() - last_message_time > 2.0:
                last_message = ""
                last_message_time = None

            # Update telemetry with autonomous status
            if isinstance(telemetry_data, dict):
                telemetry_data["auto_running"] = autonomous_running

            # ========== RENDER UI ==========
            render_ui(screen, screen_width, screen_height, font_large, font_medium, font_small,
                     lx, ly, rx, ry, lt, rt, a, b, x, y, lb, rb, back, start_btn, xbox,
                     dup, ddn, dlf, drt, start_override, system_button_pos_x, system_button_pos_y,
                     robot_mode, bt_manager.status if bt_manager else "OFFLINE",
                     telemetry_data, last_message, autonomous_running)

            start_button_rect, stop_button_rect = get_auto_button_rects()

            pygame.display.flip()
            clock.tick(UPDATE_HZ)

    except KeyboardInterrupt:
        print("\nStopped by user.")

    finally:
        # Close Bluetooth connection
        if bt_manager:
            bt_manager.close()
        
        # Ensure autonomous thread is signaled to stop and joined
        if autonomous_running and auto_stop_event:
            auto_stop_event.set()
        if auto_thread is not None and auto_thread.is_alive():
            auto_thread.join(timeout=1.0)
        
        pygame.quit()
        print("Controller UI closed.")
if __name__ == "__main__":
    main()
