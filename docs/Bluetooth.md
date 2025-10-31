# Bluetooth Communication Module (`bluetooth.c`)

## Overview

This module manages Bluetooth communication for a STM32-based robot, enabling remote control via a game controller. It utilizes UART for serial communication and implements a specific protocol to interpret controller inputs. The module is designed to be non-blocking, using UART interrupts for efficient data reception.

## Features

- **UART-based Communication:** Communicates over `USART1`.
- **Interrupt-driven Reception:** Asynchronously receives data without blocking the main application thread.
- **Fixed-width Protocol:** Parses a custom, space-separated protocol for controller data.
- **Connection Status:** Monitors the Bluetooth connection and provides status updates (connected/disconnected) based on a timeout.
- **Command Handling:** Differentiates between controller data and special commands, such as an emergency stop.

## Protocol Format

The communication protocol uses a fixed-width, space-separated format to transmit the state of the game controller. Each message is terminated with a newline character (`\n`).

**Format:**

```
LX LY RX RY LT RT A|B|X|Y|LB|RB|BACK|START|XBOX DPAD_UP DN LF RT CON\n
```

**Example:**

```
+050 -030 +000 +000 000 000 000000000 0 0 0 0 1\n
```

## PC-side controller script (scripts/controller_uart.py)

The repository includes a small Python helper, `scripts/controller_uart.py`, which reads a connected game controller via pygame and streams formatted messages over a serial/UART (Bluetooth) link. The script's behavior clarifies how controller hardware maps into the ASCII protocol.

Key points (exact behavior from the script):

- Configuration:

  - Default serial port: `BT_PORT = "COM5"`
  - Baud rate: `BT_BAUD = 115200`.
  - Update rate: `UPDATE_HZ = 50` (streaming loop delay = 1 / UPDATE_HZ).
  - Run with `--test` to avoid opening the serial port and only print output locally.
  - Use `--verbose` to print the formatted message alongside the pretty table.

- Joystick → protocol mapping (as implemented):

  - Axes:
    - Left stick X = axis 0 → `LX` (mapped by map_axis: value \* 100 → integer in [-100,100]).
    - Left stick Y = axis 1 → `LY` (mapped and inverted in software: `ly = -map_axis(axis1)`).
    - Right stick X = axis 2 → `RX` (map_axis).
    - Right stick Y = axis 3 → `RY` (mapped and inverted: `ry = -map_axis(axis3)`).
  - Triggers:
    - Left trigger = axis 5 → `LT` (mapped by map_trigger: value \* 100 and rounded).
    - Right trigger = axis 4 → `RT` (mapped by map_trigger).
    - Note: the script's `map_trigger` multiplies the raw axis value by 100. Depending on the controller/OS, trigger axes may be reported in [0,1] or [-1,1]; the script expects the raw axis and directly scales it.
  - Buttons (indices used by the script):
    - `A` = button 0
    - `B` = button 1
    - `X` = button 3
    - `Y` = button 4
    - `LB` = button 6
    - `RB` = button 7
    - `BACK` = button 10
    - `START` = button 11
    - `XBOX` = button 12
  - D-Pad (hat): `joy.get_hat(0)` returns a pair `(x, y)`; mapping in the script:
    - `DPAD_UP` = 1 if y == 1 else 0
    - `DPAD_DN` = 1 if y == -1 else 0
    - `DPAD_LF` = 1 if x == -1 else 0
    - `DPAD_RT` = 1 if x == 1 else 0

- Formatted message (exact string produced):
  - The script builds the message using Python formatting; the structure is:

```
{LX:+04d} {LY:+04d} {RX:+04d} {RY:+04d} {LT:03d} {RT:03d} {A}{B}{X}{Y}{LB}{RB}{BACK}{START}{XBOX} {DPAD_UP} {DPAD_DN} {DPAD_LF} {DPAD_RT} 1\n
```

    - Notes:
        - Signed joystick values are formatted with sign and zero-padded to width 4 (e.g. `+050`, `-030`).
        - Triggers are zero-padded to width 3 (e.g. `000`, `100`).
        - The contiguous button block is emitted as digits without separators (e.g. `010100001`).
        - The final `1` in the message is a connection flag sent by the script.

- How to run (host PC):
  - Install dependencies: `pip install -r scripts/requirements.txt` (the script uses `pygame` and `pyserial`).
  - Example run (on Windows with default port):
    - `python scripts/controller_uart.py`
  - For testing without a serial device:
    - `python scripts/controller_uart.py --test --verbose`

Including this section ensures the firmware spec matches what the PC-side helper actually sends and documents exact button/axis indices for debugging.

### Protocol Fields

| Field     | Length (chars) | Range        | Description                                |
| --------- | -------------- | ------------ | ------------------------------------------ |
| `LX`      | 4              | -100 to +100 | Left Joystick X-axis                       |
| `LY`      | 4              | -100 to +100 | Left Joystick Y-axis                       |
| `RX`      | 4              | -100 to +100 | Right Joystick X-axis                      |
| `RY`      | 4              | -100 to +100 | Right Joystick Y-axis                      |
| `LT`      | 3              | 0 to 100     | Left Trigger                               |
| `RT`      | 3              | 0 to 100     | Right Trigger                              |
| `A`       | 1              | 0 or 1       | A button state                             |
| `B`       | 1              | 0 or 1       | B button state                             |
| `X`       | 1              | 0 or 1       | X button state                             |
| `Y`       | 1              | 0 or 1       | Y button state                             |
| `LB`      | 1              | 0 or 1       | Left Bumper state                          |
| `RB`      | 1              | 0 or 1       | Right Bumper state                         |
| `BACK`    | 1              | 0 or 1       | Back button state                          |
| `START`   | 1              | 0 or 1       | Start button state                         |
| `XBOX`    | 1              | 0 or 1       | Xbox button state                          |
| `DPAD_UP` | 1              | 0 or 1       | D-Pad Up state                             |
| `DPAD_DN` | 1              | 0 or 1       | D-Pad Down state                           |
| `DPAD_LF` | 1              | 0 or 1       | D-Pad Left state                           |
| `DPAD_RT` | 1              | 0 or 1       | D-Pad Right state                          |
| `CON`     | 1              | 0 or 1       | Connection status from the controller side |

### Special Commands

- **Emergency Stop:** The command `ESTOP\n` will trigger an emergency stop event.

## Data Structures

### `ControllerParam`

This structure holds the parsed state of the game controller.

```c
typedef struct {
    int16_t left_stick_x;
    int16_t left_stick_y;
    int16_t right_stick_x;
    int16_t right_stick_y;
    uint8_t left_trigger;
    uint8_t right_trigger;
    uint8_t a;
    uint8_t b;
    uint8_t x;
    uint8_t y;
    uint8_t lb;
    uint8_t rb;
    uint8_t back;
    uint8_t start;
    uint8_t xbox;
    uint8_t dpad_up;
    uint8_t dpad_down;
    uint8_t dpad_left;
    uint8_t dpad_right;
    bool connected;
    bool updated;
} ControllerParam;
```

### `BT_Command_t`

A union that holds either controller data or other command types.

```c
typedef union {
    ControllerParam controller;
} BT_CommandData_t;

typedef struct {
    BT_CommandType_t type;
    BT_CommandData_t data;
} BT_Command_t;
```

### `BT_Status_t`

An enumeration for the Bluetooth connection status.

```c
typedef enum {
    BT_STATUS_DISCONNECTED,
    BT_STATUS_CONNECTED
} BT_Status_t;
```

## Functions

A summary of the public functions available in `bluetooth.h`:

- `void Bluetooth_Init(void)`: Initializes the Bluetooth module, clearing buffers and resetting the state.
- `void Bluetooth_StartReceive(void)`: Starts listening for incoming data on the UART port.
- `void Bluetooth_StopReceive(void)`: Stops listening for incoming data.
- `bool Bluetooth_GetController(ControllerParam* controller)`: Retrieves the latest controller data if it has been updated.
- `bool Bluetooth_IsCommandAvailable(void)`: Checks if a new command has been received.
- `bool Bluetooth_GetCommand(BT_Command_t* cmd)`: Retrieves the latest command.
- `bool Bluetooth_SendString(const char* message)`: Transmits a string over Bluetooth.
- `BT_Status_t Bluetooth_GetStatus(void)`: Returns the current connection status.
- `bool Bluetooth_IsConnected(void)`: A convenience function to check if the module is connected.
- `void Bluetooth_Update(void)`: Should be called periodically to update the connection status based on the time since the last message was received.
- `void Bluetooth_RxCallback(void)`: The UART receive complete callback that processes incoming bytes. This function should be called from the `HAL_UART_RxCpltCallback` in your STM32 project.

## Usage

1.  **Initialization:** Call `Bluetooth_Init()` during your system's startup sequence.
2.  **Start Reception:** Call `Bluetooth_StartReceive()` to begin listening for Bluetooth data.
3.  **Periodic Updates:** Call `Bluetooth_Update()` in your main loop to handle connection timeouts.
4.  **Data/Command Polling:** In your main loop, you can check for new commands using `Bluetooth_IsCommandAvailable()` and retrieve them with `Bluetooth_GetCommand()`.
5.  **Controller Data:** To get the most recent controller state, use `Bluetooth_GetController()`.

**Example Implementation in `main.c`:**

```c
#include "robot/bluetooth.h"

// In your main function, after hardware initialization
Bluetooth_Init();
Bluetooth_StartReceive();

while (1) {
    Bluetooth_Update();

    if (Bluetooth_IsCommandAvailable()) {
        BT_Command_t command;
        if (Bluetooth_GetCommand(&command)) {
            if (command.type == BT_CMD_CONTROLLER) {
                // Process controller data from command.data.controller
            } else if (command.type == BT_CMD_EMERGENCY_STOP) {
                // Handle emergency stop
            }
        }
    }

    // Or, to get just the controller data directly:
    ControllerParam controller_data;
    if (Bluetooth_GetController(&controller_data)) {
        // Use the updated controller_data
    }
}

// In your stm32fXXX_it.c or wherever your UART IRQ handlers are
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart->Instance == USART1) { // Or your specific UART instance
        Bluetooth_RxCallback();
    }
}
```
