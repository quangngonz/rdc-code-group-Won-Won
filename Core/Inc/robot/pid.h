/**
 ******************************************************************************
 * @file    pid.h
 * @brief   Simple PID controller module
 * @author  RDC Won-Won Team
 * @date    October 2025
 ******************************************************************************
 * @attention
 *
 * Simple PID controller for motor control.
 * Formula: output = Kp * error + Ki * integral - Kd * derivative
 *
 ******************************************************************************
 */

#ifndef INC_ROBOT_PID_H_
#define INC_ROBOT_PID_H_


#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Simple PID controller structure
 */
typedef struct {
    float Kp;               // Proportional gain
    float Ki;               // Integral gain
    float Kd;               // Derivative gain
    float previous_error;   // Previous error
    float integral;         // Integral accumulator
} PID_Controller_t;

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize PID controller
 * @param pid: Pointer to PID structure
 * @param Kp: Proportional gain
 * @param Ki: Integral gain
 * @param Kd: Derivative gain
 */
void PID_Init(PID_Controller_t* pid, float Kp, float Ki, float Kd);

/**
 * @brief Compute PID output
 * @param pid: Pointer to PID structure
 * @param setpoint: Target value
 * @param measured: Current value
 * @param dt: Time step in seconds
 * @return PID output
 */
float PID_Compute(PID_Controller_t* pid, float setpoint, float measured, float dt);

/**
 * @brief Reset PID state (clear integral and error)
 * @param pid: Pointer to PID structure
 */
void PID_Reset(PID_Controller_t* pid);

#ifdef __cplusplus
}
#endif

#endif /* INC_ROBOT_PID_H_ */
