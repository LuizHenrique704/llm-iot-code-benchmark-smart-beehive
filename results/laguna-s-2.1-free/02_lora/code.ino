#include <HardwareSerial.h>
#include <LoRa_E32.h>

#define RX_PIN 16
#define TX_PIN 17
#define AUX_PIN 5
#define M0_PIN 18
#define M1_PIN 19

HardwareSerial UART2(2);
LoRa_E32 e32(&UART2, AUX_PIN, M0_PIN, M1_PIN);

void setup() {
  Serial.begin(9600);
  while (!Serial) {}

  UART2.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);

  e32.begin();

  e32.setParameters(0, 1, 13, UART_BPS_9600, MODE_00_8N1, AIR_DATA_RATE_010_24, WAKE_UP_250, IO_D_MODE_PUSH_PULLS_PULL_UPS, FEC_0_OFF, POWER_20, FT_FIXED_TRANSMISSION);

  e32.setMode(MODE_NORMAL);

  Serial.println("Configuracao concluida.");
}

void loop() {
  const char* message = "teste_lora";
  uint8_t len = strlen(message);

  uint8_t result = e32.sendFixedMessage(0, 3, 13, (uint8_t*)message, len);

  if (result == 0) {
    Serial.println("Transmissao bem-sucedida.");
  } else {
    Serial.print("Erro na transmissao: ");
    Serial.println(result);
  }

  delay(5000);
}