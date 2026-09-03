#include <Arduino.h>
#include <HardwareSerial.h>
#include "LoRa_E32.h"

#define PIN_RX 16
#define PIN_TX 17
#define PIN_AUX 5
#define PIN_M0 18
#define PIN_M1 19

#define DEST_ADDH 0
#define DEST_ADDL 3
#define DEST_CHAN 13

LoRa_E32 e32(&Serial2, PIN_AUX, PIN_M0, PIN_M1);

unsigned long ultimoEnvio = 0;
const unsigned long intervaloEnvio = 5000;

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;
  }
  Serial.println("\nInicializando teste do radio E32-TTL-100...");

  Serial2.begin(9600, SERIAL_8N1, PIN_RX, PIN_TX);

  e32.begin();

  ResponseStructContainer c = e32.getConfiguration();
  if (c.status.code != 1) {
    Serial.print("Erro ao obter configuracao do modulo: ");
    Serial.println(c.status.getResponseDescription());
  } else {
    Configuration configuration = *(Configuration*) c.data;

    configuration.ADDH = 0;
    configuration.ADDL = 1;
    configuration.CHAN = 13;

    configuration.SPED.uartBaudRate = UART_BPS_9600;
    configuration.SPED.uartParity = MODE_00_8N1;
    configuration.SPED.airDataRate = AIR_DATA_RATE_010_24;

    configuration.OPTION.wirelessWakeUpTime = WAKE_UP_250;
    configuration.OPTION.ioDriveMode = IO_D_MODE_PUSH_PULLS_PULL_UPS;
    configuration.OPTION.fec = FEC_0_OFF;
    configuration.OPTION.transmissionPower = POWER_20;
    configuration.OPTION.fixedTransmission = FT_FIXED_TRANSMISSION;

    ResponseStatus rs = e32.setConfiguration(configuration, WRITE_CFG_PWR_DWN_SAVE);
    Serial.print("Aplicando configuracoes: ");
    Serial.println(rs.getResponseDescription());
  }
  c.close();

  e32.setMode(MODE_0_NORMAL);
  delay(100);

  Serial.println("Radio pronto. Iniciando ciclo de transmissao fixa a cada 5 segundos.");
}

void loop() {
  if (millis() - ultimoEnvio >= intervaloEnvio) {
    ultimoEnvio = millis();

    Serial.print("Enviando mensagem fixa para [ADDH:");
    Serial.print(DEST_ADDH);
    Serial.print(", ADDL:");
    Serial.print(DEST_ADDL);
    Serial.print(", CHAN:");
    Serial.print(DEST_CHAN);
    Serial.print("]... ");

    ResponseStatus rs = e32.sendFixedMessage(DEST_ADDH, DEST_ADDL, DEST_CHAN, "teste_lora");

    if (rs.code == 1) {
      Serial.println("Sucesso!");
    } else {
      Serial.print("Erro: ");
      Serial.println(rs.getResponseDescription());
    }
  }
}