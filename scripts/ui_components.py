"""
UI Components for Robot Controller Interface
Contains all drawing and rendering functions for pygame UI
"""
import pygame

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
    # return rectangle for click detection (centered on pos)
    rect = pygame.Rect(pos[0] - size // 2, pos[1] - size // 2, size, size)
    return rect


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


def draw_motor_telemetry_with_box(surface, pos, motor_data, font_small):
    """
    Draw motor telemetry data in a box under the status box.
    Args: surface to draw on, position (x,y), motor_data list, and font.
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


def draw_status_box(surface, pos, robot_mode, bt_status, telemetry, font, font_small):
    """Draw robot status information box."""
    box_width = 350
    box_height = 200

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

    # Autonomous status (if provided in telemetry dict)
    auto_running = False
    if telemetry and isinstance(telemetry, dict):
        auto_running = telemetry.get("auto_running", False)

    draw_text(surface, f"Autonomous: {('RUNNING' if auto_running else 'STOPPED')}", 
              (pos[0] + 15, y_offset),
              font_small, COLOR_ACCENT)
    y_offset += 25

    # Telemetry data (if available)
    if telemetry:
        motor_data = telemetry.get("motors", [])
        if motor_data:
            draw_motor_telemetry_with_box(
                surface, (pos[0], y_offset + 10), motor_data, font_small)

        gpio_data = telemetry.get("other", [])
        if gpio_data:
            print("GPIO Data:", gpio_data)
