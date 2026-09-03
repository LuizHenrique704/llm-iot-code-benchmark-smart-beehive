#include <Arduino.h>
#include <HardwareSerial.h>
#include "LoRa_E32.h"

#define PIN_RX 16
#define PIN_TX 17
#define PIN_AUX 5
#define PIN_M0 18
#define PIN_M1 19

#define RX_ADDH 0
#define RX_ADDL 3
#define RX_CHAN 13

#pragma pack(push, 1)
struct DadosTransmissao {
  char identificador[8];
  uint8_t mac[6];
  float temperatura;
  float umidade;
  float pressao;
  float altitude;
  uint8_t colmeiaAberta;
  uint32_t contador;
};
#pragma pack(pop)

DadosTransmissao pacoteAtual;
LoRa_E32 e32(&Serial2, PIN_AUX, PIN_M0, PIN_M1);

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;
  }

  Serial2.begin(9600, SERIAL_8N1, PIN_RX, PIN_TX);
  e32.begin();

  ResponseStructContainer c = e32.getConfiguration();
  if (c.status.code == 1) {
    Configuration configuration = *(Configuration*)c.data;
    bool precisaConfigurar = false;

    if (configuration.ADDH != RX_ADDH || configuration.ADDL != RX_ADDL || configuration.CHAN != RX_CHAN ||
        configuration.SPED.uartBaudRate != UART_BPS_9600 || configuration.SPED.uartParity != MODE_00_8N1 ||
        configuration.SPED.airDataRate != AIR_DATA_RATE_010_24 || configuration.OPTION.wirelessWakeUpTime != WAKE_UP_250 ||
        configuration.OPTION.ioDriveMode != IO_D_MODE_PUSH_PULLS_PULL_UPS || configuration.OPTION.fec != FEC_0_OFF ||
        configuration.OPTION.transmissionPower != POWER_20 || configuration.OPTION.fixedTransmission != FT_FIXED_TRANSMISSION) {

      configuration.ADDH = RX_ADDH;
      configuration.ADDL = RX_ADDL;
      configuration.CHAN = RX_CHAN;
      configuration.SPED.uartBaudRate = UART_BPS_9600;
      configuration.SPED.uartParity = MODE_00_8N1;
      configuration.SPED.airDataRate = AIR_DATA_RATE_010_24;
      configuration.OPTION.wirelessWakeUpTime = WAKE_UP_250;
      configuration.OPTION.ioDriveMode = IO_D_MODE_PUSH_PULLS_PULL_UPS;
      configuration.OPTION.fec = FEC_0_OFF;
      configuration.OPTION.transmissionPower = POWER_20;
      configuration.OPTION.fixedTransmission = FT_FIXED_TRANSMISSION;

      precisaConfigurar = true;
    }

    if (precisaConfigurar) {
      e32.setConfiguration(configuration, WRITE_CFG_PWR_DWN_SAVE);
    }
  } else {
    Serial.println("Erro ao obter configuracao do modulo LoRa");
  }
  c.close();

  e32.setMode(MODE_0_NORMAL);
  delay(50);
}

void loop() {
  if (e32.available() > 1) {
    ResponseStructContainer rsc = e32.receiveMessage(sizeof(DadosTransmissao));
    if (rsc.status.code == 1) {
      memcpy(&pacoteAtual, rsc.data, sizeof(DadosTransmissao));

      if (strncmp(pacoteAtual.identificador, "colmeia", 7) == 0) {
        char macStr[18];
        snprintf(macStr, sizeof(macStr), "%02X:%02X:%02X:%02X:%02X:%02X",
                 pacoteAtual.mac[0], pacoteAtual.mac[1], pacoteAtual.mac[2],
                 pacoteAtual.mac[3], pacoteAtual.mac[4], pacoteAtual.mac[5]);

        Serial.print("MAC: ");
        Serial.println(macStr);

        Serial.print("Temperatura: ");
        if (isnan(pacoteAtual.temperatura)) {
          Serial.println("ERRO");
        } else {
          Serial.print(pacoteAtual.temperatura, 2);
          Serial.println(" C");
        }

        Serial.print("Umidade: ");
        if (isnan(pacoteAtual.umidade)) {
          Serial.println("ERRO");
        } else {
          Serial.print(pacoteAtual.umidade, 2);
          Serial.println(" %");
        }

        Serial.print("Pressao: ");
        if (isnan(pacoteAtual.pressao)) {
          Serial.println("ERRO");
        } else {
          Serial.print(pacoteAtual.pressao, 2);
          Serial.println(" hPa");
        }

        Serial.print("Altitude: ");
        if (isnan(pacoteAtual.altitude)) {
          Serial.println("ERRO");
        } else {
          Serial.print(pacoteAtual.altitude, 2);
          Serial.println(" m");
        }

        Serial.print("Estado: ");
        Serial.println(pacoteAtual.colmeiaAberta ? "ABERTA" : "FECHADA");

        Serial.print("Contador: ");
        Serial.println(pacoteAtual.contador);
        Serial.println();
      } else {
        Serial.println("Erro: Pacote recebido com identificador invalido.");
      }
    } else {
      Serial.print("Erro na recepcao do pacote: ");
      Serial.println(rsc.status.getResponseDescription());
    }
    rsc.close();
  }
}