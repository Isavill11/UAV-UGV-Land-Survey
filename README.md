# UAV-UGV-Land-Survey
 Current testing of Drone automation of flight pathing!
# Orange Cube+ Drone Control System - Integration Guide

## Table of Contents
1. [Hardware Requirements](#hardware-requirements)
2. [Software Requirements](#software-requirements)
3. [Hardware Configuration](#hardware-configuration)
4. [Compilation Instructions](#compilation-instructions)
5. [Integration with ArduPilot](#integration-with-ardupilot)
6. [Motor Configuration](#motor-configuration)
7. [Testing Procedure](#testing-procedure)
8. [Troubleshooting](#troubleshooting)

---

## Hardware Requirements

### Flight Controller
- **Orange Cube+ (Cubepilot)**
  - STM32H7 processor
  - ICM-20948 9-axis IMU
  - 8x PWM outputs (Main Out 1-8)

### Peripherals
- 4x Brushless ESCs (compatible with 400Hz PWM)
- 4x Brushless motors
- Power distribution board
- LiPo battery (3S-6S recommended)
- GPS module (for ArduPilot integration)
- Telemetry radio (optional)
- Camera module (for MQTT photo transmission)

### Wiring
- Motor 1 (Front-Left) → Main Out 1
- Motor 2 (Front-Right) → Main Out 2
- Motor 3 (Back-Left) → Main Out 3
- Motor 4 (Back-Right) → Main Out 4

---

## Software Requirements

### Development Tools
```bash
# ARM GCC Compiler
sudo apt-get install gcc-arm-none-eabi

# Build tools
sudo apt-get install make cmake git

# Serial terminal (for debugging)
sudo apt-get install minicom screen
```

### Libraries
- **ChibiOS RTOS** (included with ArduPilot)
- **HAL (Hardware Abstraction Layer)**
- **ArduPilot** (optional, for GPS integration)

### For MQTT Photo Transmission (C++ code)
```bash
# MQTT library
sudo apt-get install libpaho-mqtt-dev libpaho-mqttpp-dev

# OpenSSL for base64 encoding
sudo apt-get install libssl-dev

# Compile command
g++ -std=c++11 -o photo_transmitter mqtt_photo.cpp \
    -lpaho-mqttpp3 -lpaho-mqtt3as -lssl -lcrypto -pthread
```

---

## Hardware Configuration

### Orange Cube+ Pin Assignments

#### SPI1 (IMU Interface)
- **MOSI**: PA7
- **MISO**: PA6
- **SCK**: PA5
- **CS**: PC2 (Chip Select for ICM-20948)

#### PWM Outputs (Main Out)
- **TIM1**: Channels 1-4 (Main Out 1-4)
- **TIM4**: Channels 5-8 (Main Out 5-8)
- **Frequency**: 400Hz
- **Range**: 1000-2000µs

#### Status LED
- **GPIO**: PE12 (Orange Cube+ onboard LED)

---

## Compilation Instructions

### Method 1: Standalone Compilation

```bash
# Create project directory
mkdir orange_cube_control
cd orange_cube_control

# Copy the C code to motor_control.c
# Copy the C++ code to photo_transmitter.cpp

# Compile C code for Orange Cube+
arm-none-eabi-gcc -mcpu=cortex-m7 -mthumb \
  -mfloat-abi=hard -mfpu=fpv5-d16 \
  -DSTM32H743xx -DUSE_HAL_DRIVER \
  -O2 -Wall \
  -c motor_control.c -o motor_control.o \
  -I/path/to/ChibiOS/os/hal/include \
  -I/path/to/ChibiOS/os/rt/include \
  -I/path/to/STM32H7xx_HAL_Driver/Inc

# Link
arm-none-eabi-gcc -mcpu=cortex-m7 -mthumb \
  -T STM32H743ZITx_FLASH.ld \
  motor_control.o -o firmware.elf \
  -lm -lc

# Generate binary
arm-none-eabi-objcopy -O binary firmware.elf firmware.bin
```

### Method 2: Integration with ArduPilot Build System

```bash
# Clone ArduPilot
git clone https://github.com/ArduPilot/ardupilot.git
cd ardupilot

# Add your custom code to libraries
mkdir libraries/CustomControl
cp motor_control.c libraries/CustomControl/

# Update wscript to include your library
# Edit libraries/wscript and add 'CustomControl' to build list

# Configure for CubeOrange+
./waf configure --board CubeOrange+

# Build
./waf copter

# Flash firmware
./waf --upload
```

---

## Integration with ArduPilot

### Basic Integration

Add this to your ArduPilot main loop or custom mode:

```c
#include "CustomControl/motor_control.h"

void setup() {
    // Initialize control system
    control_system_init();
    
    gcs().send_text(MAV_SEVERITY_INFO, "Custom control initialized");
}

void loop() {
    // Get GPS waypoint from ArduPilot
    Location target = guided_mode.get_target_loc();
    
    // Calculate desired angles from GPS position error
    float roll_target = calculate_roll_from_position();
    float pitch_target = calculate_pitch_from_position();
    float yaw_target = wrap_360(target.bearing_cd / 100.0);
    
    // Get throttle from altitude controller
    uint16_t throttle = get_throttle_from_altitude();
    
    // Send commands to control system
    set_flight_command(throttle, roll_target, pitch_target, yaw_target);
    
    // Read sensor data for logging
    SensorData sensor_data = get_sensor_data();
    
    // Log to dataflash
    log_sensor_data(sensor_data);
}
```

### Arming/Disarming Integration

```c
// In ArduPilot's arm/disarm functions
void Copter::arm_motors() {
    // Existing ArduPilot arm code...
    
    // Arm custom control system
    arm_motors();
}

void Copter::disarm_motors() {
    // Disarm custom control
    disarm_motors();
    
    // Existing ArduPilot disarm code...
}
```

---

## Motor Configuration

### Quadcopter X Configuration

```
     Front
       ^
       |
   1       2
    \  |  /
     \ | /
   ---CG----
     / | \
    /  |  \
   3       4

Motor Directions:
1 (FL): Counter-Clockwise
2 (FR): Clockwise
3 (BL): Clockwise
4 (BR): Counter-Clockwise
```

### ESC Calibration

1. **Disconnect propellers** (safety first!)
2. Set throttle range:
   ```c
   // In your setup code
   set_flight_command(MOTOR_MAX, 0, 0, 0);  // Max throttle
   arm_motors();
   // Wait for ESC beep
   
   set_flight_command(MOTOR_MIN, 0, 0, 0);  // Min throttle
   // Wait for ESC confirmation beep
   
   disarm_motors();
   ```

3. Test individual motors:
   ```c
   // Slowly increase throttle
   for (uint16_t i = 1100; i < 1300; i += 10) {
       set_flight_command(i, 0, 0, 0);
       delay(100);
   }
   ```

---

## Testing Procedure

### 1. Bench Testing (No Props)

```bash
# Connect via USB
minicom -D /dev/ttyACM0 -b 115200

# In code, add debug output:
printf("Roll: %.2f, Pitch: %.2f, Yaw: %.2f\n", 
       sensor.angles.roll, 
       sensor.angles.pitch, 
       sensor.angles.yaw);
```

**Tests:**
- [ ] IMU initialization (WHO_AM_I = 0xEA)
- [ ] Gyroscope readings update
- [ ] Accelerometer readings update
- [ ] Angle calculations (tilt board, verify angles)
- [ ] Motor arming/disarming
- [ ] PWM outputs on oscilloscope

### 2. Motor Spin Test (No Props)

**Safety:** Remove all propellers!

```c
// Test each motor individually
arm_motors();
set_flight_command(1200, 0, 0, 0);  // Low throttle
delay(2000);
disarm_motors();
```

**Verify:**
- [ ] All motors spin in correct direction
- [ ] No unusual vibrations or sounds
- [ ] Motors stop immediately on disarm

### 3. Stability Test (With Props, Secured)

**Safety:** Secure drone to test stand!

```c
// Test stabilization response
arm_motors();
set_flight_command(1300, 0, 0, 0);  // Hover throttle

// Manually tilt drone
// Motors should respond to maintain level
```

**Verify:**
- [ ] Roll correction works (tilt left/right)
- [ ] Pitch correction works (tilt forward/back)
- [ ] Yaw response (manual rotation)
- [ ] Return to level position

### 4. First Flight (Tethered)

- Attach safety tether
- Start with low altitude (1-2 feet)
- Test hover stability
- Test small roll/pitch commands
- Emergency disarm ready

---

## Troubleshooting

### IMU Not Detected
**Problem:** WHO_AM_I check fails
**Solutions:**
- Verify SPI wiring (MOSI, MISO, SCK, CS)
- Check CS pin assignment (should be PC2)
- Measure SPI clock with oscilloscope
- Add delays after SPI initialization

### Motors Don't Spin
**Problem:** No PWM output
**Solutions:**
- Check PWM timer configuration
- Verify motor output pins
- Confirm arming status
- Check throttle range (1000-2000µs)
- Verify ESC calibration

### Unstable Flight
**Problem:** Drone oscillates or flips
**Solutions:**
- Reduce PID gains (start with Kp = 0.5)
- Check motor direction (see configuration above)
- Verify motor placement (FL, FR, BL, BR)
- Check propeller orientation
- Increase loop frequency if possible

### Drift During Hover
**Problem:** Drone drifts in one direction
**Solutions:**
- Calibrate accelerometer offsets
- Check IMU mounting (should be level)
- Verify complementary filter alpha value
- Trim setpoint offsets if needed

### SPI Communication Errors
**Problem:** Intermittent sensor readings
**Solutions:**
- Add pull-up resistors to SPI lines
- Reduce SPI clock frequency
- Check for electromagnetic interference
- Verify power supply stability
- Add decoupling capacitors near IMU

---

## MQTT Photo Transmission Setup

### Running on Companion Computer

```bash
# On Raspberry Pi or similar
./photo_transmitter tcp://broker.hivemq.com:1883 drone_001

# With authentication
./photo_transmitter tcp://your-broker:1883 drone_001 username password
```

### Camera Integration

Replace the `simulate_capture()` function with actual camera code:

#### For USB Camera (V4L2):
```cpp
#include <linux/videodev2.h>
#include <fcntl.h>
#include <sys/ioctl.h>

bool capture_photo(const std::string& filename) {
    int fd = open("/dev/video0", O_RDWR);
    // Implement V4L2 capture
    close(fd);
}
```

#### For Raspberry Pi Camera:
```cpp
#include <raspicam/raspicam.h>

bool capture_photo(const std::string& filename) {
    raspicam::RaspiCam camera;
    camera.open();
    camera.grab();
    camera.retrieve(buffer);
    camera.release();
    return save_jpeg(filename, buffer);
}
```

---

## Configuration Files

### PID Tuning Parameters

Edit these values in motor_control.c:

```c
#define PID_ROLL_KP 1.5f    // Proportional gain
#define PID_ROLL_KI 0.02f   // Integral gain
#define PID_ROLL_KD 0.8f    // Derivative gain
```

**Tuning Guide:**
1. Start with all gains at 0.5
2. Increase Kp until stable oscillation
3. Reduce Kp by 20%
4. Add Ki slowly (0.01 increments)
5. Add Kd to reduce overshoot

### Flight Modes

```c
#define MODE_STABILIZE 0
#define MODE_ALTITUDE_HOLD 1
#define MODE_GPS_HOLD 2
#define MODE_AUTO 3

void set_flight_mode(uint8_t mode);
```

---

## Safety Reminders

⚠️ **CRITICAL SAFETY RULES:**

1. **ALWAYS** remove propellers during initial testing
2. **NEVER** arm motors without confirming safe environment
3. **ALWAYS** have emergency disarm ready
4. **TEST** on secure test stand before free flight
5. **VERIFY** motor directions before first flight
6. **CHECK** all connections before powering on
7. **START** with low PID gains and increase gradually
8. **MONITOR** battery voltage during flight tests

---

## Additional Resources

### Documentation
- Orange Cube+ Manual: https://docs.cubepilot.org/
- ArduPilot Documentation: https://ardupilot.org/copter/
- ChibiOS Documentation: http://www.chibios.org/dokuwiki/

### Community Support
- ArduPilot Forum: https://discuss.ardupilot.org/
- CubePilot Support: https://discuss.cubepilot.org/

### Useful Tools
- Mission Planner (Windows)
- QGroundControl (Cross-platform)
- MAVProxy (Command-line)

---

## Version History

- **v1.0** - Initial release with Orange Cube+ support
- Hardware: ICM-20948 IMU, STM32H7, 8-channel PWM
- Features: 400Hz control loop, complementary filter, X-quad mixing

---

## License

This code is provided as-is for educational and research purposes.
Always follow local drone regulations and safety guidelines.

---

## Contact & Support

For issues specific to this implementation:
- Check the troubleshooting section above
- Review ArduPilot documentation
- Post on relevant forums with debug output

**Always prioritize safety in all testing and operations!**


Author: Jose Bermudez 
