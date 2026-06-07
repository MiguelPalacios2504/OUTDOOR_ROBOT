#include <Arduino.h>
#include "motor_controller.hpp"

#include <micro_ros_platformio.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <std_msgs/msg/float64_multi_array.h>

#define PWM_PIN1      18
#define DIR_PIN1      21
#define ENCODER_PIN1  23

#define PWM_PIN2      19
#define DIR_PIN2      22
#define ENCODER_PIN2  27

#define NUM_STEER     4
#define NUM_WHEEL     4
#define NUM_JOINTS    (NUM_STEER + NUM_WHEEL)

#define MOTOR1_WHEEL_INDEX  4
#define MOTOR2_WHEEL_INDEX  5

#define AGENT_PING_MS         2000
#define AGENT_PING_TIMEOUT_MS  200
#define AGENT_PING_RETRIES       3
#define STATES_PUBLISH_MS       10
#define CMD_TIMEOUT_MS          1000

// micro-ROS: topic names without leading slash (matches /hw/* on ROS 2 side).
#define TOPIC_JOINT_COMMANDS  "hw/joint_commands"
#define TOPIC_JOINT_STATES    "hw/joint_states"

MotorController motor1(0, PWM_PIN1, DIR_PIN1, ENCODER_PIN1);
MotorController motor2(1, PWM_PIN2, DIR_PIN2, ENCODER_PIN2);

rcl_node_t node;
rclc_executor_t executor;
rcl_allocator_t allocator;
rclc_support_t support;
rcl_publisher_t publisher;
rcl_subscription_t subscriber;
std_msgs__msg__Float64MultiArray inp_msg;
std_msgs__msg__Float64MultiArray out_msg;

bool microros_initialized = false;
unsigned long last_ping = 0;
uint32_t last_cmd_ms = 0;

static void initMsgBuffer(std_msgs__msg__Float64MultiArray * msg) {
    msg->data.data = (double *)malloc(NUM_JOINTS * sizeof(double));
    msg->data.capacity = NUM_JOINTS;
    msg->data.size = NUM_JOINTS;

    msg->layout.dim.data = (std_msgs__msg__MultiArrayDimension *)malloc(
        sizeof(std_msgs__msg__MultiArrayDimension));
    msg->layout.dim.capacity = 1;
    msg->layout.dim.size = 0;
    msg->layout.data_offset = 0;

    for (size_t i = 0; i < NUM_JOINTS; ++i) {
        msg->data.data[i] = 0.0;
    }
}

static void freeMsgBuffer(std_msgs__msg__Float64MultiArray * msg) {
    if (msg->data.data != nullptr) {
        free(msg->data.data);
        msg->data.data = nullptr;
    }
    msg->data.size = 0;
    msg->data.capacity = 0;

    if (msg->layout.dim.data != nullptr) {
        free(msg->layout.dim.data);
        msg->layout.dim.data = nullptr;
    }
    msg->layout.dim.size = 0;
    msg->layout.dim.capacity = 0;
}

static float rpmToRadPerSec(float rpm) {
    return rpm * (2.0f * PI / 60.0f);
}

static float radPerSecToRpm(float rad_per_sec) {
    return rad_per_sec * (60.0f / (2.0f * PI));
}

void cmd_callback(const void * msg_in) {
    const std_msgs__msg__Float64MultiArray * msg =
        (const std_msgs__msg__Float64MultiArray *)msg_in;

    if (msg->data.size < NUM_JOINTS) {
        return;
    }

    motor1.setTargetRPM(radPerSecToRpm((float)msg->data.data[MOTOR1_WHEEL_INDEX]));
    motor2.setTargetRPM(radPerSecToRpm((float)msg->data.data[MOTOR2_WHEEL_INDEX]));
    last_cmd_ms = millis();
}

bool setup_micro_ros() {
    allocator = rcl_get_default_allocator();

    if (rclc_support_init(&support, 0, nullptr, &allocator) != RCL_RET_OK) {
        return false;
    }
    if (rclc_node_init_default(&node, "outdoor_robot_firmware", "", &support) != RCL_RET_OK) {
        rclc_support_fini(&support);
        return false;
    }

    initMsgBuffer(&inp_msg);
    initMsgBuffer(&out_msg);
    if (inp_msg.data.data == nullptr || out_msg.data.data == nullptr) {
        rcl_node_fini(&node);
        rclc_support_fini(&support);
        return false;
    }

    if (rclc_publisher_init_default(
            &publisher,
            &node,
            ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float64MultiArray),
            TOPIC_JOINT_STATES) != RCL_RET_OK) {
        freeMsgBuffer(&inp_msg);
        freeMsgBuffer(&out_msg);
        rcl_node_fini(&node);
        rclc_support_fini(&support);
        return false;
    }

    if (rclc_subscription_init_default(
            &subscriber,
            &node,
            ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float64MultiArray),
            TOPIC_JOINT_COMMANDS) != RCL_RET_OK) {
        rcl_publisher_fini(&publisher, &node);
        freeMsgBuffer(&inp_msg);
        freeMsgBuffer(&out_msg);
        rcl_node_fini(&node);
        rclc_support_fini(&support);
        return false;
    }

    if (rclc_executor_init(&executor, &support.context, 1, &allocator) != RCL_RET_OK) {
        rcl_subscription_fini(&subscriber, &node);
        rcl_publisher_fini(&publisher, &node);
        freeMsgBuffer(&inp_msg);
        freeMsgBuffer(&out_msg);
        rcl_node_fini(&node);
        rclc_support_fini(&support);
        return false;
    }

    if (rclc_executor_add_subscription(
            &executor,
            &subscriber,
            &inp_msg,
            cmd_callback,
            ON_NEW_DATA) != RCL_RET_OK) {
        rclc_executor_fini(&executor);
        rcl_subscription_fini(&subscriber, &node);
        rcl_publisher_fini(&publisher, &node);
        freeMsgBuffer(&inp_msg);
        freeMsgBuffer(&out_msg);
        rcl_node_fini(&node);
        rclc_support_fini(&support);
        return false;
    }

    last_cmd_ms = millis();
    microros_initialized = true;
    return true;
}

void deinit_micro_ros() {
    if (!microros_initialized) {
        return;
    }

    motor1.setTargetRPM(0.0);
    motor2.setTargetRPM(0.0);

    rclc_executor_fini(&executor);
    rcl_subscription_fini(&subscriber, &node);
    rcl_publisher_fini(&publisher, &node);
    rcl_node_fini(&node);
    rclc_support_fini(&support);

    freeMsgBuffer(&inp_msg);
    freeMsgBuffer(&out_msg);

    microros_initialized = false;
}

void setup() {
    Serial.begin(115200);
    delay(500);

    motor1.begin();
    motor1.setPID(0.5, 0.35, 0.0);
    motor1.setTargetRPM(0.0);

    motor2.begin();
    motor2.setPID(0.5, 0.35, 0.0);
    motor2.setTargetRPM(0.0);

    set_microros_serial_transports(Serial);
    delay(2000);

    if (rmw_uros_ping_agent(500, 3) == RMW_RET_OK) {
        setup_micro_ros();
    }
}

static bool pingAgent() {
    return rmw_uros_ping_agent(AGENT_PING_TIMEOUT_MS, AGENT_PING_RETRIES) == RMW_RET_OK;
}

void loop() {
    if (millis() - last_ping >= AGENT_PING_MS) {
        last_ping = millis();
        const bool agent_alive = pingAgent();

        if (agent_alive && !microros_initialized) {
            setup_micro_ros();
        } else if (!agent_alive && microros_initialized) {
            deinit_micro_ros();
        }
    }

    if (microros_initialized) {
        rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));
    }

    if (last_cmd_ms > 0 && (millis() - last_cmd_ms > CMD_TIMEOUT_MS)) {
        motor1.setTargetRPM(0.0);
        motor2.setTargetRPM(0.0);
    }

    motor1.update();
    motor2.update();

    static uint32_t last_states_ms = 0;
    if (microros_initialized && (millis() - last_states_ms >= STATES_PUBLISH_MS)) {
        last_states_ms = millis();

        for (size_t i = 0; i < NUM_STEER; ++i) {
            out_msg.data.data[i] = 0.0;
        }

        out_msg.data.data[MOTOR1_WHEEL_INDEX] = rpmToRadPerSec(motor1.getCurrentRPM());
        out_msg.data.data[MOTOR2_WHEEL_INDEX] = rpmToRadPerSec(motor2.getCurrentRPM());
        out_msg.data.data[6] = 0.0;
        out_msg.data.data[7] = 0.0;
        out_msg.data.size = NUM_JOINTS;

        rcl_publish(&publisher, &out_msg, NULL);
    }
}
