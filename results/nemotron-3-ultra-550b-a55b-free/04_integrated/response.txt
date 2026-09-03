#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <LoRa_E32.h>
#include <esp_sleep.h>
#include <esp_mac.h>
#include <cstring>

#define SDA_PIN 21
#define SCL_PIN 22
#define BME280_ADDRESS 0x76
#define SEALEVELPRESSURE_HPA (1013.25)

#define RX_PIN 16
#define TX_PIN 17
#define AUX_PIN 5
#define M0_PIN 18
#define M1_PIN 19

#define MC38_PIN 4

#define MY_ADDH 0x00
#define MY_ADDL 0x01
#define MY_CHAN 0x0D

#define DEST_ADDH 0x00
#define DEST_ADDL 0x03
#define DEST_CHAN 0x0D

#define WAKEUP_INTERVAL_US (60ULL * 60 * 1000000)

#pragma pack(push, 1)
struct SensorPayload {
  char id[8];
  uint8_t mac[6];
  float temperature;
  float humidity;
  float pressure;
  float altitude;
  uint8_t hiveState;
  uint32_t counter;
};
#pragma pack(pop)

RTC_DATA_ATTR uint32_t txCounter = 0;

Adafruit_BME280 bme;
HardwareSerial LoRaSerial(2);
LoRa_E32 e32ttl(&LoRaSerial, AUX_PIN, M0_PIN, M1_PIN);

void goToSleep() {
  esp_sleep_enable_timer_wakeup(WAKEUP_INTERVAL_US);
  esp_sleep_enable_ext0_wakeup(GPIO_NUM_4, 1);
  Serial.flush();
  esp_deep_sleep_start();
}

void setup() {
  setCpuFrequencyMhz(40);
  Serial.begin(115200);
  delay(100);

  txCounter++;

  Wire.begin(SDA_PIN, SCL_PIN);

  if (!bme.begin(BME280_ADDRESS, &Wire)) {
    Serial.println("Erro: BME280 nao encontrado.");
    goToSleep();
  }

  LoRaSerial.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);

  if (!e32ttl.begin()) {
    Serial.println("Erro: Falha ao inicializar modulo LoRa.");
    goToSleep();
  }

  ResponseStructContainer c = e32ttl.getConfiguration();
  if (c.status.code != 1) {
    Serial.println("Erro: Falha ao ler configuracao LoRa.");
    goToSleep();
  }
  Configuration configuration = *(Configuration*)c.data;
  c.close();

  configuration.ADDH = MY_ADDH;
  configuration.ADDL = MY_ADDL;
  configuration.CHAN = MY_CHAN;

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
    Serial.println("Erro: Falha ao salvar configuracao LoRa.");
    goToSleep();
  }

  ResponseStatus rsMode = e32ttl.setMode(MODE_0_NORMAL);
  if (rsMode.code != 1) {
    Serial.println("Erro: Falha ao definir modo normal LoRa.");
    goToSleep();
  }

  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0F;
  float altitude = bme.readAltitude(SEALEVELPRESSURE_HPA);

  if (isnan(temperature) || isnan(humidity) || isnan(pressure)) {
    Serial.println("Erro: Leitura invalida BME280.");
    goToSleep();
  }

  pinMode(MC38_PIN, INPUT_PULLUP);
  delay(10);
  uint8_t hiveState = digitalRead(MC38_PIN);

  uint8_t mac[6];
  esp_read_mac(mac, ESP_MAC_WIFI_STA);

  SensorPayload payload;
  strcpy(payload.id, "colmeia");
  memcpy(payload.mac, mac, 6);
  payload.temperature = temperature;
  payload.humidity = humidity;
  payload.pressure = pressure;
  payload.altitude = altitude;
  payload.hiveState = hiveState;
  payload.counter = txCounter;

  ResponseStatus rsSend = e32ttl.sendFixedMessage(DEST_ADDH, DEST_ADDL, DEST_CHAN, &payload, sizeof(payload));
  if (rsSend.code != 1) {
    Serial.println("Erro: Falha no envio LoRa.");
  }

  e32ttl.setMode(MODE_3_SLEEP);
  delay(100);

  goToSleep();
}

void loop() {
}