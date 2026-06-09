#include <Arduino.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <std_msgs/msg/float32_multi_array.h>

// Hardware UART setup for communicating with ESP32 #2
#define TX_PIN_TO_ESP2 17
#define RX_PIN_FROM_ESP2 16
#define ESP_BAUD 115200

rclc_executor_t executor;
rcl_node_t node;
rcl_allocator_t allocator;
rcl_support_t support;
rcl_subscription_t speed_sub;
std_msgs__msg__Float32MultiArray speed_msg;

// Callback: Fires immediately when the Pi sends new speeds
void speed_callback(const void *msgin) {
    const auto* msg = (const std_msgs__msg__Float32MultiArray*)msgin;
    
    // Safety check: Ensure the Pi sent exactly 4 motor values
    if (msg->data.size < 4) return;

    // Isolate the 4 calculated wheel speeds from the Pi
    float m11 = msg->data.data[0];
    float m12 = msg->data.data[1];
    float m13 = msg->data.data[2];
    float m14 = msg->data.data[3];

    // Pass the raw speeds through to ESP32 #2 via UART
    // Format: $M11,M12,M13,M14;
    Serial2.printf("$%.2f,%.2f,%.2f,%.2f;\n", m11, m12, m13, m14);
}

void setup() {
    Serial.begin(115200); // Standard micro-ROS USB/UART link to Raspberry Pi
    Serial2.begin(ESP_BAUD, SERIAL_8N1, RX_PIN_FROM_ESP2, TX_PIN_TO_ESP2);

    allocator = rcl_get_default_allocator();
    rcl_init_options_t init_options = rcl_get_zero_initialized_init_options();
    rcl_init_options_init(&init_options, allocator);
    
    if (rclc_support_init_with_options(&support, 0, NULL, &init_options, &allocator) != RCL_RET_OK) return;
    rclc_node_init_default(&node, "ros_uart_bridge", "", &support);

    // Initialize dynamic memory allocations required for multi-array types in C micro-ROS
    static float data_buffer[4];
    speed_msg.data.data = data_buffer;
    speed_msg.data.capacity = 4;

    // Subscribe to the calculated motor speed array
    rclc_subscription_init_default(
        &speed_sub, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32MultiArray),
        "motor_speeds"
    );

    rclc_executor_init(&executor, &support.context, 1, &allocator);
    rclc_executor_add_subscription(&executor, &speed_sub, &speed_msg, &speed_callback, ON_NEW_DATA);
}

void loop() {
    rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));
    delay(5); // Fast loop execution to minimize pass-through latency
}