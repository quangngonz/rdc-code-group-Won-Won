/**
 ******************************************************************************
 * @file    bluetooth.h
 * @brief   Bluetooth communication module header file
 * @author  RDC Won-Won Team
 * @date    October 2025
 ******************************************************************************
 * @attention
 *
 * This module handles Bluetooth communication via UART for remote control
 * of the robot using a game controller (Xbox-style).
 *
 * Protocol Format:
 * Fixed-width space-separated format (20 values total):
 * "LX LY RX RY LT RT ABXYLBRBBACKSTARTXBOX DPADUP DPADDN DPADLF DPADRT CON\n"
 *
 * Where:
 * - LX, LY, RX, RY: Left/Right stick axes (signed, -100 to +100)
 * - LT, RT: Left/Right triggers (unsigned, 0 to 100)
 * - A, B, X, Y, LB, RB, BACK, START, XBOX: Buttons (0 or 1, packed together)
 * - DPADUP, DPADDN, DPADLF, DPADRT: D-pad buttons (0 or 1)
 * - CON: Connection status (0 or 1)
 *
 * Example: "+050 -030 +000 +000 000 000 0000000000 0 0 0 0 1\n"
 *
 * Emergency Stop: "ESTOP\n"
 *
 ******************************************************************************
 */

#ifndef INC_ROBOT_BLUETOOTH_H_
#define INC_ROBOT_BLUETOOTH_H_

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Controller parameters structure
 * Represents Xbox/Game controller state
 */
typedef struct {
    // Joystick axes: range -100 to 100
    int16_t left_stick_x;
    int16_t left_stick_y;
    int16_t right_stick_x;
    int16_t right_stick_y;

    // Triggers: range 0-100
    uint8_t left_trigger;
    uint8_t right_trigger;

    // Digital buttons: 0 (released) or 1 (pressed)
    uint8_t a;
    uint8_t b;
    uint8_t x;
    uint8_t y;
    uint8_t lb;
    uint8_t rb;
    uint8_t back;
    uint8_t start;
    uint8_t xbox;

    // D-Pad
    uint8_t dpad_up;
    uint8_t dpad_down;
    uint8_t dpad_left;
    uint8_t dpad_right;

    // Connection status
    uint8_t connected;  // 1 if connected, 0 if disconnected
    bool updated;       // Flag indicating new data received
} ControllerParam;

/**
 * @brief Bluetooth command type enumeration
 */
typedef enum {
    BT_CMD_NONE = 0,
    BT_CMD_CONTROLLER,
    BT_CMD_EMERGENCY_STOP
} BT_CommandType_t;

/**
 * @brief Bluetooth command structure
 */
typedef struct {
    BT_CommandType_t type;
    union {
        ControllerParam controller;
    } data;
} BT_Command_t;

/**
 * @brief Bluetooth status enumeration
 */
typedef enum {
    BT_STATUS_DISCONNECTED = 0,
    BT_STATUS_CONNECTED,
    BT_STATUS_ERROR
} BT_Status_t;

/* Exported constants --------------------------------------------------------*/
#define BT_RX_BUFFER_SIZE   64   // Receive buffer size
#define BT_TX_BUFFER_SIZE   128  // Transmit buffer size
#define BT_TIMEOUT_MS       5000 // Communication timeout in ms

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize Bluetooth module
 * Must be called before using any other Bluetooth functions
 */
void Bluetooth_Init(void);

/**
 * @brief Start Bluetooth reception
 * Enables UART interrupt for receiving data
 */
void Bluetooth_StartReceive(void);

/**
 * @brief Stop Bluetooth reception
 */
void Bluetooth_StopReceive(void);

/**
 * @brief Get the latest controller data
 * @param controller: Pointer to controller structure to fill
 * @return true if valid data available, false otherwise
 */
bool Bluetooth_GetController(ControllerParam* controller);

/**
 * @brief Check if a new command is available
 * @return true if command available, false otherwise
 */
bool Bluetooth_IsCommandAvailable(void);

/**
 * @brief Get the latest command
 * @param cmd: Pointer to command structure to fill
 * @return true if command retrieved, false otherwise
 */
bool Bluetooth_GetCommand(BT_Command_t* cmd);

/**
 * @brief Send a string message via Bluetooth
 * @param message: Null-terminated string to send
 * @return true if sent successfully, false otherwise
 */
bool Bluetooth_SendString(const char* message);

/**
 * @brief Get Bluetooth connection status
 * @return Current Bluetooth status
 */
BT_Status_t Bluetooth_GetStatus(void);

/**
 * @brief Check if Bluetooth is connected
 * @return true if connected, false otherwise
 */
bool Bluetooth_IsConnected(void);

/**
 * @brief Update Bluetooth status (call periodically)
 * Checks for timeout and updates connection status
 */
void Bluetooth_Update(void);

/**
 * @brief UART receive complete callback (internal use)
 * This function should be called from HAL_UART_RxCpltCallback
 */
void Bluetooth_RxCallback(void);

#ifdef __cplusplus
}
#endif

#endif /* INC_ROBOT_BLUETOOTH_H_ */
