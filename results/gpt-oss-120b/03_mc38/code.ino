#include <Arduino.h>

const uint8_t SENSOR_PIN = 4;
const unsigned long DEBOUNCE_DELAY_MS = 50;

uint8_t lastReading = HIGH;
uint8_t stableState = HIGH;
unsigned long lastDebounceTime = 0;

void printState(uint8_t state) {
  if (state == HIGH) {
    Serial.println("Colmeia aberta");
  } else {
    Serial.println("Colmeia fechada");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(SENSOR_PIN, INPUT_PULLUP);
  stableState = digitalRead(SENSOR_PIN);
  lastReading = stableState;
  printState(stableState);
}

void loop() {
  uint8_t currentReading = digitalRead(SENSOR_PIN);

  if (currentReading != lastReading) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > DEBOUNCE_DELAY_MS) {
    if (currentReading != stableState) {
      stableState = currentReading;
      printState(stableState);
    }
  }

  lastReading = currentReading;
}