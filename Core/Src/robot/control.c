/**
 ******************************************************************************
 * @file    control.c
 * @brief   Robot control module implementation
 * @author  RDC Won-Won Team
 * @date    October 2025
 ******************************************************************************
 * @attention
 *
 * This module manages the robot's control system with 3-wheel omni-drive
 * kinematics.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "robot/control.h"
#include "robot/drivebase.h"
#include "robot/bluetooth.h"
//#include "robot/sensors.h"
//#include "robot/mechanisms.h"
#include "main.h"
#include <math.h>
#include <string.h>

/* Private defines -----------------------------------------------------------*/
#define SQRT3               1.732050808f
#define DEG_TO_RAD          0.017453293f

/* Private variables ---------------------------------------------------------*/
static ControlMode_t current_mode = CONTROL_MODE_IDLE;
static Movement_t current_movement = {0, 0, 0};
static bool motors_enabled = false;
static bool emergency_stop_active = false;

/* Private function prototypes -----------------------------------------------*/
static void Control_ProcessManualMode(void);
static void Control_ProcessAutoMode(void);
static void Control_ApplyMovement(Movement_t movement);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize control module
 */
void Control_Init(void) {
    current_mode = CONTROL_MODE_IDLE;
    motors_enabled = false;
    emergency_stop_active = false;

    memset(&current_movement, 0, sizeof(Movement_t));

    // Initialize subsystems
    DriveBase_Init();
    Bluetooth_Init();
//    Sensors_Init();
//    Mechanisms_Init();

    // Start Bluetooth reception
    Bluetooth_StartReceive();
}

/**
 * @brief Update control loop
 */
void Control_Update(void) {
    // Update subsystems
    Bluetooth_Update();
//    Sensors_Update();

    // Check for Bluetooth commands
    BT_Command_t cmd;
    if (Bluetooth_GetCommand(&cmd)) {
        switch (cmd.type) {
            case BT_CMD_NONE:
                break;
            case BT_CMD_CONTROLLER:
                if (current_mode == CONTROL_MODE_MANUAL)
                {
                    // Process controller input only in manual mode
                    Control_ProcessManualMode();
                }
                break;
            case BT_CMD_EMERGENCY_STOP:
                Control_EmergencyStop();
                break;

            default:
                break;
        }
    }

    // Process current mode
    if (emergency_stop_active) {
        // Emergency stop - do nothing, motors are disabled
        DriveBase_Disable();
        return;
    }

    switch (current_mode) {
        case CONTROL_MODE_MANUAL:
            Control_ProcessManualMode();
            break;

        case CONTROL_MODE_AUTO:
            Control_ProcessAutoMode();
            break;

        case CONTROL_MODE_IDLE:
        default:
            // Idle mode - stop movement but don't disable motors
            Control_SetMovement(0, 0, 0);
            Control_ApplyMovement(current_movement);
            break;
    }

    // Update drive motors
    DriveBase_Update();
}

/**
 * @brief Set robot control mode
 */
bool Control_SetMode(ControlMode_t mode) {
    if (emergency_stop_active && mode != CONTROL_MODE_IDLE) {
        // Cannot change mode while in emergency stop
        return false;
    }

    current_mode = mode;

    // Send mode change confirmation via Bluetooth (non-blocking)
    // Commented out to prevent blocking the main loop
    if (mode == CONTROL_MODE_AUTO) {
        Bluetooth_SendString("MODE:AUTO\n");
    } else if (mode == CONTROL_MODE_MANUAL) {
        Bluetooth_SendString("MODE:MANUAL\n");
    }

    return true;
}

/**
 * @brief Get current control mode
 */
ControlMode_t Control_GetMode(void) {
    return current_mode;
}

/**
 * @brief Emergency stop
 */
void Control_EmergencyStop(void) {
    emergency_stop_active = true;
    current_mode = CONTROL_MODE_EMERGENCY_STOP;

    // Stop all movement
    Control_SetMovement(0, 0, 0);
    Control_ApplyMovement(current_movement);

    // Disable motors
    DriveBase_Disable();

    // Send confirmation (non-blocking, commented out to prevent blocking)
    Bluetooth_SendString("ESTOP:ACTIVE\n");
}

/**
 * @brief Release emergency stop
 */
void Control_ReleaseEmergencyStop(void) {
    emergency_stop_active = false;
    current_mode = CONTROL_MODE_IDLE;

    // Commented out to prevent blocking
     Bluetooth_SendString("ESTOP:RELEASED\n");
}

/**
 * @brief Set movement command
 */
void Control_SetMovement(float vx, float vy, float omega) {
    // Clamp values to [-1.0, 1.0]
    if (vx > 1.0f) vx = 1.0f;
    if (vx < -1.0f) vx = -1.0f;
    if (vy > 1.0f) vy = 1.0f;
    if (vy < -1.0f) vy = -1.0f;
    if (omega > 1.0f) omega = 1.0f;
    if (omega < -1.0f) omega = -1.0f;

    current_movement.vx = vx;
    current_movement.vy = vy;
    current_movement.omega = omega;
}

/**
 * @brief Get robot status
 */
RobotStatus_t Control_GetStatus(void) {
    RobotStatus_t status;

    status.mode = current_mode;
    status.motors_enabled = motors_enabled;
    status.bluetooth_connected = Bluetooth_IsConnected();
    status.current_movement = current_movement;
    status.uptime_ms = HAL_GetTick();

    return status;
}

/**
 * @brief Enable robot motors
 */
void Control_EnableMotors(void) {
    motors_enabled = true;
    DriveBase_Enable();
}

/**
 * @brief Disable robot motors
 */
void Control_DisableMotors(void) {
    motors_enabled = false;
    DriveBase_Disable();
}

/**
 * @brief Calculate motor velocities from movement command
 *
 */
void Control_CalculateMotorVelocities(Movement_t movement, int16_t motor_vel[3]) {
	// TODO: @mech @Hoang do this
}

/**
 * @brief Calculate robot movement from motor velocities
 *
 * Forward kinematics for 3-wheel omni-drive
 */
void Control_CalculateMovement(int16_t motor_vel[3], Movement_t* movement) {

	// TODO: @mech @Hoang do this

}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Process manual control mode
 */
static void Control_ProcessManualMode(void) {
    ControllerParam controller_2;
    if (Bluetooth_GetController(&controller_2)) {
        // Convert joystick values (-100 to 100) to normalized values (-1.0 to 1.0)
        float vx = controller_2.left_stick_x / 100.0f;
        float vy = controller_2.left_stick_y / 100.0f;
        float omega = controller_2.right_stick_x / 100.0f;

        // Set movement
        Control_SetMovement(vx, vy, omega);
    }
       
    // Apply movement to motors
    Control_ApplyMovement(current_movement);
}

/**
 * @brief Process autonomous control mode
 */
static void Control_ProcessAutoMode(void) {
    // TODO: Implement autonomous control logic
    // Example: Follow a line, avoid obstacles, etc.

    // For now, just stop
    Control_SetMovement(0.2, 0.2, 0);
    Control_ApplyMovement(current_movement);
}

/**
 * @brief Apply movement command to motors
 */
static void Control_ApplyMovement(Movement_t movement) {
    if (!motors_enabled) {
        Control_EnableMotors();
    }

    // Calculate motor velocities
    int16_t motor_vel[3];
    Control_CalculateMotorVelocities(movement, motor_vel);

    // Set motor velocities
    DriveBase_SetMotorVelocity(DRIVE_MOTOR_RIGHT_FRONT, motor_vel[0]);
    DriveBase_SetMotorVelocity(DRIVE_MOTOR_REAR, motor_vel[1]);
    DriveBase_SetMotorVelocity(DRIVE_MOTOR_LEFT_FRONT, motor_vel[2]);
}

