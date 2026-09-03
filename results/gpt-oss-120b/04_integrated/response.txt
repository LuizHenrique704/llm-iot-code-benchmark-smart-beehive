#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <LoRa_E32.h>
#include <WiFi.h>
#include <esp_sleep.h>

#define SDA_PIN 21
#define SCL_PIN 22
#define BME280_ADDRESS 0x76
#define SEA_LEVEL_PRESSURE 1013.25

#define LORA_RX 16
#define LORA_TX 17
#define LORA_AUX 5
#define LORA_M0 18
#define LORA_M1 19

#define SENSOR_PIN 4
#define DEBOUNCE_DELAY_MS 50

Adafruit_BME280 bme;

HardwareSerial SerialLora(2);
LoRa_E32 lora(&SerialLora, LORA_AUX, LORA_M0, LORA_M1);

uint32_t txCounter = 0;
uint8_t lastReading = HIGH;
unsigned long lastDebounceTime = 0;

void setup() {
  setCpuFrequencyMhz(40);
  Serial.begin(115200);
  pinMode(SENSOR_PIN, INPUT_PULLUP);
  lastReading = digitalRead(SENSOR_PIN);

  // BME280 init
  Wire.begin(SDA_PIN, SCL_PIN);
  if (!bme.begin(BME280_ADDRESS, &Wire)) {
    Serial.println("BME280 init failed");
    // go to sleep, will retry on next wake
    esp_deep_sleep_start();
  }

  // LoRa init
  SerialLora.begin(9600, SERIAL_8N1, LORA_RX, LORA_TX);
  delay(200);
  if (lora.begin() != 0) {
    Serial.println("LoRa begin error");
    esp_deep_sleep_start();
  }

  Configuration cfg;
  cfg.ADDH = 0;
  cfg.ADDL = 1;
  cfg.CHAN = 13;
  cfg.UART_BPS = UART_BPS_9600;
  cfg.UART_PARITY = MODE_00_8N1;
  cfg.AIR_DATA_RATE = AIR_DATA_RATE_010_24;
  cfg.SUB_PACKET_SETTING = 0;
  cfg.RSSI_EN = 0;
  cfg.TRANSMIT_POWER = POWER_20;
  cfg.LBT = 0;
  cfg.WOR = WAKE_UP_250;
  cfg.FEC = FEC_0_OFF;
  cfg.IO_DRIVE_MODE = IO_D_MODE_PUSH_PULLS_PULL_UPS;
  if (lora.setConfiguration(cfg) != 0) {
    Serial.println("LoRa config error");
    esp_deep_sleep_start();
  }
  lora.setMode(MODE_0_NORMAL);

  // Prepare wake sources
  esp_sleep_enable_ext0_wakeup((gpio_num_t)SENSOR_PIN, 1); // wake when pin goes HIGH (open)
  esp_sleep_enable_timer_wakeup(60ULL * 60ULL * 1000000ULL); // 60 minutes

  // Gather data and transmit
  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0F; // hPa
  float altitude = bme.readAltitude(SEA_LEVEL_PRESSURE);
  uint8_t hiveState = digitalRead(SENSOR_PIN); // HIGH=open, LOW=closed

  uint8_t mac[6];
  WiFi.macAddress(mac);
  char macStr[18];
  snprintf(macStr, sizeof(macStr), "%02X:%02X:%02X:%02X:%02X:%02X",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

  const char *stateStr = (hiveState == HIGH) ? "aberta" : "fechada";

  char payload[200];
  snprintf(payload, sizeof(payload),
           "{\"id\":\"colmeia\",\"mac\":\"%s\",\"temp\":%.2f,\"hum\":%.2f,"
           "\"pres\":%.2f,\"alt\":%.2f,\"estado\":\"%s\",\"cnt\":%lu}",
           macStr, temperature, humidity, pressure, altitude, stateStr, (unsigned long)txCounter);

  int ret = lora.sendFixedMessage(0, 3, 13, payload);
  if (ret == 0) {
    Serial.println("LoRa transmission ok");
    txCounter++;
  } else {
    Serial.print("LoRa transmission error: ");
    Serial.println(ret);
  }

  // put LoRa in sleep to save power
  lora.setMode(MODE_3_SLEEP);

  // deep sleep until timer or hive opened
  esp_deep_sleep_start();
}

void loop() {
  // never reached because of deep sleep in setup()
}