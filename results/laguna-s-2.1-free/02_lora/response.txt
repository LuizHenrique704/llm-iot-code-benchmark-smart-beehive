#include <LoRa_E32.h>
#include <HardwareSerial.h>

HardwareSerial uart2(2);
LoRa_E32 e32ttl(&uart2, 5, 18, 19);

unsigned long lastSend = 0;
const long interval = 5000;

void setup() {
  Serial.begin(9600);
  while (!Serial) {}

  uart2.begin(9600, SERIAL_8N1, 16, 17);

  e32ttl.setMode(MODE_CONFIG);

  e32ttl.setAddH(0);
  e32ttl.setAddL(1);
  e32ttl.setChan(13);
  e32ttl.setUARTbaud(UART_BPS_9600);
  e32ttl.setUARTparity(MODE_00_8N1);
  e32ttl.setAirdatarate(AIR_DATA_RATE_010_24);
  e32ttl.setWakeup(WAKE_UP_250);
  e32ttl.setIO_Mode(IO_D_MODE_PUSH_PULLS_PULL_UPS);
  e32ttl.setFEC(FEC_0_OFF);
  e32ttl.setPower(POWER_20);
  e32ttl.setFixedTransmission(FT_FIXED_TRANSMISSION);

  e32ttl.saveParams();
  e32ttl.setMode(MODE_NORMAL);

  Serial.println("Configuracao aplicada. Modulo em modo normal.");
}

void loop() {
  if (millis() - lastSend >= interval) {
    lastSend = millis();

    int result = e32ttl.sendFixedMessage(0, 3, 13, "teste_lora");

    if (result == 0) {
      Serial.println("Transmissao realizada com sucesso.");
    } else {
      Serial.println("Erro na transmissao.");
    }
  }
}