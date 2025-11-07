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
 *    - LB + RB buttons pressed together (rising edge): TOGGLE E-STOP on/off
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
#include "robot/tof_sensor.h"
#include "robot/pneumatic.h"
#include "robot/autonomous.h"
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
static uint8_t prev_lb_rb_pressed = 0;  // Track LB+RB combo for E-STOP
static uint8_t prev_start_button = 0;
static uint8_t prev_x_button = 0;       // Track X button for pneumatic toggle
// BTN_1 edge tracking for motor test (rising edge starts, falling edge stops)
static uint8_t prev_btn1 = 0;
static uint8_t btn1_running = 0;

// ToF sensor
static ToF_Sensor_t tof_sensor;

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
    prev_lb_rb_pressed = 0;
    prev_start_button = 0;
    prev_x_button = 0;

    memset(&current_movement, 0, sizeof(Movement_t));

    // Initialize subsystems
    DriveBase_Init();
    Bluetooth_Init();
//    Sensors_Init();
//    Mechanisms_Init();

    // Initialize ToF sensor
    HAL_GPIO_WritePin(GPIOA, TOF_XSHUT_Pin, GPIO_PIN_SET);
    ToF_Sensor_Init(&tof_sensor, 0x52, GPIOA, TOF_XSHUT_Pin);
    ToF_Sensor_Start(&tof_sensor);

    // Initialize autonomous control
    Autonomous_Init();

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

    // Update ToF sensor reading
    ToF_Sensor_GetDistance(&tof_sensor);

    // BTN_1 motor test: start on rising edge, stop on falling edge
    uint8_t btn1 = btn_read(BTN1) ? 1 : 0;

    // Rising edge -> start motor test
    if (btn1 && !prev_btn1) {
        btn1_running = 1;
        Bluetooth_SendString("BTN1:TEST_START\n");
    }

    // Falling edge -> stop motor test (set currents to zero)
    if (!btn1 && prev_btn1) {
        btn1_running = 0;
        // Use direct current control to stop motors
        Control_SetDirectCurrent(0.0f, 0.0f, 0.0f);
        DriveBase_ApplyDirectCurrents();
        Bluetooth_SendString("BTN1:TEST_STOP\n");
        // update prev_btn1 and continue with normal processing
        prev_btn1 = btn1;
    }

    // If motor test is running, maintain test current (30% max) and skip normal control
    if (btn1_running) {
        // left_x = 0 (strafe), left_y = 0.30 (forward 30% of max current), theta = 0
        Control_SetDirectCurrent(0.0f, 0.30f, 0.0f);
        DriveBase_ApplyDirectCurrents();
        prev_btn1 = btn1;
        return;
    }

    // Update previous button state for next iteration
    prev_btn1 = btn1;

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
            // Manual: process controller input (uses direct current control)
            Control_ProcessManualMode();
            // Don't call DriveBase_Update() here - manual mode handles motor updates directly
            return;  // Early return to skip DriveBase_Update()

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

    // Update drive motors (with PID control for non-manual modes)
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

    // Enable motors
    DriveBase_Enable();

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
 * @brief Get ToF sensor distance reading
 * @return Distance in millimeters
 */
uint16_t Control_GetToFDistance(void) {
    return tof_sensor.distance;
}

/**
 * @brief Apply direct motor current control without PID
 * Passes joystick inputs to drivebase for direct current control
 * This bypasses the PID controller and sends current commands directly to motors
 */
void Control_SetDirectCurrent(float left_x, float left_y, float theta) {
    // Clamp input values to [-1.0, 1.0]
    if (left_x > 1.0f) left_x = 1.0f;
    if (left_x < -1.0f) left_x = -1.0f;
    if (left_y > 1.0f) left_y = 1.0f;
    if (left_y < -1.0f) left_y = -1.0f;
    if (theta > 1.0f) theta = 1.0f;
    if (theta < -1.0f) theta = -1.0f;

    // Enable motors if not already enabled
    if (!motors_enabled) {
        Control_EnableMotors();
    }

    // Map joystick inputs to robot velocity components
    float vx = left_y;   // Forward/backward
    float vy = left_x;   // Left/right strafe
    float omega = theta; // Rotation

    // Pass to drivebase for direct current control
    DriveBase_SetDirectCurrent(vx, vy, omega);
}



/* Private functions ---------------------------------------------------------*/

/**
 * @brief Check controller buttons for mode changes
 * - LB + RB (both pressed, rising edge): Toggle E-STOP
 * - Start button (rising edge): Toggle between MANUAL and AUTO (if not in E-STOP)
 */
static void Control_CheckModeButtons(ControllerParam* controller) {
    if (controller == NULL) {
        return;
    }

    // Check LB+RB combo for E-STOP toggle (both must be pressed)
    uint8_t lb_rb_pressed = (controller->lb && controller->rb) ? 1 : 0;
    if (lb_rb_pressed && !prev_lb_rb_pressed) {
        // Rising edge detected - toggle E-STOP
        Control_EmergencyStop();
    }
    prev_lb_rb_pressed = lb_rb_pressed;

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
 * 
 * =============================================================================
 * CONTROL MODE SELECTION:
 * =============================================================================
 * 
 * This implementation uses DIRECT CURRENT CONTROL (no PID).
 * The joystick inputs are directly mapped to motor currents.
 * 
 * To switch back to PID velocity control, replace the code below with:
 * 
 *   float vx = controller.left_stick_y / 100.0f;  // Forward/backward
 *   float vy = controller.left_stick_x / 100.0f;  // Left/right strafe
 *   float omega = controller.right_stick_x / 100.0f;  // Rotation
 *   Control_SetMovement(vx, vy, omega);
 *   Control_ApplyMovement(current_movement);
 * 
 * =============================================================================
 */
static void Control_ProcessManualMode(void) {
    ControllerParam controller;
    if (Bluetooth_GetController(&controller)) {
        // Convert joystick values (-100 to 100) to normalized values (-1.0 to 1.0)
        float left_x = controller.left_stick_x / 100.0f;  // Left/right strafe
        float left_y = controller.left_stick_y / 100.0f;  // Forward/backward
        float theta = controller.right_stick_x / 100.0f;  // Rotation

        // DIRECT CURRENT CONTROL (bypasses PID - trusts your drivers!)
        Control_SetDirectCurrent(left_x, left_y, theta);
        
        // Apply the currents directly to motors
        DriveBase_ApplyDirectCurrents();

        // Pneumatic arm control with edge detection
        // A button: Extend arm (on button press)
        if (controller.a) {
//            Pneumatic_Extend();
        	HAL_GPIO_WritePin(GPIOC, PNEU_Pin, GPIO_PIN_SET);
        }
        
        // B button: Retract arm (on button press)
        if (controller.b) {
//            Pneumatic_Retract();
        	HAL_GPIO_WritePin(GPIOC, PNEU_Pin, GPIO_PIN_RESET);
        }
        
        // X button: Toggle arm state (on button press)
        if (controller.x && !prev_x_button) {
            Pneumatic_Toggle();
        }
        prev_x_button = controller.x;

        // Get and display pneumatic state
        GPIO_PinState pneu_state = Pneumatic_GetState();
        if (pneu_state == GPIO_PIN_SET) {
            tft_prints(0, 7, "Pneu: EXTENDED");
        } else {
            tft_prints(0, 7, "Pneu: RETRACTED");
        }
        
    } else {
        // No controller data - stop all motors
        Control_SetDirectCurrent(0, 0, 0);
        DriveBase_ApplyDirectCurrents();
    }
}

/**
 * @brief Process autonomous control mode
 * Delegates to the autonomous module
 */
static void Control_ProcessAutoMode(void) {
    ControllerParam controller;
    ControllerParam* controller_ptr = NULL;
    
    // Get controller data if available
    if (Bluetooth_GetController(&controller)) {
        controller_ptr = &controller;
    }
    
    // Update autonomous control (handles button detection and state machine)
    Autonomous_Update(controller_ptr);
    
    // Apply the movement that autonomous module set
    Control_ApplyMovement(current_movement);
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
