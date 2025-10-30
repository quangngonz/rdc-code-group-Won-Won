"""
Controller configuration loader and helper functions.
Loads controller_config.json and provides safe getter functions.
"""
import json
import os

CONFIG_FILE = "C:\\Users\\USER\\Documents\\rdc-code-group-Won-Won\\scripts\\my_config.json"

# Default Xbox controller mapping (fallback)
DEFAULT_CONFIG = {
    "controller_name": "Xbox Controller (Default)",
    "axes": {
        "left_stick_x": 0,
        "left_stick_y": 1,
        "right_stick_x": 2,
        "right_stick_y": 3,
        "left_trigger": 5,
        "right_trigger": 4
    },
    "buttons": {
        "a": 0,
        "b": 1,
        "x": 3,
        "y": 4,
        "lb": 6,
        "rb": 7,
        "back": 10,
        "start": 11,
        "xbox": 12
    },
    "hats": {
        "dpad": 0
    }
}


def load_config(filename=CONFIG_FILE):
    """
    Load controller configuration from JSON file.
    Returns the config dictionary or default config if file doesn't exist.
    """
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
            print(f"✓ Loaded controller config: {config['controller_name']}")
            return config
        except Exception as e:
            print(f"⚠ Error loading config file: {e}")
            print("Using default Xbox controller configuration...")
            return DEFAULT_CONFIG
    else:
        print("⚠ No configuration file found.")
        print("  Using default Xbox controller configuration.")
        print("  Run 'python generate_controller_config.py' to create a custom config.")
        return DEFAULT_CONFIG


def get_axis(joy, config, axis_name):
    """
    Get axis value using the configuration.
    Returns the value of the specified axis, or 0.0 if not mapped.

    Args:
        joy: pygame joystick object
        config: configuration dictionary
        axis_name: name of the axis (e.g., 'left_stick_x')

    Returns:
        float: axis value between -1.0 and 1.0, or 0.0 if not mapped
    """
    axis_index = config["axes"].get(axis_name)
    if axis_index is not None:
        try:
            return joy.get_axis(axis_index)
        except:
            return 0.0
    return 0.0


def get_button(joy, config, button_name):
    """
    Get button state using the configuration.
    Returns 1 if pressed, 0 if not pressed or not mapped.

    Args:
        joy: pygame joystick object
        config: configuration dictionary
        button_name: name of the button (e.g., 'a', 'b', 'start')

    Returns:
        int: 1 if pressed, 0 otherwise
    """
    button_index = config["buttons"].get(button_name)
    if button_index is not None:
        try:
            return joy.get_button(button_index)
        except:
            return 0
    return 0


def get_dpad(joy, config):
    """
    Get D-pad state using the configuration.
    Returns tuple of (up, down, left, right) as 0 or 1 values.

    Args:
        joy: pygame joystick object
        config: configuration dictionary

    Returns:
        tuple: (dup, ddn, dlf, drt) each 0 or 1
    """
    hat_index = config["hats"].get("dpad")
    if hat_index is not None:
        try:
            hat = joy.get_hat(hat_index)

            dup = 1 if hat[1] == 1 else 0
            ddn = 1 if hat[1] == -1 else 0
            dlf = 1 if hat[0] == -1 else 0
            drt = 1 if hat[0] == 1 else 0

            return dup, ddn, dlf, drt
        except:
            return 0, 0, 0, 0

    # If no D-pad mapped, return all zeros
    return 0, 0, 0, 0


def verify_config(joy, config):
    """
    Verify if the current controller matches the configured controller.
    Prints a warning if they don't match.

    Args:
        joy: pygame joystick object
        config: configuration dictionary

    Returns:
        bool: True if user wants to continue, False otherwise
    """
    current_name = joy.get_name()
    config_name = config.get("controller_name", "Unknown")

    if current_name != config_name:
        print("\n" + "=" * 70)
        print("⚠ WARNING: Controller Mismatch!")
        print("=" * 70)
        print(f"  Connected controller: {current_name}")
        print(f"  Configured for:       {config_name}")
        print("\n  The button mapping may not work correctly!")
        print("  Consider running 'python generate_controller_config.py' to")
        print("  create a new configuration for this controller.")
        print("=" * 70)

        response = input("\n  Continue anyway? (y/n): ").strip().lower()
        return response == 'y'

    return True
