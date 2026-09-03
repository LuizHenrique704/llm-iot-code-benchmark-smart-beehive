const int SENSOR_PIN = 4;
const unsigned long DEBOUNCE_DELAY = 50;

int lastSensorReading = HIGH;
int currentSensorState = HIGH;
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

  delay(50);

  currentSensorState = digitalRead(SENSOR_PIN);
  lastSensorReading = currentSensorState;

  Serial.print("Estado inicial: ");
  printState(currentSensorState);
}

void loop() {
  int reading = digitalRead(SENSOR_PIN);

  if (reading != lastSensorReading) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > DEBOUNCE_DELAY) {
    if (reading != currentSensorState) {
      currentSensorState = reading;
      printState(currentSensorState);
    }
  }

  lastSensorReading = reading;
}