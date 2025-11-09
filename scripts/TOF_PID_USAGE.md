# ToF-Based Movement with PID Control

## Overview

The autonomous control system now supports two modes for ToF sensor-based movement:

1. **Simple Bang-Bang Control**: Full speed until target reached
2. **PID Control**: Smooth speed adjustment based on distance

## Usage Examples

### Simple Bang-Bang Control (Default)

```json
{
  "description": "Move left until ToF target (simple)",
  "controls": [-100, 0, 0, 0, 0, 0],
  "tof_target": 300,
  "tof_timeout": 10.0,
  "tof_tolerance": 10
}
```

- Moves at full speed (-100) until ToF ≤ 300mm
- Stops immediately when target reached
- Good for: Quick movements, when precision isn't critical

### PID Control Mode

```json
{
  "description": "Move forward with PID control",
  "controls": [0, 100, 0, 0, 0, 0],
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

- Automatically adjusts speed based on distance from target
- Slows down as it approaches target
- Good for: Precise positioning, smooth motion, reducing overshoot

## Parameters

### Common Parameters (Both Modes)

| Parameter       | Type  | Default  | Description                                  |
| --------------- | ----- | -------- | -------------------------------------------- |
| `controls`      | array | required | Movement direction: [lx, ly, rx, ry, lt, rt] |
| `tof_target`    | int   | required | Target distance in mm                        |
| `tof_timeout`   | float | 10.0     | Maximum time before giving up (seconds)      |
| `tof_tolerance` | int   | 5        | Acceptable distance error (mm)               |

### PID-Specific Parameters

| Parameter   | Type  | Default | Description                        |
| ----------- | ----- | ------- | ---------------------------------- |
| `use_pid`   | bool  | false   | Enable PID control                 |
| `pid_kp`    | float | 0.5     | Proportional gain (responsiveness) |
| `pid_ki`    | float | 0.0     | Integral gain (steady-state error) |
| `pid_kd`    | float | 0.1     | Derivative gain (dampening)        |
| `min_speed` | int   | 20      | Minimum speed to overcome friction |

## PID Tuning Guide

### Kp (Proportional Gain)

- **Higher Kp** = More aggressive, faster response, but more overshoot
- **Lower Kp** = Slower, gentler approach, less overshoot
- **Recommended range**: 0.3 - 1.5
- **Start with**: 0.5

### Ki (Integral Gain)

- Eliminates steady-state error (when robot stops short of target)
- **Higher Ki** = Faster correction of persistent errors
- **Too high** = Oscillation and instability
- **Recommended range**: 0.0 - 0.1
- **Start with**: 0.0 (add only if needed)

### Kd (Derivative Gain)

- Reduces overshoot by dampening rapid changes
- **Higher Kd** = More dampening, smoother deceleration
- **Too high** = Sluggish response, sensitive to noise
- **Recommended range**: 0.05 - 0.3
- **Start with**: 0.1

### Min Speed

- Minimum power to overcome friction and actually move
- **Too low** = Robot stalls before reaching target
- **Too high** = Less smooth, harder to stop precisely
- **Recommended range**: 15 - 35
- **Start with**: 25

## Tuning Process

1. **Start with defaults**: kp=0.5, ki=0.0, kd=0.1, min_speed=25
2. **Test the movement**: Does it reach the target?
3. **Adjust Kp**:
   - Too slow? Increase Kp
   - Overshoots a lot? Decrease Kp
4. **Add Kd** if oscillating or overshooting
5. **Add Ki** only if it consistently stops short

## Movement Direction

The `controls` array specifies which axis and direction to move:

- **Left**: `[-100, 0, 0, 0, 0, 0]` (negative lx)
- **Right**: `[100, 0, 0, 0, 0, 0]` (positive lx)
- **Forward**: `[0, 100, 0, 0, 0, 0]` (positive ly)
- **Backward**: `[0, -100, 0, 0, 0, 0]` (negative ly)

The PID controller will automatically scale this to the appropriate speed based on distance from target.

## How PID Works

```
Error = Target - Current_Distance

Speed = (Kp × Error) + (Ki × Accumulated_Error) + (Kd × Rate_of_Change)
```

**Example**: Target = 200mm, Current = 500mm

- Error = 200 - 500 = -300mm
- With Kp=0.5: Speed ≈ -150 (fast approach)
- At Current = 220mm: Error = -20mm, Speed ≈ -10 (slow final approach)
- Stops when within tolerance (e.g., 195-205mm)

## Troubleshooting

| Problem              | Likely Cause              | Solution                    |
| -------------------- | ------------------------- | --------------------------- |
| Robot doesn't move   | min_speed too low         | Increase min_speed to 30-35 |
| Overshoots target    | Kp too high               | Decrease Kp or increase Kd  |
| Oscillates at target | Ki too high or Kd too low | Decrease Ki, increase Kd    |
| Stops before target  | min_speed too high        | Decrease min_speed          |
| Very slow approach   | Kp too low                | Increase Kp to 0.8-1.0      |
| Jerky movement       | Kd too high               | Decrease Kd to 0.05         |

"controls": [lx, ly, rx, ry, lt, rt]
