/**
 ******************************************************************************
 * @file    control.h
 * @brief   Robot control module header file
 * @author  RDC Won-Won Team
 * @date    October 2025
 ******************************************************************************
 * @attention
 *
 * This module manages the robot's control system, including:
 * - Mode switching between autonomous and manual (Bluetooth) control
 * - 3-wheel omni-drive kinematics for movement control
 * - High-level robot state management
 *
 ******************************************************************************
 */

#ifndef INC_ROBOT_CONTROL_H_
#define INC_ROBOT_CONTROL_H_


#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Robot control mode enumeration
 */
typedef enum {
    CONTROL_MODE_IDLE = 0,      // Robot idle (motors disabled)
    CONTROL_MODE_MANUAL,        // Manual control via Bluetooth
    CONTROL_MODE_AUTO,          // Autonomous control
    CONTROL_MODE_EMERGENCY_STOP // Emergency stop mode
} ControlMode_t;

/**
 * @brief Robot movement command structure
 */
typedef struct {
    float vx;       // Forward/backward velocity [-1.0 to 1.0]
    float vy;       // Left/right velocity [-1.0 to 1.0]
    float omega;    // Rotational velocity [-1.0 to 1.0]
} Movement_t;

/**
 * @brief Robot status structure
 */
typedef struct {
    ControlMode_t mode;
    bool motors_enabled;
    bool bluetooth_connected;
    Movement_t current_movement;
    uint32_t uptime_ms;
} RobotStatus_t;

/* Exported constants --------------------------------------------------------*/
#define CONTROL_MAX_VELOCITY_RPM    3000    // Maximum motor velocity
#define CONTROL_DEADZONE            5       // Joystick deadzone (%)

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize control module
 * Sets up the control system and initializes all subsystems
 */
void Control_Init(void);

/**
 * @brief Update control loop
 * Should be called periodically (e.g., every 10ms)
 * Handles mode switching, command processing, and motor control
 */
void Control_Update(void);

/**
 * @brief Set robot control mode
 * @param mode: Target control mode
 * @return true if mode changed successfully, false otherwise
 */
bool Control_SetMode(ControlMode_t mode);

/**
 * @brief Get current control mode
 * @return Current control mode
 */
ControlMode_t Control_GetMode(void);

/**
 * @brief Emergency stop - immediately stops all motors
 */
void Control_EmergencyStop(void);

/**
 * @brief Release emergency stop and return to idle mode
 */
void Control_ReleaseEmergencyStop(void);

/**
 * @brief Set movement command (normalized values)
 * @param vx: Forward/backward [-1.0 to 1.0]
 * @param vy: Left/right [-1.0 to 1.0]
 * @param omega: Rotation [-1.0 to 1.0]
 */
void Control_SetMovement(float vx, float vy, float omega);

/**
 * @brief Get robot status
 * @return Robot status structure
 */
RobotStatus_t Control_GetStatus(void);

/**
 * @brief Enable robot motors
 */
void Control_EnableMotors(void);

/**
 * @brief Disable robot motors
 */
void Control_DisableMotors(void);

#ifdef __cplusplus
}
#endif

#endif /* INC_ROBOT_CONTROL_H_ */
