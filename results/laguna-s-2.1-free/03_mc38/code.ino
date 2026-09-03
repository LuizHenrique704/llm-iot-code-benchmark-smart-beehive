const int sensorPin = 4;
const int debounceDelay = 50;

int lastState;
int currentState;

void setup() {
  pinMode(sensorPin, INPUT_PULLUP);
  Serial.begin(115200);

  currentState = digitalRead(sensorPin);
  lastState = currentState;

  if (currentState == HIGH) {
    Serial.println("Colmeia aberta");
  } else {
    Serial.println("Colmeia fechada");
  }
}

void loop() {
  currentState = digitalRead(sensorPin);

  if (currentState != lastState) {
    delay(debounceDelay);

    currentState = digitalRead(sensorPin);

    if (currentState != lastState) {
      lastState = currentState;

      if (currentState == HIGH) {
        Serial.println("Colmeia aberta");
      } else {
        Serial.println("Colmeia fechada");
      }
    }
  }
}