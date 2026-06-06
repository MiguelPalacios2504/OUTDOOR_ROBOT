#ifndef BOT_HARDWARE_INTERFACE__BOT_INTERFACE_HPP_
#define BOT_HARDWARE_INTERFACE__BOT_INTERFACE_HPP_

#include <atomic>
#include <chrono>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

#include "hardware_interface/handle.hpp"
#include "hardware_interface/hardware_info.hpp"
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_lifecycle/state.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"

namespace bot_hardware_interface
{
using CallbackReturn = rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;

class BotInterface : public hardware_interface::SystemInterface
{
public:
  BotInterface();
  ~BotInterface() override;

  CallbackReturn on_init(const hardware_interface::HardwareInfo & hardware_info) override;
  CallbackReturn on_activate(const rclcpp_lifecycle::State & previous_state) override;
  CallbackReturn on_deactivate(const rclcpp_lifecycle::State & previous_state) override;

  std::vector<hardware_interface::StateInterface> export_state_interfaces() override;
  std::vector<hardware_interface::CommandInterface> export_command_interfaces() override;

  hardware_interface::return_type read(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

  hardware_interface::return_type write(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

private:
  static constexpr size_t kNumSteerJoints = 4;
  static constexpr size_t kNumWheelJoints = 4;
  static constexpr size_t kNumJoints = kNumSteerJoints + kNumWheelJoints;

  void joint_states_callback(const std_msgs::msg::Float64MultiArray::SharedPtr msg);
  void publish_zero_commands();
  bool parse_joint_layout();

  std::string joint_commands_topic_{"/hw/joint_commands"};
  std::string joint_states_topic_{"/hw/joint_states"};
  double state_timeout_sec_{0.2};

  std::vector<double> hw_positions_;
  std::vector<double> hw_velocities_;
  std::vector<double> hw_steering_commands_;
  std::vector<double> hw_wheel_commands_;

  std::unordered_map<std::string, size_t> steer_index_by_joint_;
  std::unordered_map<std::string, size_t> wheel_index_by_joint_;

  rclcpp::Subscription<std_msgs::msg::Float64MultiArray>::SharedPtr joint_states_sub_;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr joint_commands_pub_;

  std::mutex joint_states_mutex_;
  std_msgs::msg::Float64MultiArray latest_joint_states_;
  std::chrono::steady_clock::time_point last_joint_states_time_;
  bool joint_states_received_{false};
  std::atomic<bool> active_{false};
};

}  // namespace bot_hardware_interface

#endif  // BOT_HARDWARE_INTERFACE__BOT_INTERFACE_HPP_
