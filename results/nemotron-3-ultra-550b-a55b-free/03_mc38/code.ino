#include <Arduino.h>

const uint8_t SENSOR_PIN = 4;
const unsigned long DEBOUNCE_DELAY = 50;

int lastStableState = HIGH;
int lastRawReading = HIGH;
unsigned long lastDebounceTime = 0;

void printState(int state) {
  if (state == HIGH) {
    Serial.println("COLMEIA ABERTA");
  } else {
    Serial.println("COLMEIA FECHADA");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(SENSOR_PIN, INPUT_PULLUP);

  delay(100);

  lastRawReading = digitalRead(SENSOR_PIN);
  lastStableState = lastRawReading;
  lastDebounceTime = millis();

  printState(lastStableState);
}

void loop() {
  int currentRawReading = digitalRead(SENSOR_PIN);

  if (currentRawReading != lastRawReading) {
    lastDebounceTime = millis();
    lastRawReading = currentRawReading;
  }

  if ((millis() - lastDebounceTime) > DEBOUNCE_DELAY) {
    if (currentRawReading != lastStableState) {
      lastStableState = currentRawReading;
      printState(lastStableState);
    }
  }
}