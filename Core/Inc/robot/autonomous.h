/**
 ******************************************************************************
 * @file    autonomous.h
 * @brief   Autonomous control module header
 * @author  RDC Won-Won Team
 * @date    November 2025
 ******************************************************************************
 * @attention
 *
 * This module handles autonomous robot control sequences with a state machine.
 * Separated from control.c for better code organization.
 *
 ******************************************************************************
 */

#ifndef AUTONOMOUS_H
#define AUTONOMOUS_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <stdbool.h>
#include "robot/bluetooth.h"

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Autonomous state machine states
 */
typedef enum {
    AUTO_STATE_IDLE = 0,
    AUTO_STATE_MOVE_FORWARD_1,
    AUTO_STATE_EXTEND_ARM_1,
    AUTO_STATE_ROTATE_120,
    AUTO_STATE_RETRACT_ARM_1,
    AUTO_STATE_STOP_1,
    AUTO_STATE_ROTATE_BACK,
    AUTO_STATE_MOVE_FORWARD_2,
    AUTO_STATE_EXTEND_ARM_2,
    AUTO_STATE_ROTATE_180,
    AUTO_STATE_COMPLETE
} AutoState_t;

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize autonomous control module
 */
void Autonomous_Init(void);

/**
 * @brief Update autonomous control state machine
 * Should be called regularly from the main control loop
 * @param controller Pointer to controller parameters (can be NULL if no controller data)
 */
void Autonomous_Update(ControllerParam* controller);

/**
 * @brief Start the autonomous sequence
 */
void Autonomous_Start(void);

/**
 * @brief Stop the autonomous sequence
 */
void Autonomous_Stop(void);

/**
 * @brief Check if autonomous mode is currently running
 * @return true if running, false otherwise
 */
bool Autonomous_IsRunning(void);

/**
 * @brief Get current autonomous state
 * @return Current state of the autonomous state machine
 */
AutoState_t Autonomous_GetState(void);

/**
 * @brief Reset autonomous state machine to idle
 */
void Autonomous_Reset(void);

#ifdef __cplusplus
}
#endif

#endif /* AUTONOMOUS_H */
