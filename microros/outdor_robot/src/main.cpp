#include <Arduino.h>
#include "motor_controller.hpp"

#include <micro_ros_platformio.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <std_msgs/msg/float64_multi_array.h>

#define PWM_PIN1      19
#define DIR_PIN1      13
#define ENCODER_PIN1  27
#define PWM_PIN2      18
#define DIR_PIN2      21
#define ENCODER_PIN2  23
#define PWM_PIN3      16
#define DIR_PIN3      34
#define ENCODER_PIN3  32
#define PWM_PIN4      5
#define DIR_PIN4      17
#define ENCODER_PIN4  33

#define NUM_JOINTS    8
#define MOTOR1_WHEEL_INDEX  4
#define MOTOR2_WHEEL_INDEX  5
#define MOTOR3_WHEEL_INDEX  6
#define MOTOR4_WHEEL_INDEX  7

#define STATES_PUBLISH_MS   100
#define CMD_TIMEOUT_MS     1000
#define RETRY_MS           1000

const float COUNTS_PER_REV = 800.0f;

MotorController motor1(0, PWM_PIN1, DIR_PIN1, ENCODER_PIN1, COUNTS_PER_REV);
MotorController motor2(1, PWM_PIN2, DIR_PIN2, ENCODER_PIN2, COUNTS_PER_REV);
MotorController motor3(2, PWM_PIN3, DIR_PIN3, ENCODER_PIN3, COUNTS_PER_REV);
MotorController motor4(3, PWM_PIN4, DIR_PIN4, ENCODER_PIN4, COUNTS_PER_REV);

rcl_allocator_t allocator;
rclc_support_t support;
rcl_node_t node;
rcl_publisher_t publisher;
rcl_subscription_t subscriber;
rclc_executor_t executor;

std_msgs__msg__Float64MultiArray cmd_msg;
std_msgs__msg__Float64MultiArray state_msg;
static double cmd_data[NUM_JOINTS];
static double state_data[NUM_JOINTS];

bool ros_ok = false;
bool motors_ok = false;
unsigned long last_retry = 0;
unsigned long last_cmd_ms = 0;

static void initBuffer(std_msgs__msg__Float64MultiArray * msg, double * buf) {
    msg->data.data = buf;
    msg->data.capacity = NUM_JOINTS;
    msg->data.size = NUM_JOINTS;
    msg->layout.dim.data = nullptr;
    msg->layout.dim.capacity = 0;
    msg->layout.dim.size = 0;
    msg->layout.data_offset = 0;
    for (int i = 0; i < NUM_JOINTS; ++i) {
        buf[i] = 0.0;
    }
}

static float rpmToRad(float rpm) {
    return rpm * (2.0f * PI / 60.0f);
}

static float radToRpm(float rad) {
    return rad * (60.0f / (2.0f * PI));
}

void cmdCb(const void * raw) {
    const auto * msg = (const std_msgs__msg__Float64MultiArray *)raw;
    if (msg->data.size < NUM_JOINTS) {
        return;
    }
    motor1.setTargetRPM(-radToRpm((float)msg->data.data[MOTOR1_WHEEL_INDEX]));
    motor2.setTargetRPM(-radToRpm((float)msg->data.data[MOTOR2_WHEEL_INDEX]));
    motor3.setTargetRPM(radToRpm((float)msg->data.data[MOTOR3_WHEEL_INDEX]));
    motor4.setTargetRPM(radToRpm((float)msg->data.data[MOTOR4_WHEEL_INDEX]));
    last_cmd_ms = millis();
}

static void startMotors() {
    if (motors_ok) {
        return;
    }
    motor1.begin();
    motor2.begin();
    motor3.begin();
    motor4.begin();
    motor1.setFeedForward(0.85f);
    motor2.setFeedForward(0.85f);
    motor3.setFeedForward(0.85f);
    motor4.setFeedForward(0.85f);
    motor1.setPI(0.08f, 0.01f);
    motor2.setPI(0.08f, 0.01f);
    motor3.setPI(0.06f, 0.008f);
    motor4.setPI(0.06f, 0.008f);
    motors_ok = true;
}

static bool startRos() {
    if (ros_ok) {
        return true;
    }

    allocator = rcl_get_default_allocator();
    if (rclc_support_init(&support, 0, nullptr, &allocator) != RCL_RET_OK) {
        return false;
    }
    if (rclc_node_init_default(&node, "outdoor_robot_firmware", "", &support) != RCL_RET_OK) {
        rclc_support_fini(&support);
        return false;
    }

    initBuffer(&cmd_msg, cmd_data);
    initBuffer(&state_msg, state_data);

    if (rclc_publisher_init_default(
            &publisher, &node,
            ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float64MultiArray),
            "hw/joint_states") != RCL_RET_OK) {
        rcl_node_fini(&node);
        rclc_support_fini(&support);
        return false;
    }
    if (rclc_subscription_init_default(
            &subscriber, &node,
            ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float64MultiArray),
            "hw/joint_commands") != RCL_RET_OK) {
        rcl_publisher_fini(&publisher, &node);
        rcl_node_fini(&node);
        rclc_support_fini(&support);
        return false;
    }
    if (rclc_executor_init(&executor, &support.context, 1, &allocator) != RCL_RET_OK) {
        rcl_subscription_fini(&subscriber, &node);
        rcl_publisher_fini(&publisher, &node);
        rcl_node_fini(&node);
        rclc_support_fini(&support);
        return false;
    }
    if (rclc_executor_add_subscription(
            &executor, &subscriber, &cmd_msg, &cmdCb, ON_NEW_DATA) != RCL_RET_OK) {
        rclc_executor_fini(&executor);
        rcl_subscription_fini(&subscriber, &node);
        rcl_publisher_fini(&publisher, &node);
        rcl_node_fini(&node);
        rclc_support_fini(&support);
        return false;
    }

    last_cmd_ms = millis();
    ros_ok = true;
    startMotors();
    return true;
}

void setup() {
    Serial.begin(115200);
    set_microros_serial_transports(Serial);
    delay(2000);
    last_retry = 0;
}

void loop() {
    if (!ros_ok) {
        if (millis() - last_retry >= RETRY_MS) {
            last_retry = millis();
            startRos();
        }
        return;
    }

    rclc_executor_spin_some(&executor, RCL_MS_TO_NS(100));

    if (motors_ok && last_cmd_ms > 0 && (millis() - last_cmd_ms > CMD_TIMEOUT_MS)) {
        motor1.setTargetRPM(0);
        motor2.setTargetRPM(0);
        motor3.setTargetRPM(0);
        motor4.setTargetRPM(0);
    }

    if (motors_ok) {
        motor1.update();
        motor2.update();
        motor3.update();
        motor4.update();
    }

    static unsigned long last_pub = 0;
    if (millis() - last_pub < STATES_PUBLISH_MS) {
        return;
    }
    last_pub = millis();

    for (int i = 0; i < NUM_JOINTS; ++i) {
        state_data[i] = 0.0;
    }
    if (motors_ok) {
        state_data[MOTOR1_WHEEL_INDEX] = rpmToRad(-motor1.getRPM());
        state_data[MOTOR2_WHEEL_INDEX] = rpmToRad(-motor2.getRPM());
        state_data[MOTOR3_WHEEL_INDEX] = rpmToRad(motor3.getRPM());
        state_data[MOTOR4_WHEEL_INDEX] = rpmToRad(motor4.getRPM());
    }
    state_msg.data.size = NUM_JOINTS;
    rcl_publish(&publisher, &state_msg, nullptr);
}
