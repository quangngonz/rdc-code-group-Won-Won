/**
 ******************************************************************************
 * @file    drivebase.h
 * @brief   3-Wheel Omni Drive Base Control Module
 * @author  RDC Won-Won Team
 * @date    October 2025
 ******************************************************************************
 * @attention
 *
 * This module controls the 3-wheel omni-drive base.
 * Handles individual motor control and inverse/forward kinematics.
 *
 *             Front
 *      M2 (Left Front)   M0 (Right Front)
 *             \           /
 *              \         /
 *               \       /
 *               M1 (Rear)
 *                Back
 *
 ******************************************************************************
 */

#ifndef INC_ROBOT_DRIVEBASE_H_
#define INC_ROBOT_DRIVEBASE_H_


#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Drive motor enumeration
 */
typedef enum {
    DRIVE_MOTOR_RIGHT_FRONT = 0,  // M0
    DRIVE_MOTOR_REAR = 1,         // M1
    DRIVE_MOTOR_LEFT_FRONT = 2,   // M2
    DRIVE_MOTOR_COUNT
} DriveMotor_t;



/**
 * @brief Drive motor status
 */
typedef struct {
    int16_t velocity_rpm;
    int16_t current;
    uint16_t encoder;
    uint8_t temperature;
} DriveMotorStatus_t;

/**
 * @brief Robot velocity command (in robot frame)
 */
typedef struct {
    float vx;       // Forward/backward velocity [-1.0 to 1.0]
    float vy;       // Left/right velocity [-1.0 to 1.0]
    float omega;    // Rotational velocity [-1.0 to 1.0]
} DriveVelocity_t;

/* Exported constants --------------------------------------------------------*/
#define DRIVE_MAX_RPM           3000
#define DRIVE_MAX_CURRENT       16384

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize drive base
 */
void DriveBase_Init(void);

/**
 * @brief Enable drive motors
 */
void DriveBase_Enable(void);

/**
 * @brief Disable drive motors
 */
void DriveBase_Disable(void);

/**
 * @brief Set drive velocity (uses inverse kinematics)
 * @param vx: Forward/backward [-1.0 to 1.0]
 * @param vy: Left/right [-1.0 to 1.0]
 * @param omega: Rotation [-1.0 to 1.0]
 */
void DriveBase_SetVelocity(float vx, float vy, float omega);

/**
 * @brief Set drive currents directly (bypasses PID)
 * Uses inverse kinematics to directly map velocities to motor currents
 * @param vx: Forward/backward [-1.0 to 1.0]
 * @param vy: Left/right [-1.0 to 1.0]
 * @param omega: Rotation [-1.0 to 1.0]
 */
void DriveBase_SetDirectCurrent(float vx, float vy, float omega);

/**
 * @brief Set individual motor velocity
 * @param motor: Motor ID
 * @param velocity_rpm: Target velocity in RPM
 */
void DriveBase_SetMotorVelocity(DriveMotor_t motor, int16_t velocity_rpm);

/**
 * @brief Set individual motor current
 * @param motor: Motor ID
 * @param current: Target current [-16384 to 16384]
 */
void DriveBase_SetMotorCurrent(DriveMotor_t motor, int16_t current);

/**
 * @brief Get motor status
 * @param motor: Motor ID
 * @return Motor status
 */
DriveMotorStatus_t DriveBase_GetMotorStatus(DriveMotor_t motor);

/**
 * @brief Get current robot velocity (forward kinematics)
 * @return Current velocity
 */
DriveVelocity_t DriveBase_GetVelocity(void);

/**
 * @brief Stop all drive motors
 */
void DriveBase_Stop(void);

/**
 * @brief Update drive control loop (call every 1ms)
 */
void DriveBase_Update(void);

/**
 * @brief Apply direct currents to motors (bypassing PID)
 * This function immediately sends current commands to motors without PID control
 */
void DriveBase_ApplyDirectCurrents(void);

#ifdef __cplusplus
}
#endif

#endif /* INC_ROBOT_DRIVEBASE_H_ */
