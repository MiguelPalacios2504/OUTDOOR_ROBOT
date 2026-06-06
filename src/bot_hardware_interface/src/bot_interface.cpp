#include "bot_hardware_interface/bot_interface.hpp"

#include <array>
#include <algorithm>
#include <cmath>

#include "pluginlib/class_list_macros.hpp"
#include "rclcpp/clock.hpp"

namespace bot_hardware_interface
{
namespace
{
constexpr size_t kNumSteerJoints = 4;
constexpr size_t kNumWheelJoints = 4;
constexpr size_t kNumJoints = kNumSteerJoints + kNumWheelJoints;

constexpr std::array<const char *, kNumSteerJoints> kSteerJointOrder = {
  "f_left_steer", "f_right_steer", "b_leftsteer", "b_rightsteer"};
constexpr std::array<const char *, kNumWheelJoints> kWheelJointOrder = {
  "f_leftwheel", "f_rightwheel", "b_leftwheel", "b_rightwheel"};
}  // namespace

BotInterface::BotInterface() = default;

BotInterface::~BotInterface() = default;

CallbackReturn BotInterface::on_init(const hardware_interface::HardwareInfo & hardware_info)
{
  if (hardware_interface::SystemInterface::on_init(hardware_info) != CallbackReturn::SUCCESS) {
    return CallbackReturn::ERROR;
  }

  const auto commands_topic_it = info_.hardware_parameters.find("joint_commands_topic");
  if (commands_topic_it != info_.hardware_parameters.end()) {
    joint_commands_topic_ = commands_topic_it->second;
  }

  const auto states_topic_it = info_.hardware_parameters.find("joint_states_topic");
  if (states_topic_it != info_.hardware_parameters.end()) {
    joint_states_topic_ = states_topic_it->second;
  }

  const auto timeout_it = info_.hardware_parameters.find("state_timeout_sec");
  if (timeout_it != info_.hardware_parameters.end()) {
    state_timeout_sec_ = std::stod(timeout_it->second);
  }

  if (!parse_joint_layout()) {
    return CallbackReturn::ERROR;
  }

  hw_positions_.assign(info_.joints.size(), 0.0);
  hw_velocities_.assign(info_.joints.size(), 0.0);
  hw_steering_commands_.assign(kNumSteerJoints, 0.0);
  hw_wheel_commands_.assign(kNumWheelJoints, 0.0);

  return CallbackReturn::SUCCESS;
}

CallbackReturn BotInterface::on_activate(const rclcpp_lifecycle::State & /*previous_state*/)
{
  auto node = get_node();
  if (!node) {
    RCLCPP_ERROR(rclcpp::get_logger("BotInterface"), "Loaned node unavailable during activation.");
    return CallbackReturn::ERROR;
  }

  joint_states_sub_ = node->create_subscription<std_msgs::msg::Float64MultiArray>(
    joint_states_topic_, rclcpp::SensorDataQoS(),
    std::bind(&BotInterface::joint_states_callback, this, std::placeholders::_1));

  joint_commands_pub_ = node->create_publisher<std_msgs::msg::Float64MultiArray>(
    joint_commands_topic_, rclcpp::SystemDefaultsQoS());

  active_.store(true);
  publish_zero_commands();

  const auto activation_deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
  while (!joint_states_received_ && std::chrono::steady_clock::now() < activation_deadline) {
    rclcpp::sleep_for(std::chrono::milliseconds(50));
  }

  if (!joint_states_received_) {
    RCLCPP_WARN(
      rclcpp::get_logger("BotInterface"),
      "No %s received within 5 s; continuing activation anyway.",
      joint_states_topic_.c_str());
  }

  RCLCPP_INFO(
    rclcpp::get_logger("BotInterface"),
    "Activated. commands=%s states=%s",
    joint_commands_topic_.c_str(), joint_states_topic_.c_str());

  return CallbackReturn::SUCCESS;
}

CallbackReturn BotInterface::on_deactivate(const rclcpp_lifecycle::State & /*previous_state*/)
{
  active_.store(false);
  publish_zero_commands();

  joint_states_sub_.reset();
  joint_commands_pub_.reset();
  joint_states_received_ = false;

  return CallbackReturn::SUCCESS;
}

std::vector<hardware_interface::StateInterface> BotInterface::export_state_interfaces()
{
  std::vector<hardware_interface::StateInterface> state_interfaces;
  state_interfaces.reserve(info_.joints.size() * 2);

  for (size_t joint_index = 0; joint_index < info_.joints.size(); ++joint_index) {
    const auto & joint = info_.joints[joint_index];
    state_interfaces.emplace_back(
      joint.name, hardware_interface::HW_IF_POSITION, &hw_positions_[joint_index]);
    state_interfaces.emplace_back(
      joint.name, hardware_interface::HW_IF_VELOCITY, &hw_velocities_[joint_index]);
  }

  return state_interfaces;
}

std::vector<hardware_interface::CommandInterface> BotInterface::export_command_interfaces()
{
  std::vector<hardware_interface::CommandInterface> command_interfaces;
  command_interfaces.reserve(kNumJoints);

  for (size_t index = 0; index < kNumSteerJoints; ++index) {
    command_interfaces.emplace_back(
      kSteerJointOrder[index], hardware_interface::HW_IF_POSITION,
      &hw_steering_commands_[index]);
  }

  for (size_t index = 0; index < kNumWheelJoints; ++index) {
    command_interfaces.emplace_back(
      kWheelJointOrder[index], hardware_interface::HW_IF_VELOCITY, &hw_wheel_commands_[index]);
  }

  return command_interfaces;
}

hardware_interface::return_type BotInterface::read(
  const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
{
  std_msgs::msg::Float64MultiArray latest_states;
  std::chrono::steady_clock::time_point latest_time;
  bool received = false;

  {
    std::lock_guard<std::mutex> lock(joint_states_mutex_);
    if (joint_states_received_) {
      latest_states = latest_joint_states_;
      latest_time = last_joint_states_time_;
      received = true;
    }
  }

  if (!received) {
    return hardware_interface::return_type::OK;
  }

  if (state_timeout_sec_ > 0.0) {
    const auto age = std::chrono::duration<double>(
      std::chrono::steady_clock::now() - latest_time).count();
    if (age > state_timeout_sec_) {
      RCLCPP_WARN_THROTTLE(
        rclcpp::get_logger("BotInterface"), *get_node()->get_clock(), 2000,
        "%s stale (%.3f s old).", joint_states_topic_.c_str(), age);
      return hardware_interface::return_type::ERROR;
    }
  }

  if (latest_states.data.size() < kNumJoints) {
    RCLCPP_WARN_THROTTLE(
      rclcpp::get_logger("BotInterface"), *get_node()->get_clock(), 2000,
      "%s expected %zu values, got %zu.",
      joint_states_topic_.c_str(), kNumJoints, latest_states.data.size());
    return hardware_interface::return_type::ERROR;
  }

  for (size_t index = 0; index < kNumSteerJoints; ++index) {
    const auto joint_it = steer_index_by_joint_.find(kSteerJointOrder[index]);
    if (joint_it == steer_index_by_joint_.end()) {
      continue;
    }
    const size_t joint_index = joint_it->second;
    hw_positions_[joint_index] = latest_states.data[index];
    hw_velocities_[joint_index] = 0.0;
  }

  for (size_t index = 0; index < kNumWheelJoints; ++index) {
    const auto joint_it = wheel_index_by_joint_.find(kWheelJointOrder[index]);
    if (joint_it == wheel_index_by_joint_.end()) {
      continue;
    }
    const size_t joint_index = joint_it->second;
    hw_velocities_[joint_index] = latest_states.data[kNumSteerJoints + index];
  }

  return hardware_interface::return_type::OK;
}

hardware_interface::return_type BotInterface::write(
  const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
{
  if (!active_.load() || !joint_commands_pub_) {
    return hardware_interface::return_type::OK;
  }

  std_msgs::msg::Float64MultiArray command_msg;
  command_msg.data.reserve(kNumJoints);

  for (size_t index = 0; index < kNumSteerJoints; ++index) {
    command_msg.data.push_back(hw_steering_commands_[index]);
  }
  for (size_t index = 0; index < kNumWheelJoints; ++index) {
    command_msg.data.push_back(hw_wheel_commands_[index]);
  }

  joint_commands_pub_->publish(command_msg);
  return hardware_interface::return_type::OK;
}

void BotInterface::joint_states_callback(
  const std_msgs::msg::Float64MultiArray::SharedPtr msg)
{
  if (!msg) {
    return;
  }

  std::lock_guard<std::mutex> lock(joint_states_mutex_);
  latest_joint_states_ = *msg;
  last_joint_states_time_ = std::chrono::steady_clock::now();
  joint_states_received_ = true;
}

void BotInterface::publish_zero_commands()
{
  if (!joint_commands_pub_) {
    return;
  }

  std_msgs::msg::Float64MultiArray command_msg;
  command_msg.data.assign(kNumJoints, 0.0);
  joint_commands_pub_->publish(command_msg);
}

bool BotInterface::parse_joint_layout()
{
  steer_index_by_joint_.clear();
  wheel_index_by_joint_.clear();

  for (size_t joint_index = 0; joint_index < info_.joints.size(); ++joint_index) {
    const auto & joint_name = info_.joints[joint_index].name;

    for (size_t steer_index = 0; steer_index < kNumSteerJoints; ++steer_index) {
      if (joint_name == kSteerJointOrder[steer_index]) {
        steer_index_by_joint_[joint_name] = joint_index;
      }
    }

    for (size_t wheel_index = 0; wheel_index < kNumWheelJoints; ++wheel_index) {
      if (joint_name == kWheelJointOrder[wheel_index]) {
        wheel_index_by_joint_[joint_name] = joint_index;
      }
    }
  }

  if (steer_index_by_joint_.size() != kNumSteerJoints ||
    wheel_index_by_joint_.size() != kNumWheelJoints)
  {
    RCLCPP_ERROR(
      rclcpp::get_logger("BotInterface"),
      "Expected %zu steering and %zu wheel joints in URDF, found %zu and %zu.",
      kNumSteerJoints, kNumWheelJoints, steer_index_by_joint_.size(),
      wheel_index_by_joint_.size());
    return false;
  }

  return true;
}

}  // namespace bot_hardware_interface

PLUGINLIB_EXPORT_CLASS(
  bot_hardware_interface::BotInterface, hardware_interface::SystemInterface)
