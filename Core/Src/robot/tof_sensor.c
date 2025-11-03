/**
 ******************************************************************************
 * @file    tof_sensor.c
 * @brief   Module for VL53L1X ToF sensor
 * @author  RDC Won-Won Team
 * @date    October 2025
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "robot/tof_sensor.h"
#include <stdio.h>

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize ToF sensor
 */
void ToF_Sensor_Init(ToF_Sensor_t* sensor, uint16_t i2c_addr, GPIO_TypeDef* xshut_port, uint16_t xshut_pin) {
    tof_vl53l1_init(&sensor->dev, i2c_addr, 0, 33, 50, xshut_port, xshut_pin);
}

/**
 * @brief Start ToF sensor measurements
 */
void ToF_Sensor_Start(ToF_Sensor_t* sensor) {
    VL53L1X_StartRanging(sensor->dev.I2cDevAddr);
}

/**
 * @brief Stop ToF sensor measurements
 */
void ToF_Sensor_Stop(ToF_Sensor_t* sensor) {
    VL53L1X_StopRanging(sensor->dev.I2cDevAddr);
}

/**
 * @brief Get distance from ToF sensor
 */
uint16_t ToF_Sensor_GetDistance(ToF_Sensor_t* sensor) {
    uint8_t dataReady = 0;
    while (dataReady == 0) {
        VL53L1X_CheckForDataReady(sensor->dev.I2cDevAddr, &dataReady);
        HAL_Delay(2);
    }
    VL53L1X_GetDistance(sensor->dev.I2cDevAddr, &sensor->distance);
    VL53L1X_ClearInterrupt(sensor->dev.I2cDevAddr);
    return sensor->distance;
}

