/**
 ******************************************************************************
 * @file    constants.h
 * @brief   Robot Configuration Constants
 * @author  RDC Won-Won Team
 * @date    October 2025
 ******************************************************************************
 * @attention
 *
 * This file contains all configurable constants for the robot system.
 * Tune these values to adjust robot performance.
 *
 ******************************************************************************
 */

#ifndef INC_ROBOT_CONSTANTS_H_
#define INC_ROBOT_CONSTANTS_H_

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include "gpio.h"

/* Drive Base PID Constants --------------------------------------------------*/
#define DRIVE_PID_KP        7.0f
#define DRIVE_PID_KI        0.05f
#define DRIVE_PID_KD        0.00005f

/* Drive Base Physical Constants ---------------------------------------------*/
#define DRIVE_ROBOT_RADIUS  0.2f    // Distance from center to wheel (meters)

/* Pneumatic Arm GPIO Configuration ------------------------------------------*/
#define PNEUMATIC_GPIO_PORT     GPIOC
#define PNEUMATIC_GPIO_PIN      GPIO_PIN_3

#ifdef __cplusplus
}
#endif

#endif /* INC_ROBOT_CONSTANTS_H_ */
