/**
 ******************************************************************************
 * @file    pid.c
 * @brief   Simple PID controller implementation
 * @author  RDC Won-Won Team
 * @date    October 2025
 ******************************************************************************
 */


/* Includes ------------------------------------------------------------------*/
#include "robot/pid.h"

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize PID controller
 */
void PID_Init(PID_Controller_t* pid, float Kp, float Ki, float Kd) {
    pid->Kp = Kp;
    pid->Ki = Ki;
    pid->Kd = Kd;
    pid->previous_error = 0.0f;
    pid->integral = 0.0f;
}

/**
 * @brief Compute PID output
 */
float PID_Compute(PID_Controller_t* pid, float setpoint, float measured, float dt) {
    // Calculate error
    float error = setpoint - measured;

    // Proportional term
    float P = pid->Kp * error;

    // Integral term
    pid->integral += error * dt;
    float I = pid->Ki * pid->integral;

    // Derivative term
    float derivative = (error - pid->previous_error) / dt;
    float D = pid->Kd * derivative;

    // Save error for next iteration
    pid->previous_error = error;

    // Calculate output
    return P + I - D;
}

/**
 * @brief Reset PID state
 */
void PID_Reset(PID_Controller_t* pid) {
    pid->previous_error = 0.0f;
    pid->integral = 0.0f;
}
