#include <Arduino.h>
#include <LoRa_E32.h>

HardwareSerial SerialLoRa(2);

LoRa_E32 e32ttl(&SerialLoRa, 5, 18, 19);

void printParameters(struct Configuration configuration);
void printModuleInformation(struct ModuleInformation moduleInformation);

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }
  Serial.println("Iniciando teste LoRa E32-TTL-100...");

  SerialLoRa.begin(9600, SERIAL_8N1, 16, 17);
  e32ttl.begin();

  ResponseStructContainer c = e32ttl.getConfiguration();
  if (c.status.code != 1) {
    Serial.println("Erro ao obter configuracao inicial.");
    return;
  }
  Configuration configuration = *(Configuration*)c.data;
  c.close();

  configuration.ADDH = 0;
  configuration.ADDL = 1;
  configuration.CHAN = 13;
  configuration.SPED.uartBaudRate = UART_BPS_9600;
  configuration.SPED.uartParity = MODE_00_8N1;
  configuration.SPED.airDataRate = AIR_DATA_RATE_010_24;
  configuration.OPTION.wirelessWakeupTime = WAKE_UP_250;
  configuration.OPTION.ioDriveMode = IO_D_MODE_PUSH_PULLS_PULL_UPS;
  configuration.OPTION.fec = FEC_0_OFF;
  configuration.OPTION.transmissionPower = POWER_20;
  configuration.OPTION.fixedTransmission = FT_FIXED_TRANSMISSION;

  ResponseStatus rs = e32ttl.setConfiguration(configuration, WRITE_CFG_PWR_DWN_SAVE);
  if (rs.code != 1) {
    Serial.print("Erro ao configurar modulo: ");
    Serial.println(rs.getResponseDescription());
  } else {
    Serial.println("Configuracao aplicada com sucesso.");
    printParameters(configuration);
  }

  e32ttl.setMode(MODE_0_NORMAL);
  Serial.println("Modo Normal ativado. Iniciando transmissao a cada 5s...");
}

void loop() {
  static unsigned long lastSend = 0;
  if (millis() - lastSend >= 5000) {
    lastSend = millis();

    ResponseStatus rs = e32ttl.sendFixedMessage(0, 3, 13, "teste_lora");
    if (rs.code == 1) {
      Serial.println("Transmissao realizada com sucesso.");
    } else {
      Serial.print("Erro na transmissao: ");
      Serial.println(rs.getResponseDescription());
    }
  }
}

void printParameters(struct Configuration configuration) {
  Serial.println("----------------------------------------");
  Serial.print("HEAD: "); Serial.print(configuration.HEAD, BIN); Serial.print(" "); Serial.print(configuration.HEAD, DEC); Serial.print(" "); Serial.println(configuration.HEAD, HEX);
  Serial.println("----------------------------------------");
  Serial.print("ADDH: "); Serial.println(configuration.ADDH, DEC);
  Serial.print("ADDL: "); Serial.println(configuration.ADDL, DEC);
  Serial.print("CHAN: "); Serial.println(configuration.CHAN, DEC);
  Serial.println("----------------------------------------");
  Serial.print("UART Baud Rate: "); Serial.println(configuration.SPED.getUARTBaudRateDescription());
  Serial.print("UART Parity: "); Serial.println(configuration.SPED.getUARTParityDescription());
  Serial.print("Air Data Rate: "); Serial.println(configuration.SPED.getAirDataRateDescription());
  Serial.println("----------------------------------------");
  Serial.print("Wireless Wakeup Time: "); Serial.println(configuration.OPTION.getWirelessWakeUPTimeDescription());
  Serial.print("IO Drive Mode: "); Serial.println(configuration.OPTION.getIODriveModeDescription());
  Serial.print("FEC: "); Serial.println(configuration.OPTION.getFECDescription());
  Serial.print("Transmission Power: "); Serial.println(configuration.OPTION.getTransmissionPowerDescription());
  Serial.print("Fixed Transmission: "); Serial.println(configuration.OPTION.getFixedTransmissionDescription());
  Serial.println("----------------------------------------");
}