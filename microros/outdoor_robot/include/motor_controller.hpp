#ifndef MOTOR_CONTROLLER_HPP
#define MOTOR_CONTROLLER_HPP

#include <Arduino.h>

class MotorController {
public:
    MotorController(
        int motorId,
        uint8_t pwmPin,
        uint8_t dirPin,
        uint8_t encoderPin,
        float countsPerRev
    );

    void begin();
    bool update();

    void setTargetRPM(float rpm);
    void setPI(float kp, float ki);
    void setFeedForward(float pwmPerRPM);

    float getTargetRPM() const;
    float getRPM() const;
    int getPWM() const;
    long getLastPulses() const;

private:
    int motorId_;

    uint8_t pwmPin_;
    uint8_t dirPin_;
    uint8_t encoderPin_;

    float countsPerRev_;

    volatile long encoderCount_ = 0;

    float targetRPM_ = 0.0;
    float measuredRPM_ = 0.0;

    float kp_ = 0.9;
    float ki_ = 0.01;

    float pwmPerRPM_ = 0.90;

    float integral_ = 0.0;

    int pwmOutput_ = 0;
    int direction_ = 1;

    long lastPulses_ = 0;

    unsigned long lastTime_ = 0;
    const unsigned long sampleTimeMs_ = 600;

    static MotorController* instances_[4];

    static void IRAM_ATTR encoderISR0();
    static void IRAM_ATTR encoderISR1();
    static void IRAM_ATTR encoderISR2();
    static void IRAM_ATTR encoderISR3();

    void IRAM_ATTR handleEncoder();
};

#endif