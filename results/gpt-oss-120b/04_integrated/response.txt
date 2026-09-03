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

#define SENSOR_PIN 4

#define LORA_RX 16
#define LORA_TX 17
#define LORA_AUX 5
#define LORA_M0 18
#define LORA_M1 19

#define WAKEUP_INTERVAL_US (60ULL * 60ULL * 1000000ULL) // 60 minutes

Adafruit_BME280 bme;
HardwareSerial SerialLora(2);
LoRa_E32 lora(&SerialLora, LORA_AUX, LORA_M0, LORA_M1);

uint32_t txCounter = 0;
String macString;

void setCpuFreq() {
  setCpuFrequencyMhz(40);
}

String getMacString() {
  uint8_t mac[6];
  esp_read_mac(mac, ESP_MAC_WIFI_STA);
  char buf[18];
  sprintf(buf, "%02X:%02X:%02X:%02X:%02X:%02X",
          mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  return String(buf);
}

bool initBME280() {
  Wire.begin(SDA_PIN, SCL_PIN);
  if (!bme.begin(BME280_ADDRESS, &Wire)) {
    Serial.println("BME280 initialization failed.");
    return false;
  }
  return true;
}

bool initLoRa() {
  SerialLora.begin(9600, SERIAL_8N1, LORA_RX, LORA_TX);
  delay(200);
  if (lora.begin() != 0) {
    Serial.println("LoRa begin error");
    return false;
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
    Serial.println("Set configuration error");
    return false;
  }

  lora.setMode(MODE_0_NORMAL);
  return true;
}

void sendPayload() {
  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0F; // hPa
  float altitude = bme.readAltitude(SEA_LEVEL_PRESSURE);
  uint8_t hiveState = digitalRead(SENSOR_PIN);
  const char *stateStr = (hiveState == HIGH) ? "aberta" : "fechada";

  String payload = "{";
  payload += "\"id\":\"colmeia\",";
  payload += "\"mac\":\"" + macString + "\",";
  payload += "\"temp\":" + String(temperature, 2) + ",";
  payload += "\"hum\":" + String(humidity, 2) + ",";
  payload += "\"pres\":" + String(pressure, 2) + ",";
  payload += "\"alt\":" + String(altitude, 2) + ",";
  payload += "\"estado\":\"" + String(stateStr) + "\",";
  payload += "\"cnt\":" + String(txCounter);
  payload += "}";

  int ret = lora.sendFixedMessage(0, 3, 13, payload.c_str());
  if (ret == 0) {
    Serial.println("Transmission successful");
  } else {
    Serial.print("Transmission error: ");
    Serial.println(ret);
  }
  txCounter++;
}

void configureWakeup() {
  esp_sleep_enable_timer_wakeup(WAKEUP_INTERVAL_US);
  esp_sleep_enable_ext0_wakeup((gpio_num_t)SENSOR_PIN, 1); // wake on HIGH (open)
}

void setup() {
  setCpuFreq();
  Serial.begin(115200);
  pinMode(SENSOR_PIN, INPUT_PULLUP);
  delay(100);

  macString = getMacString();

  if (!initBME280()) {
    // error already printed
    configureWakeup();
    esp_deep_sleep_start();
  }

  if (!initLoRa()) {
    // error already printed
    configureWakeup();
    esp_deep_sleep_start();
  }

  sendPayload();

  configureWakeup();
  esp_deep_sleep_start();
}

void loop() {
  // never reached
}