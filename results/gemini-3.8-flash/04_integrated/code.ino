#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <HardwareSerial.h>
#include "LoRa_E32.h"
#include <esp_mac.h>
#include <esp_sleep.h>

#define I2C_SDA 21
#define I2C_SCL 22
#define BME280_ADDR 0x76
#define SEALEVELPRESSURE_HPA (1013.25)

#define SENSOR_PIN 4

#define PIN_RX 16
#define PIN_TX 17
#define PIN_AUX 5
#define PIN_M0 18
#define PIN_M1 19

#define TX_ADDH 0
#define TX_ADDL 1
#define TX_CHAN 13

#define DEST_ADDH 0
#define DEST_ADDL 3
#define DEST_CHAN 13

#define SLEEP_TIME_US (60ULL * 60ULL * 1000000ULL)

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

RTC_DATA_ATTR uint32_t contadorTransmissoes = 0;

Adafruit_BME280 bme;
LoRa_E32 e32(&Serial2, PIN_AUX, PIN_M0, PIN_M1);

void setup() {
  setCpuFrequencyMhz(40);

  Serial.begin(115200);

  pinMode(SENSOR_PIN, INPUT_PULLUP);
  delay(10);

  Wire.begin(I2C_SDA, I2C_SCL);
  bool bmeIniciado = bme.begin(BME280_ADDR, &Wire);

  Serial2.begin(9600, SERIAL_8N1, PIN_RX, PIN_TX);
  e32.begin();

  ResponseStructContainer c = e32.getConfiguration();
  if (c.status.code == 1) {
    Configuration configuration = *(Configuration*)c.data;
    bool precisaConfigurar = false;

    if (configuration.ADDH != TX_ADDH || configuration.ADDL != TX_ADDL || configuration.CHAN != TX_CHAN ||
        configuration.SPED.uartBaudRate != UART_BPS_9600 || configuration.SPED.uartParity != MODE_00_8N1 ||
        configuration.SPED.airDataRate != AIR_DATA_RATE_010_24 || configuration.OPTION.wirelessWakeUpTime != WAKE_UP_250 ||
        configuration.OPTION.ioDriveMode != IO_D_MODE_PUSH_PULLS_PULL_UPS || configuration.OPTION.fec != FEC_0_OFF ||
        configuration.OPTION.transmissionPower != POWER_20 || configuration.OPTION.fixedTransmission != FT_FIXED_TRANSMISSION) {

      configuration.ADDH = TX_ADDH;
      configuration.ADDL = TX_ADDL;
      configuration.CHAN = TX_CHAN;
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
  }
  c.close();

  e32.setMode(MODE_0_NORMAL);
  delay(50);

  DadosTransmissao pacote;
  memset(&pacote, 0, sizeof(pacote));
  strncpy(pacote.identificador, "colmeia", sizeof(pacote.identificador));

  esp_read_mac(pacote.mac, ESP_MAC_WIFI_STA);

  if (bmeIniciado) {
    pacote.temperatura = bme.readTemperature();
    pacote.umidade = bme.readHumidity();
    pacote.pressao = bme.readPressure() / 100.0F;
    pacote.altitude = bme.readAltitude(SEALEVELPRESSURE_HPA);
  } else {
    pacote.temperatura = NAN;
    pacote.umidade = NAN;
    pacote.pressao = NAN;
    pacote.altitude = NAN;
  }

  pacote.colmeiaAberta = (digitalRead(SENSOR_PIN) == HIGH) ? 1 : 0;
  pacote.contador = ++contadorTransmissoes;

  e32.sendFixedMessage(DEST_ADDH, DEST_ADDL, DEST_CHAN, &pacote, sizeof(pacote));

  e32.setMode(MODE_3_SLEEP);
  delay(50);

  esp_sleep_enable_timer_wakeup(SLEEP_TIME_US);
  esp_sleep_enable_ext0_wakeup((gpio_num_t)SENSOR_PIN, 1);

  esp_deep_sleep_start();
}

void loop() {
}