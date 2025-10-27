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
+050 -030 +000 +000 000 000 0000000000 0000 1\n
```

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
