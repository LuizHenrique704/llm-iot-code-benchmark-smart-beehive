const int sensorPin = 4;
int prevSensorState;
int currentSensorState;

void setup() {
  pinMode(sensorPin, INPUT_PULLUP);
  Serial.begin(115200);
  prevSensorState = digitalRead(sensorPin);
  if (prevSensorState == HIGH) {
    Serial.println("Colmeia aberta");
  } else {
    Serial.println("Colmeia fechada");
  }
}

void loop() {
  currentSensorState = digitalRead(sensorPin);
  if (currentSensorState != prevSensorState) {
    delay(50);
    currentSensorState = digitalRead(sensorPin);
    if (currentSensorState != prevSensorState) {
      prevSensorState = currentSensorState;
      if (currentSensorState == HIGH) {
        Serial.println("Colmeia aberta");
      } else {
        Serial.println("Colmeia fechada");
      }
    }
  }
  delay(10);
}