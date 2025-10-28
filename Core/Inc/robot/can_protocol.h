/**
 ******************************************************************************
 * @file    can_protocol.h
 * @brief   CAN bus protocol wrapper header file
 * @author  RDC Won-Won Team
 * @date    October 2025
 ******************************************************************************
 * @attention
 *
 * This module provides a high-level wrapper around the CAN bus driver
 * for easier motor control and feedback access. It simplifies the interface
 * to the underlying can.c module.
 *
 ******************************************************************************
 */


#ifndef INC_ROBOT_CAN_PROTOCOL_H_
#define INC_ROBOT_CAN_PROTOCOL_H_


#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <stdbool.h>
#include "can.h"

/* Re-export types from can.h for convenience ----------------------------- */
// Use the Motor enum and MotorStats struct from can.h

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize CAN bus protocol
 * Configures filters and starts CAN communication
 */
void CAN_Protocol_Init(void);

/**
 * @brief Stop CAN bus communication
 */
void CAN_Protocol_Stop(void);

/**
 * @brief Update CAN bus communication (transmit and receive)
 * Should be called periodically (e.g., every 1ms)
 */
void CAN_Protocol_Update(void);

/**
 * @brief Send motor current command
 * @param motor: Target motor
 * @param current: Current value [-16384 to 16384]
 */
void CAN_Protocol_SetMotorCurrent(Motor motor, int16_t current);

/**
 * @brief Get motor feedback data
 * @param motor: Target motor
 * @return Motor feedback structure with encoder, velocity, current, temperature
 */
MotorStats CAN_Protocol_GetMotorFeedback(Motor motor);

/**
 * @brief Get motor velocity
 * @param motor: Target motor
 * @return Velocity in RPM
 */
int16_t CAN_Protocol_GetMotorVelocity(Motor motor);

/**
 * @brief Get motor encoder position
 * @param motor: Target motor
 * @return Encoder position [0-8191]
 */
uint16_t CAN_Protocol_GetMotorPosition(Motor motor);

/**
 * @brief Get motor current
 * @param motor: Target motor
 * @return Current reading
 */
int16_t CAN_Protocol_GetMotorCurrent(Motor motor);

/**
 * @brief Get motor temperature
 * @param motor: Target motor
 * @return Temperature in °C
 */
uint8_t CAN_Protocol_GetMotorTemperature(Motor motor);

/**
 * @brief Check if motor feedback is valid/updated
 * @param motor: Target motor
 * @return true if valid feedback received recently, false otherwise
 */
bool CAN_Protocol_IsMotorConnected(Motor motor);

#ifdef __cplusplus
}
#endif


#endif /* INC_ROBOT_CAN_PROTOCOL_H_ */
