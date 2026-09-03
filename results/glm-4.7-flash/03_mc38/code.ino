void setup() {
  Serial.begin(115200);
  pinMode(4, INPUT_PULLUP);
  
  int estadoInicial = digitalRead(4);
  if (estadoInicial == HIGH) {
    Serial.println("Colmeia: Aberta");
  } else {
    Serial.println("Colmeia: Fechada");
  }
}

void loop() {
  int estadoAtual = digitalRead(4);
  static int estadoAnterior = -1;

  if (estadoAtual != estadoAnterior) {
    delay(50); // Tratamento simples para evitar oscilação (debounce)
    estadoAtual = digitalRead(4);

    if (estadoAtual != estadoAnterior) {
      if (estadoAtual == HIGH) {
        Serial.println("Colmeia: Aberta");
      } else {
        Serial.println("Colmeia: Fechada");
      }
      estadoAnterior = estadoAtual;
    }
  }
}