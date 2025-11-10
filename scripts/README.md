# Creating an Autonomous Sequence File

The `autonomous_sequence.json` file defines the series of steps the robot will execute when running in autonomous mode. This guide explains the structure of the file and how to define different types of actions, from simple timed movements to sensor-based PID control.

## File Structure

The file is a JSON array, where each element in the array is an object representing a single step in the sequence.

```json
[
  {
    "description": "First step...",
    "...": "..."
  },
  {
    "description": "Second step...",
    "...": "..."
  }
]
```

---

## Step Types

There are three main types of steps you can define:

1.  **Time-Based Movement**: Move the robot in a specific direction for a set duration.
2.  **Pneumatic Action**: Extend or retract the pneumatic arm.
3.  **ToF-Based Movement**: Move the robot until the Time-of-Flight (ToF) distance sensor reaches a specific target distance. This can be done with simple "full speed" control or more precise PID control. (DOES NOT WORK RIGHT NOW TRY TO FIX IT)

---

## 1. Time-Based Movement

This is the simplest action. It sends a specific controller input to the robot for a fixed amount of time.

### Parameters

| Parameter     | Type   | Description                                                                                                                                                                                                                                                                                                                          |
| ------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `description` | String | A brief explanation of what the step does. This is shown in the UI.                                                                                                                                                                                                                                                                  |
| `controls`    | Array  | An array of 6 integers `[lx, ly, rx, ry, lt, rt]` representing the controller state. Values range from -100 to +100 for sticks and 0 to 100 for triggers. <br>• `lx`: Left Stick X (Strafe Left/Right)<br>• `ly`: Left Stick Y (Forward/Backward)<br>• `rx`: Right Stick X (Rotate Left/Right)<br>• `ry`: Right Stick Y does nothing |
| `duration`    | Float  | The duration of the movement in seconds.                                                                                                                                                                                                                                                                                             |

### Example

```json
{
  "description": "Move forward at 70% speed for 3.5 seconds",
  "controls": [0, 70, 0, 0, 0, 0],
  "duration": 3.5
},
{
  "description": "Rotate clockwise at full speed for 1.2 seconds",
  "controls": [0, 0, 100, 0, 0, 0],
  "duration": 1.2
}
```

---

## 2. Pneumatic Action

This step activates the pneumatic arm. The system identifies the action based on the `description` text.

### Parameters

| Parameter     | Type   | Description                                                                |
| ------------- | ------ | -------------------------------------------------------------------------- |
| `description` | String | Must contain the word **"Extend"** or **"Retract"** to trigger the action. |
| `controls`    | `null` | This **must** be set to `null` to indicate a non-movement, special action. |
| `duration`    | Float  | The time in seconds to hold the button that activates the pneumatic arm.   |

### Example

```json
{
  "description": "Extend Pneumatic arm",
  "controls": null,
  "duration": 1.0
},
{
  "description": "Retract Pneumatic arm",
  "controls": null,
  "duration": 1.0
}
```

---

## 3. ToF-Based Movement

This action uses the Time-of-Flight (ToF) sensor to control movement, stopping when a target distance is reached. It has two modes: simple (bang-bang) and PID-controlled.

### Common Parameters (Both Modes)

| Parameter       | Type    | Default | Description                                                                                                           |
| --------------- | ------- | ------- | --------------------------------------------------------------------------------------------------------------------- |
| `description`   | String  | -       | A description of the step.                                                                                            |
| `controls`      | Array   | -       | The initial movement direction, e.g., `[0, 100, 0, 0, 0, 0]` for forward. The speed will be controlled by the system. |
| `tof_target`    | Integer | -       | The target distance in millimeters (mm). The robot will stop when it reaches this distance.                           |
| `tof_timeout`   | Float   | 10.0    | The maximum time in seconds to attempt the movement before giving up.                                                 |
| `tof_tolerance` | Integer | 5       | The acceptable error margin in mm for reaching the target.                                                            |

### Simple (Bang-Bang) Mode Example

This mode moves at full speed until the `tof_target` is reached. It is the default if `use_pid` is not specified.

```json
{
  "description": "Move forward until 300mm from wall",
  "controls":,
  "tof_target": 300,
  "tof_timeout": 8.0,
  "tof_tolerance": 10
}
```

### PID Control Mode

This mode provides smoother, more precise movement by slowing the robot down as it approaches the target. This helps prevent overshooting and is ideal for accurate positioning.

#### PID-Specific Parameters

| Parameter   | Type    | Default | Description                                                                                                                           |
| ----------- | ------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `use_pid`   | Boolean | `false` | Set to `true` to enable PID control for this step.                                                                                    |
| `pid_kp`    | Float   | 0.5     | **Proportional gain**: Controls how aggressively the robot responds to the distance error. Higher is faster, but can cause overshoot. |
| `pid_ki`    | Float   | 0.0     | **Integral gain**: Corrects small, steady-state errors if the robot stops just short of the target.                                   |
| `pid_kd`    | Float   | 0.1     | **Derivative gain**: Dampens the movement to reduce overshoot and oscillation.                                                        |
| `min_speed` | Integer | 20      | The minimum power level (0-100) required to overcome friction and make the robot move.                                                |

#### PID Mode Example

```json
{
  "description": "Move forward precisely to 150mm using PID",
  "controls":,
  "tof_target": 150,
  "tof_timeout": 15.0,
  "use_pid": true,
  "pid_kp": 0.8,
  "pid_ki": 0.05,
  "pid_kd": 0.2,
  "min_speed": 25,
  "tof_tolerance": 5
}
```

---

## Full Example (`autonomous_sequence.json`)

Here is a complete example file combining different step types.

```json
[
  {
    "description": "Retract Pneumatic arm to start",
    "controls": null,
    "duration": 1.0
  },
  {
    "description": "Move forward at 70% speed",
    "controls":,
    "duration": 7.0
  },
  {
    "description": "Extend Pneumatic arm to score",
    "controls": null,
    "duration": 1.0
  },
  {
    "description": "Move backward precisely using PID",
    "controls": [0, -100, 0, 0, 0, 0],
    "tof_target": 500,
    "tof_timeout": 10.0,
    "use_pid": true,
    "pid_kp": 0.7,
    "min_speed": 20
  },
  {
    "description": "Rotate clockwise",
    "controls":,
    "duration": 1.2
  }
]
```
