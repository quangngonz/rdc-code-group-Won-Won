/**
 ******************************************************************************
 * @file    drivebase.c
 * @brief   3-Wheel Omni Drive Base Implementation
 * @author  RDC Won-Won Team
 * @date    October 2025
 ******************************************************************************
 * @attention
 *
 * Configuration: 2 wheels at front, 1 wheel at back
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

/* Includes ------------------------------------------------------------------*/
#include "robot/drivebase.h"
#include "robot/pid.h"
#include "robot/constants.h"
#include "can.h"
#include "main.h"
#include <string.h>
#include <math.h>

/* Private defines -----------------------------------------------------------*/
#ifndef M_PI
#define M_PI 3.14159265358979323846f
#endif

// Robot geometry parameters
#define SIDE_A 0.093f          // 93mm - short side 
#define SIDE_B 0.141f          // 141mm - long side
#define WHEEL_OFFSET 0.049f    // Distance from frame mounting point to wheel center 
#define WHEEL_RAD 0.0762f      // 3 inch 

/* Private typedef -----------------------------------------------------------*/

typedef struct {
	bool is_enabled;
	int16_t target_velocity_rpm;
	int16_t target_current;
	PID_Controller_t velocity_pid;
} DriveMotorControl_t;

/* Private variables ---------------------------------------------------------*/

static DriveMotorControl_t drive_motors[DRIVE_MOTOR_COUNT];

// Mapping to CAN motors
static const Motor motor_can_map[DRIVE_MOTOR_COUNT] = {
		CAN1_MOTOR0, 	// Right Front (M0)
		CAN1_MOTOR1,   	// Left Front (M2)
		CAN2_MOTOR0  	// Rear (M1)
		};

/* Private function prototypes -----------------------------------------------*/
static void DriveBase_LimitCurrent(int16_t *current);
static void DriveBase_LimitRPM(int16_t *rpm);
static float DriveBase_CalculateRotationScale(void);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize drive base
 */
void DriveBase_Init(void) {
	memset(drive_motors, 0, sizeof(drive_motors));

	// Initialize PID for each drive motor
	for (uint8_t i = 0; i < DRIVE_MOTOR_COUNT; i++) {
		drive_motors[i].is_enabled = false;
		PID_Init(&drive_motors[i].velocity_pid, DRIVE_PID_KP, DRIVE_PID_KI,
				DRIVE_PID_KD);
	}
} 

/**
 * @brief Enable drive motors
 */
void DriveBase_Enable(void) {
	for (uint8_t i = 0; i < DRIVE_MOTOR_COUNT; i++) {
		drive_motors[i].is_enabled = true;
	}
}

/**
 * @brief Disable drive motors
 */
void DriveBase_Disable(void) {
	for (uint8_t i = 0; i < DRIVE_MOTOR_COUNT; i++) {
		drive_motors[i].is_enabled = false;
		drive_motors[i].target_velocity_rpm = 0;
		drive_motors[i].target_current = 0;
		set_motor_current(motor_can_map[i], 0);
	}
}

/**
 * @brief Set drive velocity using inverse kinematics
 *
 * Inverse Kinematics for 3-wheel omni drive (2 front, 1 rear):
 *
 * Configuration:
 *     M2 (Left Front, 150°)    M0 (Right Front, 30°)
 *              \               /
 *               \             /
 *                \           /
 *              M1 (Rear, 270°)
 */
void DriveBase_SetVelocity(float vx, float vy, float omega) {
	// 74
	const float ROTATION_SCALE = DriveBase_CalculateRotationScale();
	
	// Wheel angles
	const float ANGLE_M0 = 30.0f * M_PI / 180.0f;   // Right Front
	const float ANGLE_M1 = 270.0f * M_PI / 180.0f;  // Rear
	const float ANGLE_M2 = 150.0f * M_PI / 180.0f;  // Left Front

	// Inverse kinematics
	float v_M0 = vx * cosf(ANGLE_M0) - vy * sinf(ANGLE_M0) + omega * ROTATION_SCALE;
	float v_M1 = vx * cosf(ANGLE_M1) - vy * sinf(ANGLE_M1) + omega * ROTATION_SCALE;
	float v_M2 = vx * cosf(ANGLE_M2) - vy * sinf(ANGLE_M2) + omega * ROTATION_SCALE;

	DriveBase_SetMotorVelocity(DRIVE_MOTOR_RIGHT_FRONT, (int16_t)(v_M0 * DRIVE_MAX_RPM));
	DriveBase_SetMotorVelocity(DRIVE_MOTOR_REAR, (int16_t)(v_M1 * DRIVE_MAX_RPM));
	DriveBase_SetMotorVelocity(DRIVE_MOTOR_LEFT_FRONT, (int16_t)(v_M2 * DRIVE_MAX_RPM));
}

/**
 * @brief Set individual motor velocity
 */
void DriveBase_SetMotorVelocity(DriveMotor_t motor, int16_t velocity_rpm) {
	if (motor >= DRIVE_MOTOR_COUNT)
		return;

	DriveBase_LimitRPM(&velocity_rpm);
	drive_motors[motor].target_velocity_rpm = velocity_rpm;
}

/**
 * @brief Set individual motor current
 */
void DriveBase_SetMotorCurrent(DriveMotor_t motor, int16_t current) {
	if (motor >= DRIVE_MOTOR_COUNT)
		return;

	DriveBase_LimitCurrent(&current);
	drive_motors[motor].target_current = current;
}

/**
 * @brief Get motor status
 */
DriveMotorStatus_t DriveBase_GetMotorStatus(DriveMotor_t motor) {
	DriveMotorStatus_t status = { 0 };

	if (motor < DRIVE_MOTOR_COUNT) {
		MotorStats feedback = get_motor_feedback(motor_can_map[motor]);
		status.velocity_rpm = feedback.vel_rpm;
		status.current = feedback.actual_current;
		status.encoder = feedback.encoder;
		status.temperature = feedback.temperature;
	}

	return status;
}

/**
 * @brief Get current robot velocity using forward kinematics
 */
DriveVelocity_t DriveBase_GetVelocity(void) {
	DriveVelocity_t velocity = { 0 };

	// Actual velocity from motors
	DriveMotorStatus_t status_M0 = DriveBase_GetMotorStatus(DRIVE_MOTOR_RIGHT_FRONT);
	DriveMotorStatus_t status_M1 = DriveBase_GetMotorStatus(DRIVE_MOTOR_REAR);
	DriveMotorStatus_t status_M2 = DriveBase_GetMotorStatus(DRIVE_MOTOR_LEFT_FRONT);
	
	// Normalizing stuff
	float v_M0 = (float)status_M0.velocity_rpm / DRIVE_MAX_RPM;
	float v_M1 = (float)status_M1.velocity_rpm / DRIVE_MAX_RPM;
	float v_M2 = (float)status_M2.velocity_rpm / DRIVE_MAX_RPM;
	
	// Wheel angles
	const float ANGLE_M0 = 30.0f * M_PI / 180.0f;   // Right Front
	const float ANGLE_M1 = 270.0f * M_PI / 180.0f;  // Rear
	const float ANGLE_M2 = 150.0f * M_PI / 180.0f;  // Left Front
	
	velocity.vx = (2.0f/3.0f) * (
		v_M0 * cosf(ANGLE_M0) + 
		v_M1 * cosf(ANGLE_M1) + 
		v_M2 * cosf(ANGLE_M2)
	);
	
	velocity.vy = -(2.0f/3.0f) * (
		v_M0 * sinf(ANGLE_M0) + 
		v_M1 * sinf(ANGLE_M1) + 
		v_M2 * sinf(ANGLE_M2)
	);
	
	// Calculate omega from average wheel velocity
	const float ROTATION_SCALE = DriveBase_CalculateRotationScale();
	velocity.omega = (v_M0 + v_M1 + v_M2) / (3.0f * ROTATION_SCALE);

	return velocity;
}
;

/**
 * @brief Stop all drive motors
 */
void DriveBase_Stop(void) {
	DriveBase_SetVelocity(0, 0, 0);
}
;

/**
 * @brief Update drive control loop
 */
void DriveBase_Update(void) {
	for (uint8_t i = 0; i < DRIVE_MOTOR_COUNT; i++) {
		if (!drive_motors[i].is_enabled) {
			set_motor_current(motor_can_map[i], 0);
			continue;
		}

		// Get current velocity
		DriveMotorStatus_t status = DriveBase_GetMotorStatus((DriveMotor_t) i);

		// Compute PID
		float pid_output = PID_Compute(&drive_motors[i].velocity_pid,
				drive_motors[i].target_velocity_rpm, status.velocity_rpm,
				0.001f); // 1ms

		// Limit and send
		int16_t current = (int16_t) pid_output;
		DriveBase_LimitCurrent(&current);
		set_motor_current(motor_can_map[i], current);
	}
}
;

/* Private functions ---------------------------------------------------------*/

static void DriveBase_LimitCurrent(int16_t* current) {
    if (*current > DRIVE_MAX_CURRENT) {
        *current = DRIVE_MAX_CURRENT;
    } else if (*current < -DRIVE_MAX_CURRENT) {
        *current = -DRIVE_MAX_CURRENT;
    }
}

static void DriveBase_LimitRPM(int16_t* rpm) {
    if (*rpm > DRIVE_MAX_RPM) {
        *rpm = DRIVE_MAX_RPM;
    } else if (*rpm < -DRIVE_MAX_RPM) {
        *rpm = -DRIVE_MAX_RPM;
    }
}

/**
 * @brief Calculate rotation scale factor for omega
 * @return ROTATION_SCALE = ROBOT_RAD / WHEEL_RAD
 */
static float DriveBase_CalculateRotationScale(void) {
	float temp = SIDE_A * sqrtf(3.0f) / (2.0f * SIDE_B + SIDE_A);
	float angle = 2.0f * atanf(temp);
	float circumradius = sqrtf((SIDE_A * SIDE_A) / (2.0f * (1.0f - cosf(angle))));
	float projection_center_to_frame = circumradius * cosf(M_PI / 6.0f);
	float robot_rad = projection_center_to_frame + WHEEL_OFFSET;
	return robot_rad / WHEEL_RAD;
}

