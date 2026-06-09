#include "motor_controller.hpp"

MotorController* MotorController::instances_[2] = {nullptr, nullptr};

MotorController::MotorController(
    int motorId,
    uint8_t pwmPin,
    uint8_t dirPin,
    uint8_t encoderPin,
    float countsPerRev
)
    : motorId_(motorId),
      pwmPin_(pwmPin),
      dirPin_(dirPin),
      encoderPin_(encoderPin),
      countsPerRev_(countsPerRev)
{
}

void MotorController::begin() {
    pinMode(pwmPin_, OUTPUT);
    pinMode(dirPin_, OUTPUT);
    pinMode(encoderPin_, INPUT_PULLUP);

    digitalWrite(dirPin_, LOW);
    analogWrite(pwmPin_, 0);

    if (motorId_ >= 0 && motorId_ < 2) {
        instances_[motorId_] = this;

        if (motorId_ == 0) {
            attachInterrupt(
                digitalPinToInterrupt(encoderPin_),
                encoderISR0,
                RISING
            );
        } else if (motorId_ == 1) {
            attachInterrupt(
                digitalPinToInterrupt(encoderPin_),
                encoderISR1,
                RISING
            );
        }
    }

    lastTime_ = millis();
}

void IRAM_ATTR MotorController::encoderISR0() {
    if (instances_[0] != nullptr) {
        instances_[0]->handleEncoder();
    }
}

void IRAM_ATTR MotorController::encoderISR1() {
    if (instances_[1] != nullptr) {
        instances_[1]->handleEncoder();
    }
}

void IRAM_ATTR MotorController::handleEncoder() {
    encoderCount_++;
}

void MotorController::setTargetRPM(float rpm) {
    targetRPM_ = rpm;

    if (targetRPM_ > 0.0) {
        direction_ = 1;
        digitalWrite(dirPin_, LOW);      // adelante
    } else if (targetRPM_ < 0.0) {
        direction_ = -1;
        digitalWrite(dirPin_, HIGH);     // atrás
    } else {
        pwmOutput_ = 0;
        integral_ = 0.0;
        analogWrite(pwmPin_, 0);
        return;
    }

    float targetAbsRPM = fabs(targetRPM_);

    pwmOutput_ = constrain(
        (int)(targetAbsRPM * pwmPerRPM_),
        0,
        255
    );

    analogWrite(pwmPin_, pwmOutput_);
}

void MotorController::setPI(float kp, float ki) {
    kp_ = kp;
    ki_ = ki;
}

void MotorController::setFeedForward(float pwmPerRPM) {
    pwmPerRPM_ = pwmPerRPM;
}

bool MotorController::update() {
    unsigned long now = millis();

    if (now - lastTime_ < sampleTimeMs_) {
        return false;
    }

    noInterrupts();
    long pulses = encoderCount_;
    encoderCount_ = 0;
    interrupts();

    float dt = (now - lastTime_) / 1000.0;
    lastTime_ = now;

    lastPulses_ = pulses;

    float revolutions = pulses / countsPerRev_;
    float rpmAbs = (revolutions / dt) * 60.0;

    if (direction_ < 0) {
        measuredRPM_ = -rpmAbs;
    } else {
        measuredRPM_ = rpmAbs;
    }

    if (targetRPM_ == 0.0) {
        pwmOutput_ = 0;
        integral_ = 0.0;
        analogWrite(pwmPin_, 0);
        return true;
    }

    float targetAbsRPM = fabs(targetRPM_);
    float measuredAbsRPM = fabs(measuredRPM_);

    float error = targetAbsRPM - measuredAbsRPM;

    // Zona muerta pequeña para evitar oscilaciones
    if (fabs(error) < 1.0) {
        error = 0.0;
    }

    integral_ += error * dt;

    // Anti-windup
    integral_ = constrain(integral_, -100.0, 100.0);

    float feedforward = targetAbsRPM * pwmPerRPM_;
    float correction = kp_ * error + ki_ * integral_;

    float pwm = feedforward + correction;

    pwmOutput_ = constrain((int)pwm, 0, 255);

    analogWrite(pwmPin_, pwmOutput_);

    return true;
}

float MotorController::getTargetRPM() const {
    return targetRPM_;
}

float MotorController::getRPM() const {
    return measuredRPM_;
}

int MotorController::getPWM() const {
    return pwmOutput_;
}

long MotorController::getLastPulses() const {
    return lastPulses_;
}