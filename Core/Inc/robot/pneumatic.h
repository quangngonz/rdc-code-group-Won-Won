/**
 ******************************************************************************
 * @file    pneumatic.h
 * @brief   Pneumatic Arm Control Module
 * @author  RDC Won-Won Team
 * @date    November 2025
 ******************************************************************************
 * @attention
 *
 * This module controls the pneumatic arm extension/retraction.
 * Uses a single GPIO pin to control a solenoid valve.
 *
 ******************************************************************************
 */

#ifndef INC_ROBOT_PNEUMATIC_H_
#define INC_ROBOT_PNEUMATIC_H_

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "gpio.h"

/* Exported Functions --------------------------------------------------------*/

/**
 * @brief  Extends the pneumatic arm
 * @note   Sets the GPIO pin HIGH to activate the solenoid
 * @retval None
 */
void Pneumatic_Extend(void);

/**
 * @brief  Retracts the pneumatic arm
 * @note   Sets the GPIO pin LOW to deactivate the solenoid
 * @retval None
 */
void Pneumatic_Retract(void);

/**
 * @brief  Toggles the pneumatic arm state
 * @note   If extended, it will retract. If retracted, it will extend.
 * @retval None
 */
void Pneumatic_Toggle(void);

/**
 * @brief  Gets the current state of the pneumatic arm
 * @retval GPIO_PinState Current state (GPIO_PIN_SET = extended, GPIO_PIN_RESET = retracted)
 */
GPIO_PinState Pneumatic_GetState(void);

#ifdef __cplusplus
}
#endif

#endif /* INC_ROBOT_PNEUMATIC_H_ */
