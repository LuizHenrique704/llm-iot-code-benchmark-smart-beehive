#include <Arduino.h>

const uint8_t SENSOR_PIN = 4;
const unsigned long DEBOUNCE_DELAY = 50;

int lastStableState = HIGH;
int lastRawReading = HIGH;
unsigned long lastDebounceTime = 0;

void printState(int state) {
  if (state == HIGH) {
    Serial.println("ESTADO: COLMEIA ABERTA");
  } else {
    Serial.println("ESTADO: COLMEIA FECHADA");
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }

  pinMode(SENSOR_PIN, INPUT_PULLUP);

  lastRawReading = digitalRead(SENSOR_PIN);
  lastStableState = lastRawReading;
  lastDebounceTime = millis();

  Serial.println("--- Iniciando Monitoramento MC-38 (GPIO 4) ---");
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