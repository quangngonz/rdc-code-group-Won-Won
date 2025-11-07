/**
 ******************************************************************************
 * @file    pneumatic.c
 * @brief   Pneumatic Arm Control Implementation
 * @author  RDC Won-Won Team
 * @date    November 2025
 ******************************************************************************
 * @attention
 *
 * This module implements the pneumatic arm control functions.
 * The GPIO pin is configured in constants.h for easy modification.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "robot/pneumatic.h"
#include "robot/constants.h"

/* Private Functions ---------------------------------------------------------*/

/* Exported Functions --------------------------------------------------------*/

/**
 * @brief  Extends the pneumatic arm
 * @note   Sets the GPIO pin HIGH to activate the solenoid
 * @retval None
 */
void Pneumatic_Extend(void) {
    HAL_GPIO_WritePin(GPIOC, PNEU_Pin, GPIO_PIN_SET);
}

/**
 * @brief  Retracts the pneumatic arm
 * @note   Sets the GPIO pin LOW to deactivate the solenoid
 * @retval None
 */
void Pneumatic_Retract(void) {
    HAL_GPIO_WritePin(GPIOC, PNEU_Pin, GPIO_PIN_RESET);
}

/**
 * @brief  Toggles the pneumatic arm state
 * @note   If extended, it will retract. If retracted, it will extend.
 * @retval None
 */
void Pneumatic_Toggle(void) {
    HAL_GPIO_TogglePin(GPIOC, PNEU_Pin);
}

/**
 * @brief  Gets the current state of the pneumatic arm
 * @retval GPIO_PinState Current state (GPIO_PIN_SET = extended, GPIO_PIN_RESET = retracted)
 */
GPIO_PinState Pneumatic_GetState(void) {
    return HAL_GPIO_ReadPin(GPIOC, PNEU_Pin);
}
