#include <Arduino.h>

const int SENSOR_PIN = 4;
const unsigned long DEBOUNCE_DELAY = 50; // milliseconds

int lastReading = HIGH;
int stableState = HIGH;
unsigned long lastDebounceTime = 0;

void printState(int state) {
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
  int currentReading = digitalRead(SENSOR_PIN);

  if (currentReading != lastReading) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > DEBOUNCE_DELAY) {
    if (currentReading != stableState) {
      stableState = currentReading;
      printState(stableState);
    }
  }

  lastReading = currentReading;
}