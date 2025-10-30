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
 * CONTROL LOGIC:
 * ==============
 * 1. E-STOP (Emergency Stop):
 *    - Xbox button (rising edge): TOGGLE E-STOP on/off
 *    - When active: motors disabled, all other controls ignored
 *
 * 2. Mode Switching (when not in E-STOP):
 *    - Start button (rising edge): Toggle between MANUAL and AUTO modes
 *
 * 3. Three Operating Modes:
 *    - IDLE: Motors enabled but stopped (default after E-STOP release)
 *    - MANUAL: Controller directly controls movement (left stick + right stick X for rotation)
 *    - AUTO: Autonomous control (A button starts, B button stops autonomous routine)
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

/* Private variables ---------------------------------------------------------*/
static ControlMode_t current_mode = CONTROL_MODE_IDLE;
static Movement_t current_movement = {0, 0, 0};
static bool motors_enabled = false;
static bool emergency_stop_active = false;

// Button state tracking for edge detection
static uint8_t prev_xbox_button = 0;
static uint8_t prev_start_button = 0;

/* Private function prototypes -----------------------------------------------*/
static void Control_ProcessManualMode(void);
static void Control_ProcessAutoMode(void);
static void Control_ApplyMovement(Movement_t movement);
static void Control_CheckModeButtons(ControllerParam* controller);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize control module
 */
void Control_Init(void) {
    current_mode = CONTROL_MODE_IDLE;
    motors_enabled = false;
    emergency_stop_active = false;
    prev_xbox_button = 0;
    prev_start_button = 0;

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
 * Main state machine: checks mode and executes appropriate control
 */
void Control_Update(void) {
    // Update subsystems
    Bluetooth_Update();
//    Sensors_Update();

    // Get controller data if available
    ControllerParam controller;
    if (Bluetooth_GetController(&controller)) {
        // Check for mode change buttons (Xbox button for E-STOP toggle)
        Control_CheckModeButtons(&controller);
    }

    // ======== MAIN STATE MACHINE ========
    // Handle E-STOP state first
    if (emergency_stop_active) {
        // E-STOP active - motors disabled, do nothing
        DriveBase_Disable();
        DriveBase_Update();
        return;
    }

    // Process based on current mode
    switch (current_mode) {
        case CONTROL_MODE_IDLE:
            // Idle: motors stopped but enabled
            Control_SetMovement(0, 0, 0);
            Control_ApplyMovement(current_movement);
            break;

        case CONTROL_MODE_MANUAL:
            // Manual: process controller input
            Control_ProcessManualMode();
            break;

        case CONTROL_MODE_AUTO:
            // Auto: run autonomous logic
            Control_ProcessAutoMode();
            break;

        case CONTROL_MODE_EMERGENCY_STOP:
            // Should not reach here (handled above)
            DriveBase_Disable();
            break;

        default:
            // Unknown mode - go to idle
            current_mode = CONTROL_MODE_IDLE;
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

    // Send mode change confirmation via Bluetooth
    if (mode == CONTROL_MODE_AUTO) {
        Bluetooth_SendString("MODE:AUTO  \n");
    } else if (mode == CONTROL_MODE_MANUAL) {
        Bluetooth_SendString("MODE:MANUAL\n");
    } else if (mode == CONTROL_MODE_IDLE) {
        Bluetooth_SendString("MODE:IDLE  \n");
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
 * @brief Emergency stop - TOGGLE functionality
 */
void Control_EmergencyStop(void) {
    if (emergency_stop_active) {
        // Already in E-STOP, release it
        Control_ReleaseEmergencyStop();
    } else {
        // Activate E-STOP
        emergency_stop_active = true;
        current_mode = CONTROL_MODE_EMERGENCY_STOP;

        // Stop all movement
        Control_SetMovement(0, 0, 0);
        Control_ApplyMovement(current_movement);

        // Disable motors
        DriveBase_Disable();

        Bluetooth_SendString("ESTOP:ACTIVE\n");
    }
}

/**
 * @brief Release emergency stop
 */
void Control_ReleaseEmergencyStop(void) {
    emergency_stop_active = false;
    current_mode = CONTROL_MODE_IDLE;

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



/* Private functions ---------------------------------------------------------*/

/**
 * @brief Check controller buttons for mode changes
 * - Xbox button (rising edge): Toggle E-STOP
 * - Start button (rising edge): Toggle between MANUAL and AUTO (if not in E-STOP)
 */
static void Control_CheckModeButtons(ControllerParam* controller) {
    if (controller == NULL) {
        return;
    }

    // Check Xbox button for E-STOP toggle (rising edge)
    if (controller->xbox && !prev_xbox_button) {
        // Rising edge detected - toggle E-STOP
        Control_EmergencyStop();
    }
    prev_xbox_button = controller->xbox;

    // Check Start button for mode switching (only if not in E-STOP)
    if (!emergency_stop_active) {
        if (controller->start && !prev_start_button) {
            // Rising edge detected - toggle between MANUAL and AUTO
            if (current_mode == CONTROL_MODE_MANUAL) {
                Control_SetMode(CONTROL_MODE_AUTO);
            } else if (current_mode == CONTROL_MODE_AUTO || current_mode == CONTROL_MODE_IDLE) {
                Control_SetMode(CONTROL_MODE_MANUAL);
            }
        }
    }
    prev_start_button = controller->start;
}

/**
 * @brief Process manual control mode
 */
static void Control_ProcessManualMode(void) {
    ControllerParam controller;
    if (Bluetooth_GetController(&controller)) {
        // Convert joystick values (-100 to 100) to normalized values (-1.0 to 1.0)
        float vx = controller.left_stick_y / 100.0f;  // Forward/backward
        float vy = controller.left_stick_x / 100.0f;  // Left/right strafe
        float omega = controller.right_stick_x / 100.0f;  // Rotation

        // Set movement
        Control_SetMovement(vx, vy, omega);

        // Get controller buttons data for mechanism control
        if (controller.a) {
            // Mechanisms_ActivateA();
        }
        if (controller.b) {
            // Mechanisms_ActivateB();
        }
        
    } else {
        // No controller data - stop
        Control_SetMovement(0, 0, 0);
    }
       
    // Apply movement to motors
    Control_ApplyMovement(current_movement);
}

/**
 * @brief Process autonomous control mode
 * Waits for A button to start autonomous routine
 */
static void Control_ProcessAutoMode(void) {
    static bool auto_running = false;
    
    ControllerParam controller;
    if (Bluetooth_GetController(&controller)) {
        // A button starts/stops autonomous routine
        if (controller.a) {
            auto_running = true;
        }
        // B button stops autonomous routine
        if (controller.b) {
            auto_running = false;
        }
    }

    if (auto_running) {
        // TODO: Implement autonomous control logic
        // Example: Follow a line, avoid obstacles, etc.
        
        // For now, just move in a pattern
        Control_SetMovement(0.2, 0.2, 0);
        Control_ApplyMovement(current_movement);
    } else {
        // Auto mode but not running - stay still
        Control_SetMovement(0, 0, 0);
        Control_ApplyMovement(current_movement);
    }
}

/**
 * @brief Apply movement command to motors
 */
static void Control_ApplyMovement(Movement_t movement) {
    if (!motors_enabled) {
        Control_EnableMotors();
    }

    // DriveBase handles inverse kinematics and sets motor velocities
    DriveBase_SetVelocity(movement.vx, movement.vy, movement.omega);
}
