/**
 ******************************************************************************
 * @file    can_protocol.c
 * @brief   CAN bus protocol wrapper implementation
 * @author  RDC Won-Won Team
 * @date    October 2025
 ******************************************************************************
 * @attention
 *
 * This module provides a high-level wrapper around the CAN bus driver.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "robot/can_protocol.h"
#include "can.h"

/* Private variables ---------------------------------------------------------*/
static uint32_t motor_last_update[MAX_NUM_OF_MOTORS] = {0};

/* Private defines -----------------------------------------------------------*/
#define MOTOR_TIMEOUT_MS  100  // Motor feedback timeout

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize CAN bus protocol
 */
void CAN_Protocol_Init(void) {
    can_init();

    // Clear last update times
    for (uint8_t i = 0; i < MAX_NUM_OF_MOTORS; i++) {
        motor_last_update[i] = 0;
    }
}

/**
 * @brief Stop CAN bus communication
 */
void CAN_Protocol_Stop(void) {

}

/**
 * @brief Update CAN bus communication
 */
void CAN_Protocol_Update(void) {
    can_ctrl_loop();
}

/**
 * @brief Send motor current command
 */
void CAN_Protocol_SetMotorCurrent(Motor motor, int16_t current) {
    if (motor >= MAX_NUM_OF_MOTORS) {
        return;
    }

    set_motor_current(motor, current);
}

/**
 * @brief Get motor feedback data
 */
MotorStats CAN_Protocol_GetMotorFeedback(Motor motor) {
    MotorStats feedback = {0};

    if (motor < MAX_NUM_OF_MOTORS) {
        feedback = get_motor_feedback(motor);
        motor_last_update[motor] = HAL_GetTick();
    }

    return feedback;
}

/**
 * @brief Get motor velocity
 */
int16_t CAN_Protocol_GetMotorVelocity(Motor motor) {
    MotorStats feedback = CAN_Protocol_GetMotorFeedback(motor);
    return feedback.vel_rpm;
}

/**
 * @brief Get motor encoder position
 */
uint16_t CAN_Protocol_GetMotorPosition(Motor motor) {
    MotorStats feedback = CAN_Protocol_GetMotorFeedback(motor);
    return feedback.encoder;
}

/**
 * @brief Get motor current
 */
int16_t CAN_Protocol_GetMotorCurrent(Motor motor) {
    MotorStats feedback = CAN_Protocol_GetMotorFeedback(motor);
    return feedback.actual_current;
}

/**
 * @brief Get motor temperature
 */
uint8_t CAN_Protocol_GetMotorTemperature(Motor motor) {
    MotorStats feedback = CAN_Protocol_GetMotorFeedback(motor);
    return feedback.temperature;
}

/**
 * @brief Check if motor feedback is valid/updated
 */
bool CAN_Protocol_IsMotorConnected(Motor motor) {
    if (motor >= MAX_NUM_OF_MOTORS) {
        return false;
    }

    uint32_t current_time = HAL_GetTick();
    uint32_t time_since_update = current_time - motor_last_update[motor];

    return (time_since_update < MOTOR_TIMEOUT_MS);
}
