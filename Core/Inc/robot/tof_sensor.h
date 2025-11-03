/**
 ******************************************************************************
 * @file    tof_sensor.h
 * @brief   Header for tof_sensor.c module
 * @author  RDC Won-Won Team
 * @date    October 2025
 ******************************************************************************
 */

#ifndef INC_ROBOT_TOF_SENSOR_H_
#define INC_ROBOT_TOF_SENSOR_H_

#include "main.h"
#include "tof_vl53l1.h"

/* Exported types ------------------------------------------------------------*/

typedef struct {
    tof_vl53l1_dev_t dev;
    uint16_t distance;
} ToF_Sensor_t;

/* Exported functions --------------------------------------------------------*/

void ToF_Sensor_Init(ToF_Sensor_t* sensor, uint16_t i2c_addr, GPIO_TypeDef* xshut_port, uint16_t xshut_pin);
void ToF_Sensor_Start(ToF_Sensor_t* sensor);
void ToF_Sensor_Stop(ToF_Sensor_t* sensor);
uint16_t ToF_Sensor_GetDistance(ToF_Sensor_t* sensor);
void ToF_Sensor_Log(ToF_Sensor_t* sensor);

#endif /* INC_ROBOT_TOF_SENSOR_H_ */
