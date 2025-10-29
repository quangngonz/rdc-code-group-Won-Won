import pygame
import json
import time
import sys

CONFIG_FILE = "controller_config.json"


def clear_screen():
    """Clear the terminal screen."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def wait_for_button_press(joy, timeout=10):
    """
    Wait for a button press and return the button index.
    Returns None if timeout or user skips.
    """
    start_time = time.time()
    initial_states = [joy.get_button(i) for i in range(joy.get_numbuttons())]

    print("  Press the button now (or press Enter to skip)...")

    while time.time() - start_time < timeout:
        pygame.event.pump()

        # Check for button presses
        for i in range(joy.get_numbuttons()):
            current = joy.get_button(i)
            if current == 1 and initial_states[i] == 0:
                print(f"  ✓ Detected: Button {i}")
                time.sleep(0.3)  # Debounce
                return i

        time.sleep(0.01)

    return None


def wait_for_axis_movement(joy, timeout=10):
    """
    Wait for significant axis movement and return the axis index.
    Returns None if timeout or user skips.
    """
    # Capture initial states immediately
    initial_states = [joy.get_axis(i) for i in range(joy.get_numaxes())]

    print("  Move the axis/stick to its extreme position (or press Enter to skip)...")

    start_time = time.time()
    detected_axis = None

    while time.time() - start_time < timeout:
        pygame.event.pump()

        # Check for axis movement (threshold > 0.5 for clear detection)
        for i in range(joy.get_numaxes()):
            current = joy.get_axis(i)
            delta = abs(current - initial_states[i])
            if delta > 0.5:
                print(f"  ✓ Detected: Axis {i} (value: {current:.2f})")
                detected_axis = i
                break

        if detected_axis is not None:
            break

        time.sleep(0.01)

    if detected_axis is None:
        return None

    # Wait for the axis to return close to neutral before continuing
    print("  Please release the stick/trigger...")
    release_threshold = 0.2

    while True:
        pygame.event.pump()
        current = joy.get_axis(detected_axis)
        delta = abs(current - initial_states[detected_axis])

        if delta < release_threshold:
            print("  ✓ Released")
            time.sleep(0.2)  # Small delay for stability
            break

        time.sleep(0.05)

    return detected_axis


def wait_for_hat_movement(joy, timeout=10):
    """
    Wait for D-pad/hat movement and return the hat index.
    Returns None if timeout or user skips.
    """
    start_time = time.time()

    print("  Press any direction on the D-pad (or press Enter to skip)...")

    while time.time() - start_time < timeout:
        pygame.event.pump()

        # Check for hat movement
        for i in range(joy.get_numhats()):
            hat = joy.get_hat(i)
            if hat != (0, 0):
                print(f"  ✓ Detected: Hat {i} (direction: {hat})")
                time.sleep(0.3)  # Debounce
                return i

        time.sleep(0.01)

    return None


def configure_controller():
    """
    Interactive controller configuration.
    Returns a configuration dictionary.
    """
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("❌ No controller detected!")
        print("Please connect a controller and try again.")
        return None

    joy = pygame.joystick.Joystick(0)
    joy.init()

    clear_screen()
    print("=" * 70)
    print("CONTROLLER CONFIGURATION GENERATOR")
    print("=" * 70)
    print(f"Controller Name: {joy.get_name()}")
    print(f"Number of Axes: {joy.get_numaxes()}")
    print(f"Number of Buttons: {joy.get_numbuttons()}")
    print(f"Number of Hats (D-pads): {joy.get_numhats()}")
    print("=" * 70)
    print("\nInstructions:")
    print("- When prompted, press the specified button/axis")
    print("- If a button doesn't exist on your controller, press Enter to skip")
    print("- Skipped buttons will be set to return 0 (inactive)")
    print("=" * 70)

    input("\nPress Enter to start configuration...")

    config = {
        "controller_name": joy.get_name(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "axes": {},
        "buttons": {},
        "hats": {}
    }

    # Configure Analog Sticks
    clear_screen()
    print("=" * 70)
    print("STEP 1: ANALOG STICKS")
    print("=" * 70)

    print("\n[Left Stick X-Axis]")
    print("Move the LEFT STICK to the RIGHT (horizontally)")
    config["axes"]["left_stick_x"] = wait_for_axis_movement(joy)

    print("\n[Left Stick Y-Axis]")
    print("Move the LEFT STICK UP (vertically)")
    config["axes"]["left_stick_y"] = wait_for_axis_movement(joy)

    print("\n[Right Stick X-Axis]")
    print("Move the RIGHT STICK to the RIGHT (horizontally)")
    config["axes"]["right_stick_x"] = wait_for_axis_movement(joy)

    print("\n[Right Stick Y-Axis]")
    print("Move the RIGHT STICK UP (vertically)")
    config["axes"]["right_stick_y"] = wait_for_axis_movement(joy)

    # Configure Triggers
    clear_screen()
    print("=" * 70)
    print("STEP 2: TRIGGERS")
    print("=" * 70)

    print("\n[Left Trigger (LT)]")
    print("Press the LEFT TRIGGER fully")
    config["axes"]["left_trigger"] = wait_for_axis_movement(joy)

    print("\n[Right Trigger (RT)]")
    print("Press the RIGHT TRIGGER fully")
    config["axes"]["right_trigger"] = wait_for_axis_movement(joy)

    # Configure Buttons
    clear_screen()
    print("=" * 70)
    print("STEP 3: BUTTONS")
    print("=" * 70)

    button_prompts = [
        ("a", "A button (usually bottom face button)"),
        ("b", "B button (usually right face button)"),
        ("x", "X button (usually left face button)"),
        ("y", "Y button (usually top face button)"),
        ("lb", "Left Bumper (LB) button"),
        ("rb", "Right Bumper (RB) button"),
        ("back", "BACK/SELECT button"),
        ("start", "START button"),
        ("xbox", "XBOX/HOME/GUIDE button"),
    ]

    for key, description in button_prompts:
        print(f"\n[{description.upper()}]")
        config["buttons"][key] = wait_for_button_press(joy)

    # Configure D-pad
    clear_screen()
    print("=" * 70)
    print("STEP 4: D-PAD")
    print("=" * 70)

    print("\n[D-Pad/Directional Pad]")
    config["hats"]["dpad"] = wait_for_hat_movement(joy)

    return config


def display_config(config):
    """Display the configuration in a readable format."""
    clear_screen()
    print("=" * 70)
    print("CONFIGURATION SUMMARY")
    print("=" * 70)
    print(f"Controller: {config['controller_name']}")
    print(f"Created: {config['timestamp']}")

    print("\n--- AXES ---")
    for name, index in config['axes'].items():
        status = f"Axis {index}" if index is not None else "NOT MAPPED (will return 0)"
        print(f"  {name:20s}: {status}")

    print("\n--- BUTTONS ---")
    for name, index in config['buttons'].items():
        status = f"Button {index}" if index is not None else "NOT MAPPED (will return 0)"
        print(f"  {name:20s}: {status}")

    print("\n--- HATS (D-PAD) ---")
    for name, index in config['hats'].items():
        status = f"Hat {index}" if index is not None else "NOT MAPPED (will return 0,0,0,0)"
        print(f"  {name:20s}: {status}")

    print("=" * 70)


def save_config(config, filename=CONFIG_FILE):
    """Save configuration to JSON file."""
    with open(filename, 'w') as f:
        json.dump(config, f, indent=4)
    print(f"\n✓ Configuration saved to: {filename}")
    print(f"  You can now use this config with your controller scripts!")


def main():
    try:
        print("Starting controller configuration...\n")

        config = configure_controller()

        if config is None:
            return

        display_config(config)

        # Ask to save
        save = input("\nSave this configuration? (y/n): ").strip().lower()
        if save == 'y':
            save_config(config)
            print("\n" + "=" * 70)
            print("NEXT STEPS:")
            print("=" * 70)
            print("1. Your configuration has been saved to 'controller_config.json'")
            print("2. Update your controller scripts to use this configuration")
            print("3. Run your controller script normally")
            print("=" * 70)
        else:
            print("\n❌ Configuration not saved.")

            # Ask if they want to save with different name
            alt_save = input(
                "Save with a different name? (y/n): ").strip().lower()
            if alt_save == 'y':
                filename = input(
                    "Enter filename (e.g., my_config.json): ").strip()
                if not filename.endswith('.json'):
                    filename += '.json'
                save_config(config, filename)

    except KeyboardInterrupt:
        print("\n\n❌ Configuration cancelled by user.")

    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
