#include <Arduino.h>
#include <SCServo.h>

#define RX_PIN_FROM_ESP1 16
#define TX_PIN_TO_ESP1 17
#define ESP_BAUD 115200

#define SERVO_RX 4
#define SERVO_TX 2
#define SERVO_BAUD 1000000

SMS_STS st3215_bus;
String input_buffer = "";

void parse_and_drive(String command);

void setup() {
    Serial2.begin(ESP_BAUD, SERIAL_8N1, RX_PIN_FROM_ESP1, TX_PIN_TO_ESP1);
    Serial1.begin(SERVO_BAUD, SERIAL_8N1, SERVO_RX, SERVO_TX);
    st3215_bus.pSerial = &Serial1;
    
    delay(500); // Allow hardware lines to settle
}

void loop() {
    while (Serial2.available() > 0) {
        char in_char = (char)Serial2.read();
        if (in_char == '\n' || in_char == ';') {
            if (input_buffer.length() > 0) {
                parse_and_drive(input_buffer);
                input_buffer = "";
            }
        } else {
            input_buffer += in_char;
        }
    }
}

void parse_and_drive(String command) {
    if (!command.startsWith("$")) return;
    command = command.substring(1); // Drop '$'

    // Parse values split by commas
    int comma1 = command.indexOf(',');
    int comma2 = command.indexOf(',', comma1 + 1);
    int comma3 = command.indexOf(',', comma2 + 1);

    if (comma1 == -1 || comma2 == -1 || comma3 == -1) return;

    // Extract individual speeds
    int16_t speed11 = command.substring(0, comma1).toInt();
    int16_t speed12 = command.substring(comma1 + 1, comma2).toInt();
    int16_t speed13 = command.substring(comma2 + 1, comma3).toInt();
    int16_t speed14 = command.substring(comma3 + 1).toInt();

    // Directly write calculated values to the respective motor IDs
    // WriteSpe(ID, Speed, Acceleration)
    st3215_bus.WriteSpe(11, speed11, 0);
    st3215_bus.WriteSpe(12, speed12, 0);
    st3215_bus.WriteSpe(13, speed13, 0);
    st3215_bus.WriteSpe(14, speed14, 0);
}