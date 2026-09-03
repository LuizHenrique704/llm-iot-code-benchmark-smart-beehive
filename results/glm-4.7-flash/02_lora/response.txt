#include <LoRa_E32.h>
#include <HardwareSerial.h>

#define RX_PIN 16
#define TX_PIN 17
#define AUX_PIN 5
#define M0_PIN 18
#define M1_PIN 19

HardwareSerial Uart2(2);
LoRa_E32 e32(&Uart2, AUX_PIN, M0_PIN, M1_PIN);

void setup() {
  Serial.begin(115200);
  Uart2.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);
  delay(1000);

  Configuration config = Configuration();
  config.ADDH = 0;
  config.ADDL = 1;
  config.CHAN = 13;
  config.SPED.uartBaudRate = UART_BPS_9600;
  config.SPED.airDataRate = AIR_DATA_RATE_010_24;
  config.SPED.uartParity = MODE_00_8N1;
  config.OPT.wirelessWakeUpTime = WAKE_UP_250;
  config.OPT.ioDriveMode = IO_D_MODE_PUSH_PULLS_PULL_UPS;
  config.OPT.fec = FEC_0_OFF;
  config.POWER = POWER_20;
  config.TRANSMISSION_MODE = FT_FIXED_TRANSMISSION;

  ResponseStatus status = e32.setModuleConfiguration(config);
  if (status.code != 1) {
    Serial.println(F("Erro ao configurar modulo"));
    Serial.println(status.toString());
  } else {
    Serial.println(F("Modulo configurado com sucesso"));
  }

  e32.setMode(MODE_NORMAL);
}

void loop() {
  Message message;
  message.frameHeader = 'T';
  message.payload = "teste_lora";
  message.length = message.payload.length() + 1;

  ResponseStatus rs = e32.sendFixedMessage(0, 3, 13, message);

  if (rs.success) {
    Serial.println(F("Transmissao realizada com sucesso"));
  } else {
    Serial.println(F("Erro na transmissao"));
    Serial.println(rs.toString());
  }

  delay(5000);
}