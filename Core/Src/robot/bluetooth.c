/**
 ******************************************************************************
 * @file    bluetooth.c
 * @brief   Bluetooth communication module implementation
 * @author  RDC Won-Won Team
 * @date    October 2025
 ******************************************************************************
 * @attention
 *
 * This module handles Bluetooth communication via UART for remote control
 * of the robot using a game controller.
 *
 * Protocol Format:
 * Fixed-width space-separated format:
 * LX LY RX RY LT RT A|B|X|Y|LB|RB|BACK|START|XBOX DPAD_UP DN LF RT CON\n
 * Example: "+050 -030 +000 +000 000 000 0000000000 0000 1\n"
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "robot/bluetooth.h"
#include "robot/control.h"
#include "usart.h"
#include "main.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>

/* Private defines -----------------------------------------------------------*/
#define BT_UART_HANDLE          huart1  // UART handle for Bluetooth
#define BT_COMMAND_DELIMITER    '\n'    // Command delimiter

/* Private variables ---------------------------------------------------------*/
static char rx_buffer[BT_RX_BUFFER_SIZE];
static char rx_byte;
static uint16_t rx_index = 0;

static char tx_buffer[BT_TX_BUFFER_SIZE];

static BT_Command_t current_command;
static bool command_available = false;

static ControllerParam current_controller = {0};

static BT_Status_t bt_status = BT_STATUS_DISCONNECTED;
static uint32_t last_receive_time = 0;

/* Private function prototypes -----------------------------------------------*/
static void Bluetooth_ParseCommand(const char* cmd_string);
static bool Bluetooth_ParseControllerData(const char* data_string);
static int16_t Bluetooth_ClampStick(int value);
static uint8_t Bluetooth_ClampTrigger(int value);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize Bluetooth module
 */
void Bluetooth_Init(void) {
    memset(rx_buffer, 0, BT_RX_BUFFER_SIZE);
    memset(tx_buffer, 0, BT_TX_BUFFER_SIZE);
    rx_index = 0;
    command_available = false;
    bt_status = BT_STATUS_DISCONNECTED;
    last_receive_time = HAL_GetTick();
}

/**
 * @brief Start Bluetooth reception
 */
void Bluetooth_StartReceive(void) {
    HAL_UART_Receive_IT(&BT_UART_HANDLE, (uint8_t*)&rx_byte, 1);
}

/**
 * @brief Stop Bluetooth reception
 */
void Bluetooth_StopReceive(void) {
    HAL_UART_AbortReceive_IT(&BT_UART_HANDLE);
}

/**
 * @brief Get the latest controller data
 * @note Does NOT clear the updated flag - allows multiple readers
 */
bool Bluetooth_GetController(ControllerParam* controller) {
    if (controller == NULL || !current_controller.updated) {
        return false;
    }

    // Copy data but DON'T clear flag - multiple functions can read same data
    *controller = current_controller;

    return true;
}

/**
 * @brief Check if a new command is available
 */
bool Bluetooth_IsCommandAvailable(void) {
    return command_available;
}

/**
 * @brief Get the latest command
 */
bool Bluetooth_GetCommand(BT_Command_t* cmd) {
    if (cmd == NULL || !command_available) {
        return false;
    }

    *cmd = current_command;
    command_available = false;

    return true;
}

/**
 * @brief Send a string message via Bluetooth
 */
bool Bluetooth_SendString(const char* message) {
    if (message == NULL) {
        return false;
    }

    uint16_t len = strlen(message);
    if (len > BT_TX_BUFFER_SIZE - 1) {
        len = BT_TX_BUFFER_SIZE - 1;
    }

    // Use blocking transmission to ensure message is sent
    // Timeout of 100ms should be sufficient for short messages
    HAL_StatusTypeDef status = HAL_UART_Transmit(&BT_UART_HANDLE,
                                                   (uint8_t*)message,
                                                   len,
                                                   100);  // 100ms timeout

    return (status == HAL_OK);
}

/**
 * @brief Get Bluetooth connection status
 */
BT_Status_t Bluetooth_GetStatus(void) {
    return bt_status;
}

/**
 * @brief Check if Bluetooth is connected
 */
bool Bluetooth_IsConnected(void) {
    return (bt_status == BT_STATUS_CONNECTED);
}

/**
 * @brief Update Bluetooth status
 */
void Bluetooth_Update(void) {
    uint32_t current_time = HAL_GetTick();

    // Check for timeout
    if (current_time - last_receive_time > BT_TIMEOUT_MS) {
        if (bt_status == BT_STATUS_CONNECTED) {
            bt_status = BT_STATUS_DISCONNECTED;
        }
    }
}

/**
 * @brief UART receive complete callback
 */
void Bluetooth_RxCallback(void) {
    last_receive_time = HAL_GetTick();
    bt_status = BT_STATUS_CONNECTED;

    // Check for command delimiter (newline)
    if (rx_byte == BT_COMMAND_DELIMITER || rx_byte == '\r') {
        if (rx_index > 0) {
            rx_buffer[rx_index] = '\0';  // Null terminate
            Bluetooth_ParseCommand(rx_buffer);
            rx_index = 0;
        }
    } else if (rx_index < BT_RX_BUFFER_SIZE - 1) {
        rx_buffer[rx_index++] = rx_byte;
    } else {
        // Buffer overflow - reset
        rx_index = 0;
    }

    // Restart reception
    HAL_UART_Receive_IT(&BT_UART_HANDLE, (uint8_t*)&rx_byte, 1);
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Parse incoming command string
 * Format: "LX LY RX RY LT RT ABXYLBRBBACKSTARTXBOX DPADUP DPADDN DPADLF DPADRT CON\n"
 * Example: "+050 -030 +000 +000 000 000 0000000000 0 0 0 0 1\n"
 */
static void Bluetooth_ParseCommand(const char* cmd_string) {
    if (cmd_string == NULL || strlen(cmd_string) == 0) {
        return;
    }

    // Try to parse as controller data
    if (Bluetooth_ParseControllerData(cmd_string)) {
        current_command.type = BT_CMD_CONTROLLER;
        current_command.data.controller = current_controller;
        command_available = true;
    }
}

/**
 * @brief Parse controller data from fixed-width format
 * Format: "LX LY RX RY LT RT ABXYLBRBBACKSTARTXBOX DPADUP DPADDN DPADLF DPADRT CON"
 */
static bool Bluetooth_ParseControllerData(const char* data_string) {
    if (data_string == NULL) {
        return false;
    }

    int lx, ly, rx, ry, lt, rt;
    int a, b, x, y, lb, rb, back, start, xbox;
    int dup, ddn, dlf, drt, con;

    // Parse the fixed-width format
    // Format: "+000 +000 +000 +000 000 000 0000000000 0 0 0 0 1"
    int parsed = sscanf(data_string,
        "%d %d %d %d %d %d %1d%1d%1d%1d%1d%1d%1d%1d%1d %d %d %d %d %d",
        &lx, &ly, &rx, &ry, &lt, &rt,
        &a, &b, &x, &y, &lb, &rb, &back, &start, &xbox,
        &dup, &ddn, &dlf, &drt, &con
    );

    if (parsed == 20) {
        // Clear old data flag first
        current_controller.updated = false;
        
        // Clamp and assign stick values
        current_controller.left_stick_x = Bluetooth_ClampStick(lx);
        current_controller.left_stick_y = Bluetooth_ClampStick(ly);
        current_controller.right_stick_x = Bluetooth_ClampStick(rx);
        current_controller.right_stick_y = Bluetooth_ClampStick(ry);

        // Clamp and assign trigger values
        current_controller.left_trigger = Bluetooth_ClampTrigger(lt);
        current_controller.right_trigger = Bluetooth_ClampTrigger(rt);

        // Assign button states (already 0 or 1)
        current_controller.a = (a != 0) ? 1 : 0;
        current_controller.b = (b != 0) ? 1 : 0;
        current_controller.x = (x != 0) ? 1 : 0;
        current_controller.y = (y != 0) ? 1 : 0;
        current_controller.lb = (lb != 0) ? 1 : 0;
        current_controller.rb = (rb != 0) ? 1 : 0;
        current_controller.back = (back != 0) ? 1 : 0;
        current_controller.start = (start != 0) ? 1 : 0;
        current_controller.xbox = (xbox != 0) ? 1 : 0;

        // Assign D-pad states
        current_controller.dpad_up = (dup != 0) ? 1 : 0;
        current_controller.dpad_down = (ddn != 0) ? 1 : 0;
        current_controller.dpad_left = (dlf != 0) ? 1 : 0;
        current_controller.dpad_right = (drt != 0) ? 1 : 0;

        // Assign connection status
        current_controller.connected = (con != 0) ? 1 : 0;
        
        // Set flag LAST to indicate fresh data
        current_controller.updated = true;

        return true;
    }

    return false;
}

/**
 * @brief Clamp stick value to valid range [-100, 100]
 */
static int16_t Bluetooth_ClampStick(int value) {
    if (value > 100) {
        return 100;
    } else if (value < -100) {
        return -100;
    }
    return (int16_t)value;
}

/**
 * @brief Clamp trigger value to valid range [0, 100]
 */
static uint8_t Bluetooth_ClampTrigger(int value) {
    if (value > 100) {
        return 100;
    } else if (value < 0) {
        return 0;
    }
    return (uint8_t)value;
}
