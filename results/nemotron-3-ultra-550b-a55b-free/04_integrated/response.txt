#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <LoRa_E32.h>
#include <esp_sleep.h>
#include <esp_wifi.h>

#define SDA_PIN 21
#define SCL_PIN 22
#define BME280_ADDRESS 0x76
#define SEALEVELPRESSURE_HPA (1013.25)

#define RX_PIN 16
#define TX_PIN 17
#define AUX_PIN 5
#define M0_PIN 18
#define M1_PIN 19

#define SENSOR_PIN 4

#define WAKEUP_GPIO GPIO_NUM_4
#define SLEEP_DURATION_US (60ULL * 60 * 1000000)

#pragma pack(push, 1)
struct Payload {
  char identifier[8];
  uint8_t mac[6];
  float temperature;
  float humidity;
  float pressure;
  float altitude;
  uint8_t hiveState;
  uint32_t txCounter;
};
#pragma pack(pop)

RTC_DATA_ATTR uint32_t bootCount = 0;
RTC_DATA_ATTR uint32_t txCounter = 0;

Adafruit_BME280 bme;
HardwareSerial LoRaSerial(2);
LoRa_E32 e32ttl(&LoRaSerial, AUX_PIN, M0_PIN, M1_PIN);

void setupLoRaConfig() {
  ResponseStructContainer c = e32ttl.getConfiguration();
  if (c.status.code != 1) return;
  Configuration configuration = *(Configuration*)c.data;
  c.close();

  configuration.ADDH = 0x00;
  configuration.ADDL = 0x01;
  configuration.CHAN = 0x0D;

  configuration.SPED.uartBaudRate = UART_BPS_9600;
  configuration.SPED.uartParity = MODE_00_8N1;
  configuration.SPED.airDataRate = AIR_DATA_RATE_010_24;

  configuration.OPTION.wirelessWakeupTime = WAKE_UP_250;
  configuration.OPTION.ioDriveMode = IO_D_MODE_PUSH_PULLS_PULL_UPS;
  configuration.OPTION.fec = FEC_0_OFF;
  configuration.OPTION.transmissionPower = POWER_20;
  configuration.OPTION.fixedTransmission = FT_FIXED_TRANSMISSION;

  e32ttl.setConfiguration(configuration, WRITE_CFG_PWR_DWN_SAVE);
  e32ttl.setMode(MODE_0_NORMAL);
}

bool readSensors(Payload &data) {
  float t = bme.readTemperature();
  float h = bme.readHumidity();
  float p = bme.readPressure() / 100.0F;
  float a = bme.readAltitude(SEALEVELPRESSURE_HPA);

  if (isnan(t) || isnan(h) || isnan(p) || isnan(a)) {
    return false;
  }

  data.temperature = t;
  data.humidity = h;
  data.pressure = p;
  data.altitude = a;
  data.hiveState = (digitalRead(SENSOR_PIN) == HIGH) ? 1 : 0;
  return true;
}

void sendPayload(const Payload &data) {
  ResponseStatus rs = e32ttl.sendFixedMessage(0x00, 0x03, 0x0D, (uint8_t*)&data, sizeof(Payload));
  (void)rs;
}

void enterDeepSleep() {
  e32ttl.setMode(MODE_3_SLEEP);
  delay(100);
  LoRaSerial.end();
  pinMode(RX_PIN, INPUT);
  pinMode(TX_PIN, INPUT);
  pinMode(AUX_PIN, INPUT);
  pinMode(M0_PIN, INPUT);
  pinMode(M1_PIN, INPUT);

  esp_sleep_enable_timer_wakeup(SLEEP_DURATION_US);
  esp_sleep_enable_ext0_wakeup(WAKEUP_GPIO, 1);

  esp_deep_sleep_start();
}

void setup() {
  setCpuFrequencyMhz(40);
  Serial.begin(115200);
  delay(100);

  bootCount++;

  Wire.begin(SDA_PIN, SCL_PIN);
  if (!bme.begin(BME280_ADDRESS, &Wire)) {
    enterDeepSleep();
  }

  pinMode(SENSOR_PIN, INPUT_PULLUP);

  LoRaSerial.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);
  if (!e32ttl.begin()) {
    enterDeepSleep();
  }

  setupLoRaConfig();

  Payload payload;
  memset(&payload, 0, sizeof(Payload));
  strncpy(payload.identifier, "colmeia", sizeof(payload.identifier) - 1);
  uint64_t chipid = ESP.getEfuseMac();
  for (int i = 0; i < 6; i++) {
    payload.mac[i] = (chipid >> (40 - i * 8)) & 0xFF;
  }
  payload.txCounter = txCounter;

  if (readSensors(payload)) {
    sendPayload(payload);
    txCounter++;
  }

  enterDeepSleep();
}

void loop() {
}