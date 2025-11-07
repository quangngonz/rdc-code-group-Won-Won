/**
 ******************************************************************************
 * @file    autonomous.c
 * @brief   Autonomous control module implementation
 * @author  RDC Won-Won Team
 * @date    November 2025
 ******************************************************************************
 * @attention
 *
 * This module handles autonomous robot control sequences with a state machine.
 * Each state has a specific duration and transitions automatically.
 *
 * AUTONOMOUS SEQUENCE:
 * ====================
 * 1. Move forward (5 seconds)
 * 2. Extend pneumatic arm (0.5 seconds)
 * 3. Rotate 120 degrees (1 second)
 * 4. Retract arm (0.5 seconds)
 * 5. Brief stop (0.5 seconds)
 * 6. Rotate back (1 second)
 * 7. Move forward again (5 seconds)
 * 8. Extend arm (0.5 seconds)
 * 9. Rotate 180 degrees (1 second)
 * 10. Complete and stop
 *
 * Total duration: ~14.5 seconds
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "robot/autonomous.h"
#include "robot/control.h"
#include "robot/drivebase.h"
#include "robot/bluetooth.h"
#include "robot/pneumatic.h"
#include "main.h"

/* Private variables ---------------------------------------------------------*/
static AutoState_t current_state = AUTO_STATE_IDLE;
static uint32_t state_start_time = 0;
static bool running = false;

/* Private function prototypes -----------------------------------------------*/
static void Autonomous_ExecuteState(void);
static void Autonomous_TransitionToState(AutoState_t new_state);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize autonomous control module
 */
void Autonomous_Init(void) {
    current_state = AUTO_STATE_IDLE;
    state_start_time = 0;
    running = false;
}

/**
 * @brief Update autonomous control state machine
 */
void Autonomous_Update(ControllerParam* controller) {
    // Handle button inputs if controller is available
    if (controller != NULL) {
        static uint8_t prev_a_button = 0;
        static uint8_t prev_b_button = 0;
        
        // A button starts autonomous routine
        if (controller->a && !prev_a_button) {
            Autonomous_Start();
        }
        prev_a_button = controller->a;
        
        // B button stops autonomous routine
        if (controller->b && !prev_b_button) {
            Autonomous_Stop();
        }
        prev_b_button = controller->b;
    }

    // Execute current state if running
    if (running) {
        Autonomous_ExecuteState();
    } else {
        // Not running - stay still
        Control_SetMovement(0, 0, 0);
    }
}

/**
 * @brief Start the autonomous sequence
 */
void Autonomous_Start(void) {
    running = true;
    Autonomous_TransitionToState(AUTO_STATE_MOVE_FORWARD_1);
    Bluetooth_SendString("AUTO:STARTED\n");
}

/**
 * @brief Stop the autonomous sequence
 */
void Autonomous_Stop(void) {
    running = false;
    current_state = AUTO_STATE_IDLE;
    Control_SetMovement(0, 0, 0);
    Bluetooth_SendString("AUTO:STOPPED\n");
}

/**
 * @brief Check if autonomous mode is currently running
 */
bool Autonomous_IsRunning(void) {
    return running;
}

/**
 * @brief Get current autonomous state
 */
AutoState_t Autonomous_GetState(void) {
    return current_state;
}

/**
 * @brief Reset autonomous state machine to idle
 */
void Autonomous_Reset(void) {
    current_state = AUTO_STATE_IDLE;
    state_start_time = 0;
    running = false;
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Transition to a new state
 */
static void Autonomous_TransitionToState(AutoState_t new_state) {
    current_state = new_state;
    state_start_time = HAL_GetTick();
}

/**
 * @brief Execute current state logic
 */
static void Autonomous_ExecuteState(void) {
    uint32_t current_time = HAL_GetTick();
    uint32_t elapsed_time = current_time - state_start_time;
    
    switch (current_state) {
        case AUTO_STATE_IDLE:
            // Waiting to start
            Control_SetMovement(0, 0, 0);
            break;
            
        case AUTO_STATE_MOVE_FORWARD_1:
            // Move forward for 5 seconds
            Control_SetMovement(0.5, 0, 0);
            
            if (elapsed_time >= 5000) {  // 5 seconds
                Autonomous_TransitionToState(AUTO_STATE_EXTEND_ARM_1);
                Bluetooth_SendString("AUTO:EXTEND_1\n");
            }
            break;
            
        case AUTO_STATE_EXTEND_ARM_1:
            // Stop and extend arm
            Control_SetMovement(0, 0, 0);
            Pneumatic_Extend();
            
            if (elapsed_time >= 500) {  // 0.5 seconds for arm extension
                Autonomous_TransitionToState(AUTO_STATE_ROTATE_120);
                Bluetooth_SendString("AUTO:ROTATE_120\n");
            }
            break;
            
        case AUTO_STATE_ROTATE_120:
            // Rotate 120 degrees (2.0 rad/s for ~1 second)
            Control_SetMovement(0, 0, 2.0);
            
            if (elapsed_time >= 1000) {  // 1 second rotation
                Autonomous_TransitionToState(AUTO_STATE_RETRACT_ARM_1);
                Bluetooth_SendString("AUTO:RETRACT_1\n");
            }
            break;
            
        case AUTO_STATE_RETRACT_ARM_1:
            // Stop and retract arm
            Control_SetMovement(0, 0, 0);
            Pneumatic_Retract();
            
            if (elapsed_time >= 500) {  // 0.5 seconds for arm retraction
                Autonomous_TransitionToState(AUTO_STATE_STOP_1);
                Bluetooth_SendString("AUTO:STOP_1\n");
            }
            break;
            
        case AUTO_STATE_STOP_1:
            // Brief stop
            Control_SetMovement(0, 0, 0);
            
            if (elapsed_time >= 500) {  // 0.5 second pause
                Autonomous_TransitionToState(AUTO_STATE_ROTATE_BACK);
                Bluetooth_SendString("AUTO:ROTATE_BACK\n");
            }
            break;
            
        case AUTO_STATE_ROTATE_BACK:
            // Rotate back to original position
            Control_SetMovement(0, 0, -2.0);
            
            if (elapsed_time >= 1000) {  // 1 second rotation back
                Autonomous_TransitionToState(AUTO_STATE_MOVE_FORWARD_2);
                Bluetooth_SendString("AUTO:FORWARD_2\n");
            }
            break;
            
        case AUTO_STATE_MOVE_FORWARD_2:
            // Move forward to next block for 5 seconds
            Control_SetMovement(0.5, 0, 0);
            
            if (elapsed_time >= 5000) {  // 5 seconds
                Autonomous_TransitionToState(AUTO_STATE_EXTEND_ARM_2);
                Bluetooth_SendString("AUTO:EXTEND_2\n");
            }
            break;
            
        case AUTO_STATE_EXTEND_ARM_2:
            // Stop and extend arm
            Control_SetMovement(0, 0, 0);
            Pneumatic_Extend();
            
            if (elapsed_time >= 500) {  // 0.5 seconds for arm extension
                Autonomous_TransitionToState(AUTO_STATE_ROTATE_180);
                Bluetooth_SendString("AUTO:ROTATE_180\n");
            }
            break;
            
        case AUTO_STATE_ROTATE_180:
            // Rotate 180 degrees (3.14 rad/s)
            Control_SetMovement(0, 0, 3.14);
            
            if (elapsed_time >= 1000) {  // 1 second for 180 degree rotation
                Autonomous_TransitionToState(AUTO_STATE_COMPLETE);
                Bluetooth_SendString("AUTO:COMPLETE\n");
            }
            break;
            
        case AUTO_STATE_COMPLETE:
            // Sequence complete - stop
            Control_SetMovement(0, 0, 0);
            running = false;
            current_state = AUTO_STATE_IDLE;
            break;
            
        default:
            // Unknown state - reset
            Autonomous_Stop();
            break;
    }
}
