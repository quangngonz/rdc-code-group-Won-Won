/**
 ******************************************************************************
 * @file    drivebase.c
 * @brief   3-Wheel Omni Drive Base Implementation (fixed kinematics + currents)
 * @author  RDC Won-Won Team (edited)
 * @date    November 2025
 ******************************************************************************
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

#include "robot/drivebase.h"
#include "robot/pid.h"
#include "robot/constants.h"
#include "can.h"
#include "main.h"
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <stdbool.h>

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

// Mapping to CAN motors (unchanged)
static const Motor motor_can_map[DRIVE_MOTOR_COUNT] = {
	CAN1_MOTOR1, 	// Right Front (M0)
	CAN1_MOTOR0,   	// Left Front (M2)
	CAN2_MOTOR0  	// Rear (M1)
};

/* Private function prototypes -----------------------------------------------*/
static void DriveBase_LimitCurrent(int16_t *current);
static void DriveBase_LimitRPM(int16_t *rpm);
static float DriveBase_CalculateRotationScale(void);

/* Exported functions --------------------------------------------------------*/

void DriveBase_Init(void) {
	memset(drive_motors, 0, sizeof(drive_motors));

	// Initialize PID for each drive motor
	for (uint8_t i = 0; i < DRIVE_MOTOR_COUNT; i++) {
		drive_motors[i].is_enabled = false;
		PID_Init(&drive_motors[i].velocity_pid, DRIVE_PID_KP, DRIVE_PID_KI,
				DRIVE_PID_KD);
	}
}

void DriveBase_Enable(void) {
	for (uint8_t i = 0; i < DRIVE_MOTOR_COUNT; i++) {
		drive_motors[i].is_enabled = true;
	}
}

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
 * NOTE: vx, vy, omega are expected normalized to [-1, 1] (same convention as
 * your previous code — DRIVE_MAX_RPM and ROTATION_SCALE convert to motor units).
 *
 * Kinematic projection used consistently everywhere:
 *   v_wheel = vx * cos(theta) + vy * sin(theta) + omega * ROTATION_SCALE
 *
 * Wheel angles (measured from +X axis), degrees:
 *   M0 (Right Front) = 30°
 *   M1 (Rear)        = 270° (or -90°)
 *   M2 (Left Front)  = 150°
 */
void DriveBase_SetVelocity(float vx, float vy, float omega) {
	const float ROTATION_SCALE = DriveBase_CalculateRotationScale();
	// wheel angles in radians (consistent)
	const float ANGLE_M0 = 30.0f * M_PI / 180.0f;   // Right Front
	const float ANGLE_M1 = 270.0f * M_PI / 180.0f;  // Rear
	const float ANGLE_M2 = 150.0f * M_PI / 180.0f;  // Left Front

	// projection onto wheel rolling direction (consistent sign convention)
	float v_M0 = vx * cosf(ANGLE_M0) + vy * sinf(ANGLE_M0) + omega * ROTATION_SCALE;
	float v_M1 = vx * cosf(ANGLE_M1) + vy * sinf(ANGLE_M1) + omega * ROTATION_SCALE;
	float v_M2 = vx * cosf(ANGLE_M2) + vy * sinf(ANGLE_M2) + omega * ROTATION_SCALE;

	// Clamp normalization in case inputs exceed [-1,1]
	float max_abs = fabsf(v_M0);
	if (fabsf(v_M1) > max_abs) max_abs = fabsf(v_M1);
	if (fabsf(v_M2) > max_abs) max_abs = fabsf(v_M2);
	if (max_abs > 1.0f) {
		v_M0 /= max_abs;
		v_M1 /= max_abs;
		v_M2 /= max_abs;
	}

	// Convert normalized wheel velocities to RPM target
	int16_t rpm0 = (int16_t)roundf(v_M0 * (float)DRIVE_MAX_RPM);
	int16_t rpm1 = (int16_t)roundf(v_M1 * (float)DRIVE_MAX_RPM);
	int16_t rpm2 = (int16_t)roundf(v_M2 * (float)DRIVE_MAX_RPM);

	DriveBase_SetMotorVelocity(DRIVE_MOTOR_RIGHT_FRONT, rpm0);
	DriveBase_SetMotorVelocity(DRIVE_MOTOR_REAR, rpm1);
	DriveBase_SetMotorVelocity(DRIVE_MOTOR_LEFT_FRONT, rpm2);
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
 *
 * Uses the inverse relationship of:
 *   [v0]   [ cosθ0  sinθ0  R ] [vx]
 *   [v1] = [ cosθ1  sinθ1  R ] [vy]
 *   [v2]   [ cosθ2  sinθ2  R ] [ω ]
 *
 * For the symmetric wheel angles (30°, 150°, 270°) and identical R, the
 * inverse reduces to:
 *   vx = (2/3) * (v0*cosθ0 + v1*cosθ1 + v2*cosθ2)
 *   vy = (2/3) * (v0*sinθ0 + v1*sinθ1 + v2*sinθ2)
 *   ω  = (1 / (3*R)) * (v0 + v1 + v2)
 *
 * Here v_i are normalized wheel speeds (motor_rpm / DRIVE_MAX_RPM).
 */
DriveVelocity_t DriveBase_GetVelocity(void) {
	DriveVelocity_t velocity = { 0 };

	DriveMotorStatus_t status_M0 = DriveBase_GetMotorStatus(DRIVE_MOTOR_RIGHT_FRONT);
	DriveMotorStatus_t status_M1 = DriveBase_GetMotorStatus(DRIVE_MOTOR_REAR);
	DriveMotorStatus_t status_M2 = DriveBase_GetMotorStatus(DRIVE_MOTOR_LEFT_FRONT);

	// Normalize wheel speeds to [-1,1]
	float v_M0 = (float)status_M0.velocity_rpm / (float)DRIVE_MAX_RPM;
	float v_M1 = (float)status_M1.velocity_rpm / (float)DRIVE_MAX_RPM;
	float v_M2 = (float)status_M2.velocity_rpm / (float)DRIVE_MAX_RPM;

	const float ANGLE_M0 = 30.0f * M_PI / 180.0f;   // Right Front
	const float ANGLE_M1 = 270.0f * M_PI / 180.0f;  // Rear
	const float ANGLE_M2 = 150.0f * M_PI / 180.0f;  // Left Front

	velocity.vx = (2.0f / 3.0f) * (
		v_M0 * cosf(ANGLE_M0) +
		v_M1 * cosf(ANGLE_M1) +
		v_M2 * cosf(ANGLE_M2)
	);

	velocity.vy = (2.0f / 3.0f) * (
		v_M0 * sinf(ANGLE_M0) +
		v_M1 * sinf(ANGLE_M1) +
		v_M2 * sinf(ANGLE_M2)
	);

	const float ROTATION_SCALE = DriveBase_CalculateRotationScale();
	velocity.omega = (v_M0 + v_M1 + v_M2) / (3.0f * ROTATION_SCALE);

	return velocity;
}

/**
 * @brief Set drive currents directly (bypasses PID)
 *
 * Maps desired robot velocity (normalized vx, vy, omega) directly to motor
 * currents using inverse kinematics. The maximum current magnitude is scaled
 * to CURRENT_LIMIT * DRIVE_MAX_CURRENT.
 *
 * vx: forward (+), vy: left (+), omega: counterclockwise (+)
 */
#define CLAMP(x, min, max) ((x) < (min) ? (min) : ((x) > (max) ? (max) : (x)))

void DriveBase_SetDirectCurrent(float vx, float vy, float omega) {
    const float CURRENT_LIMIT = 0.20f; // fraction of DRIVE_MAX_CURRENT to apply
    const float ROTATION_SCALE = DriveBase_CalculateRotationScale(); // robot geometry factor

    // Wheel angles (radians)
    const float ANGLE_M0 = 30.0f * M_PI / 180.0f;   // Right Front
    const float ANGLE_M1 = 150.0f * M_PI / 180.0f;  // Left Front
    const float ANGLE_M2 = 270.0f * M_PI / 180.0f;  // Rear

    // Inverse kinematics for 3-wheel omni
    float v_M0 = vx * cosf(ANGLE_M0) + vy * sinf(ANGLE_M0) + omega * ROTATION_SCALE;
    float v_M1 = vx * cosf(ANGLE_M1) + vy * sinf(ANGLE_M1) + omega * ROTATION_SCALE;
    float v_M2 = vx * cosf(ANGLE_M2) + vy * sinf(ANGLE_M2) + omega * ROTATION_SCALE;

    // Normalize so max magnitude = 1.0
    float maxMag = fmaxf(fmaxf(fabsf(v_M0), fabsf(v_M1)), fabsf(v_M2));
    if (maxMag > 1.0f) {
        v_M0 /= maxMag;
        v_M1 /= maxMag;
        v_M2 /= maxMag;
    }

    // Scale to current limit
    const int32_t MAX_APPLIED_CURRENT = (int32_t)roundf((float)DRIVE_MAX_CURRENT * CURRENT_LIMIT);
    int32_t cur0 = (int32_t)roundf(v_M0 * (float)MAX_APPLIED_CURRENT);
    int32_t cur1 = (int32_t)roundf(v_M1 * (float)MAX_APPLIED_CURRENT);
    int32_t cur2 = (int32_t)roundf(v_M2 * (float)MAX_APPLIED_CURRENT);

    // Safety clamps
    cur0 = CLAMP(cur0, -MAX_APPLIED_CURRENT, MAX_APPLIED_CURRENT);
    cur1 = CLAMP(cur1, -MAX_APPLIED_CURRENT, MAX_APPLIED_CURRENT);
    cur2 = CLAMP(cur2, -MAX_APPLIED_CURRENT, MAX_APPLIED_CURRENT);

    // Apply via existing API (will be limited again by DriveBase_ApplyDirectCurrents)
    DriveBase_SetMotorCurrent(DRIVE_MOTOR_RIGHT_FRONT, (int16_t)cur0);
    DriveBase_SetMotorCurrent(DRIVE_MOTOR_REAR, (int16_t)cur1);
    DriveBase_SetMotorCurrent(DRIVE_MOTOR_LEFT_FRONT, (int16_t)cur2);

    // Update the values on the tfts
	tft_prints(0, 4, "Cur: %d", cur0); // Right Front
	tft_prints(0, 5, "Cur: %d", cur1); // Left Front
	tft_prints(0, 6, "Cur: %d", cur2); // Rear
}


void DriveBase_Stop(void) {
	DriveBase_SetVelocity(0.0f, 0.0f, 0.0f);
}

void DriveBase_Update(void) {
	for (uint8_t i = 0; i < DRIVE_MOTOR_COUNT; i++) {
		if (!drive_motors[i].is_enabled) {
			set_motor_current(motor_can_map[i], 0);
			continue;
		}

		// Get current velocity
		DriveMotorStatus_t status = DriveBase_GetMotorStatus((DriveMotor_t) i);

		// Compute PID (setpoint in RPM)
		float pid_output = PID_Compute(&drive_motors[i].velocity_pid,
				drive_motors[i].target_velocity_rpm, status.velocity_rpm,
				0.001f); // 1ms

		// Limit and send
		int16_t current = (int16_t)roundf(pid_output);
		DriveBase_LimitCurrent(&current);
		set_motor_current(motor_can_map[i], current);
	}
}

/* Private functions ---------------------------------------------------------*/

static void DriveBase_LimitCurrent(int16_t *current) {
	if (*current > DRIVE_MAX_CURRENT) {
		*current = DRIVE_MAX_CURRENT;
	} else if (*current < -DRIVE_MAX_CURRENT) {
		*current = -DRIVE_MAX_CURRENT;
	}
}

static void DriveBase_LimitRPM(int16_t *rpm) {
	if (*rpm > DRIVE_MAX_RPM) {
		*rpm = DRIVE_MAX_RPM;
	} else if (*rpm < -DRIVE_MAX_RPM) {
		*rpm = -DRIVE_MAX_RPM;
	}
}

/**
 * @brief Calculate rotation scale factor for omega
 * @return ROTATION_SCALE = robot_linear_equivalent / wheel_linear (normalized units)
 *
 * This function preserves your original geometric approach. It returns the
 * factor that converts a normalized angular velocity (omega) into an
 * equivalent normalized wheel speed contribution (consistent with SetVelocity).
 */
static float DriveBase_CalculateRotationScale(void) {
	float temp = SIDE_A * sqrtf(3.0f) / (2.0f * SIDE_B + SIDE_A);
	float angle = 2.0f * atanf(temp);
	// circumradius of triangle formed by the wheel centers
	float circumradius = sqrtf((SIDE_A * SIDE_A) / (2.0f * (1.0f - cosf(angle))));
	// project center-to-frame distance along wheel rolling direction
	float projection_center_to_frame = circumradius * cosf(M_PI / 6.0f);
	float robot_rad = projection_center_to_frame + WHEEL_OFFSET;
	// divide by wheel radius to convert rotational contribution into wheel-linear units
	return robot_rad / WHEEL_RAD;
}

/**
 * @brief Apply direct currents to motors (bypassing PID)
 */
void DriveBase_ApplyDirectCurrents(void) {
	for (uint8_t i = 0; i < DRIVE_MOTOR_COUNT; i++) {
		if (!drive_motors[i].is_enabled) {
			set_motor_current(motor_can_map[i], 0);
			continue;
		}

		int16_t current = drive_motors[i].target_current;
		DriveBase_LimitCurrent(&current);
		set_motor_current(motor_can_map[i], current);
	}
}
