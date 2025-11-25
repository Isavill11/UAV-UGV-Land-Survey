/*
 * Orange Cube+ Autonomous Stabilization System
 * Automatic altitude hold, GPS position hold, return-to-home, and obstacle avoidance
 * Compatible with ChibiOS/ArduPilot environment
 * Supports ICM-20948 IMU and STM32H7 processor
 */

#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include "ch.h"
#include "hal.h"

// Orange Cube+ Hardware Configuration
#define IMU_SPI_DEVICE SPID1
#define IMU_CS_PORT GPIOC
#define IMU_CS_PIN 2

// ICM-20948 Registers
#define ICM20948_WHO_AM_I 0x00
#define ICM20948_PWR_MGMT_1 0x06
#define ICM20948_GYRO_CONFIG 0x01
#define ICM20948_ACCEL_CONFIG 0x14
#define ICM20948_ACCEL_XOUT_H 0x2D
#define ICM20948_GYRO_XOUT_H 0x33

// Sensor Sensitivity
#define GYRO_SCALE 131.0f
#define ACCEL_SCALE 16384.0f

// PWM Configuration
#define PWM_FREQ 400
#define MOTOR_MIN 1000
#define MOTOR_MAX 2000
#define MOTOR_ARM 1100

// PID Gains - Roll/Pitch
#define PID_ROLL_KP 1.5f
#define PID_ROLL_KI 0.02f
#define PID_ROLL_KD 0.8f
#define PID_PITCH_KP 1.5f
#define PID_PITCH_KI 0.02f
#define PID_PITCH_KD 0.8f

// PID Gains - Yaw
#define PID_YAW_KP 2.0f
#define PID_YAW_KI 0.05f
#define PID_YAW_KD 0.5f

// PID Gains - Altitude Hold
#define PID_ALT_KP 3.0f
#define PID_ALT_KI 0.5f
#define PID_ALT_KD 1.5f

// PID Gains - GPS Position Hold
#define PID_POS_KP 1.0f
#define PID_POS_KI 0.1f
#define PID_POS_KD 0.5f

// Control Loop
#define LOOP_FREQ 400
#define DT (1.0f / LOOP_FREQ)

// Flight Modes
#define MODE_MANUAL 0
#define MODE_STABILIZE 1
#define MODE_ALTITUDE_HOLD 2
#define MODE_POSITION_HOLD 3
#define MODE_AUTO 4
#define MODE_RTH 5

// Safety Limits
#define MAX_TILT_ANGLE 45.0f
#define RTH_ALTITUDE 20.0f
#define OBSTACLE_DISTANCE 2.0f

// Data Structures
typedef struct {
    float x, y, z;
} Vector3f;

typedef struct {
    float roll, pitch, yaw;
} Euler;

typedef struct {
    double lat, lon;
    float alt;
} GPSPosition;

typedef struct {
    float kp, ki, kd;
    float error, prev_error, integral;
    float output;
    float max_integral;
} PID;

typedef struct {
    uint16_t m1, m2, m3, m4, m5, m6, m7, m8;
} MotorOutputs;

typedef struct {
    Vector3f gyro;
    Vector3f accel;
    Euler angles;
    float temperature;
    uint32_t timestamp;
} IMUData;

typedef struct {
    GPSPosition position;
    float ground_speed;
    float heading;
    uint8_t num_sats;
    bool fix_valid;
} GPSData;

typedef struct {
    float altitude;
    float vertical_speed;
    float pressure;
} BaroData;

typedef struct {
    float distance;
    float angle;
    bool detected;
} ObstacleData;

typedef struct {
    uint16_t throttle;
    Euler setpoint;
    bool armed;
    uint8_t flight_mode;
    float target_altitude;
    GPSPosition target_position;
    GPSPosition home_position;
} FlightCommand;

// Global Variables
static IMUData imu;
static GPSData gps;
static BaroData baro;
static ObstacleData obstacle;
static FlightCommand cmd;
static MotorOutputs motors;

static PID pid_roll, pid_pitch, pid_yaw;
static PID pid_altitude, pid_velocity_z;
static PID pid_pos_n, pid_pos_e;
static PID pid_vel_n, pid_vel_e;

// Thread variables
static THD_WORKING_AREA(waControlThread, 2048);
static thread_t *control_thread = NULL;

// SPI Configuration
static const SPIConfig spi_cfg = {
    .circular = false,
    .slave = false,
    .data_cb = NULL,
    .error_cb = NULL,
    .ssport = IMU_CS_PORT,
    .sspad = IMU_CS_PIN,
    .cr1 = SPI_CR1_BR_2 | SPI_CR1_CPOL | SPI_CR1_CPHA,
    .cr2 = 0
};

// PWM Configuration
static PWMConfig pwm_cfg = {
    .frequency = 1000000,
    .period = 2500,
    .callback = NULL,
    .channels = {
        {PWM_OUTPUT_ACTIVE_HIGH, NULL},
        {PWM_OUTPUT_ACTIVE_HIGH, NULL},
        {PWM_OUTPUT_ACTIVE_HIGH, NULL},
        {PWM_OUTPUT_ACTIVE_HIGH, NULL},
        {PWM_OUTPUT_ACTIVE_HIGH, NULL},
        {PWM_OUTPUT_ACTIVE_HIGH, NULL},
        {PWM_OUTPUT_ACTIVE_HIGH, NULL},
        {PWM_OUTPUT_ACTIVE_HIGH, NULL}
    },
    .cr2 = 0,
    .dier = 0
};

// Function Prototypes
void init_hardware(void);
void init_imu_icm20948(void);
uint8_t spi_read_register(uint8_t reg);
void spi_write_register(uint8_t reg, uint8_t value);
void read_imu_data(IMUData *data);
void compute_angles(IMUData *data);
void init_pid(PID *pid, float kp, float ki, float kd, float max_int);
float update_pid(PID *pid, float setpoint, float measured, float dt);
void stabilize_and_mix(void);
void altitude_hold_controller(void);
void position_hold_controller(void);
void return_to_home_controller(void);
void obstacle_avoidance(void);
void set_motor_pwm(uint8_t motor, uint16_t pulse_us);
void safety_check(void);
float constrain_float(float val, float min, float max);
float wrap_180(float angle);
float wrap_360(float angle);
float get_distance_meters(GPSPosition *pos1, GPSPosition *pos2);
float get_bearing_deg(GPSPosition *from, GPSPosition *to);
static THD_FUNCTION(ControlThread, arg);

/*
 * Initialize Hardware
 */
void init_hardware(void) {
    spiStart(&IMU_SPI_DEVICE, &spi_cfg);
    pwmStart(&PWMD1, &pwm_cfg);
    pwmStart(&PWMD4, &pwm_cfg);
    
    palSetPadMode(IMU_CS_PORT, IMU_CS_PIN, PAL_MODE_OUTPUT_PUSHPULL);
    palSetPad(IMU_CS_PORT, IMU_CS_PIN);
    palSetPadMode(GPIOE, 12, PAL_MODE_OUTPUT_PUSHPULL);
}

/*
 * SPI Communication
 */
uint8_t spi_read_register(uint8_t reg) {
    uint8_t tx_buf[2] = {reg | 0x80, 0x00};
    uint8_t rx_buf[2];
    
    spiSelect(&IMU_SPI_DEVICE);
    spiExchange(&IMU_SPI_DEVICE, 2, tx_buf, rx_buf);
    spiUnselect(&IMU_SPI_DEVICE);
    
    return rx_buf[1];
}

void spi_write_register(uint8_t reg, uint8_t value) {
    uint8_t tx_buf[2] = {reg & 0x7F, value};
    
    spiSelect(&IMU_SPI_DEVICE);
    spiSend(&IMU_SPI_DEVICE, 2, tx_buf);
    spiUnselect(&IMU_SPI_DEVICE);
}

/*
 * Initialize IMU
 */
void init_imu_icm20948(void) {
    chThdSleepMilliseconds(100);
    
    uint8_t who_am_i = spi_read_register(ICM20948_WHO_AM_I);
    if (who_am_i != 0xEA) return;
    
    spi_write_register(ICM20948_PWR_MGMT_1, 0x80);
    chThdSleepMilliseconds(100);
    
    spi_write_register(ICM20948_PWR_MGMT_1, 0x01);
    chThdSleepMilliseconds(10);
    
    spi_write_register(ICM20948_GYRO_CONFIG, 0x00);
    spi_write_register(ICM20948_ACCEL_CONFIG, 0x00);
    chThdSleepMilliseconds(10);
}

/*
 * Read IMU Data
 */
void read_imu_data(IMUData *data) {
    uint8_t raw_data[12];
    int16_t raw[6];
    
    for (int i = 0; i < 6; i++) {
        raw_data[i] = spi_read_register(ICM20948_ACCEL_XOUT_H + i);
    }
    
    for (int i = 0; i < 6; i++) {
        raw_data[i + 6] = spi_read_register(ICM20948_GYRO_XOUT_H + i);
    }
    
    for (int i = 0; i < 6; i++) {
        raw[i] = (raw_data[i * 2] << 8) | raw_data[i * 2 + 1];
    }
    
    data->accel.x = raw[0] / ACCEL_SCALE;
    data->accel.y = raw[1] / ACCEL_SCALE;
    data->accel.z = raw[2] / ACCEL_SCALE;
    
    data->gyro.x = raw[3] / GYRO_SCALE;
    data->gyro.y = raw[4] / GYRO_SCALE;
    data->gyro.z = raw[5] / GYRO_SCALE;
}

/*
 * Compute Orientation (Complementary Filter)
 */
void compute_angles(IMUData *data) {
    static float alpha = 0.98f;
    
    float accel_roll = atan2f(data->accel.y, data->accel.z) * 180.0f / M_PI;
    float accel_pitch = atan2f(-data->accel.x, sqrtf(data->accel.y * data->accel.y + 
                                                       data->accel.z * data->accel.z)) * 180.0f / M_PI;
    
    data->angles.roll += data->gyro.x * DT;
    data->angles.pitch += data->gyro.y * DT;
    data->angles.yaw += data->gyro.z * DT;
    
    data->angles.roll = alpha * data->angles.roll + (1.0f - alpha) * accel_roll;
    data->angles.pitch = alpha * data->angles.pitch + (1.0f - alpha) * accel_pitch;
}

/*
 * Initialize PID
 */
void init_pid(PID *pid, float kp, float ki, float kd, float max_int) {
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->error = 0;
    pid->prev_error = 0;
    pid->integral = 0;
    pid->output = 0;
    pid->max_integral = max_int;
}

/*
 * Update PID
 */
float update_pid(PID *pid, float setpoint, float measured, float dt) {
    pid->error = setpoint - measured;
    pid->integral += pid->error * dt;
    
    pid->integral = constrain_float(pid->integral, -pid->max_integral, pid->max_integral);
    
    float derivative = (pid->error - pid->prev_error) / dt;
    pid->prev_error = pid->error;
    
    pid->output = pid->kp * pid->error + pid->ki * pid->integral + pid->kd * derivative;
    
    return pid->output;
}

/*
 * Altitude Hold Controller
 */
void altitude_hold_controller(void) {
    if (cmd.flight_mode < MODE_ALTITUDE_HOLD) return;
    
    // Two-stage cascade controller
    float altitude_error = cmd.target_altitude - baro.altitude;
    float target_climb_rate = update_pid(&pid_altitude, cmd.target_altitude, baro.altitude, DT);
    target_climb_rate = constrain_float(target_climb_rate, -3.0f, 3.0f);
    
    float throttle_adjust = update_pid(&pid_velocity_z, target_climb_rate, baro.vertical_speed, DT);
    
    cmd.throttle = 1500 + (int16_t)throttle_adjust;
    cmd.throttle = constrain_float(cmd.throttle, MOTOR_MIN, MOTOR_MAX);
}

/*
 * Position Hold Controller
 */
void position_hold_controller(void) {
    if (cmd.flight_mode < MODE_POSITION_HOLD || !gps.fix_valid) return;
    
    // Calculate position error in meters
    float distance = get_distance_meters(&gps.position, &cmd.target_position);
    float bearing = get_bearing_deg(&gps.position, &cmd.target_position);
    
    float error_north = distance * cosf(bearing * M_PI / 180.0f);
    float error_east = distance * sinf(bearing * M_PI / 180.0f);
    
    // Position PID -> target velocity
    float target_vel_n = update_pid(&pid_pos_n, 0, error_north, DT);
    float target_vel_e = update_pid(&pid_pos_e, 0, error_east, DT);
    
    target_vel_n = constrain_float(target_vel_n, -5.0f, 5.0f);
    target_vel_e = constrain_float(target_vel_e, -5.0f, 5.0f);
    
    // Velocity PID -> target angle
    float vel_n = gps.ground_speed * cosf(gps.heading * M_PI / 180.0f);
    float vel_e = gps.ground_speed * sinf(gps.heading * M_PI / 180.0f);
    
    float angle_n = update_pid(&pid_vel_n, target_vel_n, vel_n, DT);
    float angle_e = update_pid(&pid_vel_e, target_vel_e, vel_e, DT);
    
    // Convert to body frame (pitch/roll)
    float heading_rad = imu.angles.yaw * M_PI / 180.0f;
    cmd.setpoint.pitch = -(angle_n * cosf(heading_rad) + angle_e * sinf(heading_rad));
    cmd.setpoint.roll = -(angle_e * cosf(heading_rad) - angle_n * sinf(heading_rad));
    
    cmd.setpoint.pitch = constrain_float(cmd.setpoint.pitch, -25.0f, 25.0f);
    cmd.setpoint.roll = constrain_float(cmd.setpoint.roll, -25.0f, 25.0f);
}

/*
 * Return to Home Controller
 */
void return_to_home_controller(void) {
    if (cmd.flight_mode != MODE_RTH || !gps.fix_valid) return;
    
    float distance = get_distance_meters(&gps.position, &cmd.home_position);
    
    // If close to home, land
    if (distance < 2.0f && baro.altitude < 1.0f) {
        cmd.armed = false;
        return;
    }
    
    // Climb to safe altitude first
    if (baro.altitude < RTH_ALTITUDE) {
        cmd.target_altitude = RTH_ALTITUDE;
    }
    
    // Navigate to home
    cmd.target_position = cmd.home_position;
    position_hold_controller();
    
    // Once home, descend
    if (distance < 3.0f) {
        cmd.target_altitude = 0.5f;
    }
}

/*
 * Obstacle Avoidance (using rangefinder/lidar)
 */
void obstacle_avoidance(void) {
    if (!obstacle.detected) return;
    
    if (obstacle.distance < OBSTACLE_DISTANCE) {
        // Stop forward motion
        if (cmd.setpoint.pitch < 0) {  // If moving forward
            cmd.setpoint.pitch = 0;
        }
        
        // Move away from obstacle
        float avoidance_angle = obstacle.angle + 90.0f;  // Turn 90 degrees
        cmd.setpoint.roll = 10.0f * sinf(avoidance_angle * M_PI / 180.0f);
    }
}

/*
 * Stabilization and Motor Mixing
 */
void stabilize_and_mix(void) {
    if (!cmd.armed) {
        motors.m1 = motors.m2 = motors.m3 = motors.m4 = MOTOR_MIN;
        motors.m5 = motors.m6 = motors.m7 = motors.m8 = MOTOR_MIN;
        return;
    }
    
    // Update attitude PID controllers
    float roll_correction = update_pid(&pid_roll, cmd.setpoint.roll, imu.angles.roll, DT);
    float pitch_correction = update_pid(&pid_pitch, cmd.setpoint.pitch, imu.angles.pitch, DT);
    float yaw_correction = update_pid(&pid_yaw, cmd.setpoint.yaw, imu.angles.yaw, DT);
    
    // Quadcopter X mixing
    float base = cmd.throttle;
    
    motors.m1 = base - roll_correction + pitch_correction - yaw_correction;
    motors.m2 = base + roll_correction + pitch_correction + yaw_correction;
    motors.m3 = base - roll_correction - pitch_correction + yaw_correction;
    motors.m4 = base + roll_correction - pitch_correction - yaw_correction;
    
    // Constrain outputs
    motors.m1 = constrain_float(motors.m1, MOTOR_MIN, MOTOR_MAX);
    motors.m2 = constrain_float(motors.m2, MOTOR_MIN, MOTOR_MAX);
    motors.m3 = constrain_float(motors.m3, MOTOR_MIN, MOTOR_MAX);
    motors.m4 = constrain_float(motors.m4, MOTOR_MIN, MOTOR_MAX);
}

/*
 * Set Motor PWM
 */
void set_motor_pwm(uint8_t motor, uint16_t pulse_us) {
    uint16_t ticks = pulse_us;
    
    if (motor >= 1 && motor <= 4) {
        pwmEnableChannel(&PWMD1, motor - 1, PWM_PERCENTAGE_TO_WIDTH(&PWMD1, ticks));
    } else if (motor >= 5 && motor <= 8) {
        pwmEnableChannel(&PWMD4, motor - 5, PWM_PERCENTAGE_TO_WIDTH(&PWMD4, ticks));
    }
}

/*
 * Safety Checks
 */
void safety_check(void) {
    if (fabsf(imu.angles.roll) > MAX_TILT_ANGLE || fabsf(imu.angles.pitch) > MAX_TILT_ANGLE) {
        cmd.armed = false;
    }
    
    if (isnan(imu.angles.roll) || isnan(imu.angles.pitch)) {
        cmd.armed = false;
    }
    
    // GPS failsafe
    if (cmd.flight_mode >= MODE_POSITION_HOLD && !gps.fix_valid) {
        cmd.flight_mode = MODE_ALTITUDE_HOLD;
    }
    
    // Low battery trigger RTH (implement battery monitoring)
    // if (battery_voltage < BATTERY_MIN) {
    //     cmd.flight_mode = MODE_RTH;
    // }
    
    palWritePad(GPIOE, 12, cmd.armed ? PAL_HIGH : PAL_LOW);
}

/*
 * Utility Functions
 */
float constrain_float(float val, float min, float max) {
    return (val < min) ? min : (val > max) ? max : val;
}

float wrap_180(float angle) {
    while (angle > 180.0f) angle -= 360.0f;
    while (angle < -180.0f) angle += 360.0f;
    return angle;
}

float wrap_360(float angle) {
    while (angle >= 360.0f) angle -= 360.0f;
    while (angle < 0.0f) angle += 360.0f;
    return angle;
}

float get_distance_meters(GPSPosition *pos1, GPSPosition *pos2) {
    float dlat = (pos2->lat - pos1->lat) * M_PI / 180.0f;
    float dlon = (pos2->lon - pos1->lon) * M_PI / 180.0f;
    
    float a = sinf(dlat/2) * sinf(dlat/2) +
              cosf(pos1->lat * M_PI / 180.0f) * cosf(pos2->lat * M_PI / 180.0f) *
              sinf(dlon/2) * sinf(dlon/2);
    
    float c = 2 * atan2f(sqrtf(a), sqrtf(1-a));
    return 6371000.0f * c;  // Earth radius in meters
}

float get_bearing_deg(GPSPosition *from, GPSPosition *to) {
    float dlat = (to->lat - from->lat) * M_PI / 180.0f;
    float dlon = (to->lon - from->lon) * M_PI / 180.0f;
    
    float y = sinf(dlon) * cosf(to->lat * M_PI / 180.0f);
    float x = cosf(from->lat * M_PI / 180.0f) * sinf(to->lat * M_PI / 180.0f) -
              sinf(from->lat * M_PI / 180.0f) * cosf(to->lat * M_PI / 180.0f) * cosf(dlon);
    
    return wrap_360(atan2f(y, x) * 180.0f / M_PI);
}

/*
 * Main Control Thread
 */
static THD_FUNCTION(ControlThread, arg) {
    (void)arg;
    chRegSetThreadName("Control");
    
    systime_t prev_time = chVTGetSystemTime();
    
    while (true) {
        read_imu_data(&imu);
        compute_angles(&imu);
        
        // Execute flight mode logic
        switch (cmd.flight_mode) {
            case MODE_ALTITUDE_HOLD:
            case MODE_POSITION_HOLD:
            case MODE_AUTO:
                altitude_hold_controller();
                break;
            
            case MODE_RTH:
                return_to_home_controller();
                altitude_hold_controller();
                break;
        }
        
        if (cmd.flight_mode >= MODE_POSITION_HOLD) {
            position_hold_controller();
        }
        
        obstacle_avoidance();
        safety_check();
        stabilize_and_mix();
        
        set_motor_pwm(1, motors.m1);
        set_motor_pwm(2, motors.m2);
        set_motor_pwm(3, motors.m3);
        set_motor_pwm(4, motors.m4);
        
        prev_time = chThdSleepUntilWindowed(prev_time, prev_time + TIME_US2I(1000000 / LOOP_FREQ));
    }
}

/*
 * System Initialization
 */
void control_system_init(void) {
    init_hardware();
    init_imu_icm20948();
    
    // Initialize attitude PIDs
    init_pid(&pid_roll, PID_ROLL_KP, PID_ROLL_KI, PID_ROLL_KD, 400.0f);
    init_pid(&pid_pitch, PID_PITCH_KP, PID_PITCH_KI, PID_PITCH_KD, 400.0f);
    init_pid(&pid_yaw, PID_YAW_KP, PID_YAW_KI, PID_YAW_KD, 400.0f);
    
    // Initialize altitude PIDs
    init_pid(&pid_altitude, PID_ALT_KP, PID_ALT_KI, PID_ALT_KD, 500.0f);
    init_pid(&pid_velocity_z, 2.0f, 0.1f, 0.5f, 300.0f);
    
    // Initialize position PIDs
    init_pid(&pid_pos_n, PID_POS_KP, PID_POS_KI, PID_POS_KD, 100.0f);
    init_pid(&pid_pos_e, PID_POS_KP, PID_POS_KI, PID_POS_KD, 100.0f);
    init_pid(&pid_vel_n, 0.5f, 0.05f, 0.1f, 50.0f);
    init_pid(&pid_vel_e, 0.5f, 0.05f, 0.1f, 50.0f);
    
    cmd.throttle = MOTOR_MIN;
    cmd.setpoint.roll = 0;
    cmd.setpoint.pitch = 0;
    cmd.setpoint.yaw = 0;
    cmd.armed = false;
    cmd.flight_mode = MODE_STABILIZE;
    cmd.target_altitude = 0;
    
    imu.angles.roll = 0;
    imu.angles.pitch = 0;
    imu.angles.yaw = 0;
    
    control_thread = chThdCreateStatic(waControlThread, sizeof(waControlThread),
                                       NORMALPRIO + 1, ControlThread, NULL);
}

/*
 * API Functions
 */
void set_flight_mode(uint8_t mode) {
    cmd.flight_mode = mode;
}

void set_target_altitude(float altitude_m) {
    cmd.target_altitude = altitude_m;
}

void set_target_position(double lat, double lon) {
    cmd.target_position.lat = lat;
    cmd.target_position.lon = lon;
}

void set_home_position(double lat, double lon, float alt) {
    cmd.home_position.lat = lat;
    cmd.home_position.lon = lon;
    cmd.home_position.alt = alt;
}

void update_gps_data(double lat, double lon, float alt, float speed, float heading, uint8_t sats) {
    gps.position.lat = lat;
    gps.position.lon = lon;
    gps.position.alt = alt;
    gps.ground_speed = speed;
    gps.heading = heading;
    gps.num_sats = sats;
    gps.fix_valid = (sats >= 6);
}

void update_baro_data(float altitude, float vertical_speed) {
    baro.altitude = altitude;
    baro.vertical_speed = vertical_speed;
}

void update_obstacle_data(float distance, float angle, bool detected) {
    obstacle.distance = distance;
    obstacle.angle = angle;
    obstacle.detected = detected;
}

void arm_motors(void) {
    cmd.armed = true;
}

void disarm_motors(void) {
    cmd.armed = false;
}

void trigger_return_to_home(void) {
    cmd.flight_mode = MODE_RTH;
}

IMUData get_imu_data(void) {
    return imu;
}

GPSData get_gps_data(void) {
    return gps;
}

MotorOutputs get_motor_outputs(void) {
    return motors;
}