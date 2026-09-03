#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <LoRa_E32.h>
#include <HardwareSerial.h>
#include "esp_sleep.h"
#include "esp_wifi.h"

#define SDA_PIN 21
#define SCL_PIN 22
#define BME280_ADDRESS 0x76
#define MC38_PIN 4
#define LORA_AUX 5
#define LORA_M0 18
#define LORA_M1 19
#define LORA_RX 16
#define LORA_TX 17

Adafruit_BME280 bme;
HardwareSerial uart2(2);
LoRa_E32 e32ttl(&uart2, LORA_AUX, LORA_M0, LORA_M1);

RTC_DATA_ATTR uint32_t transmissionCount = 0;

struct __attribute__((packed)) HiveData {
  char id[8];
  uint8_t mac[6];
  float temperature;
  float humidity;
  float pressure;
  float altitude;
  uint8_t isOpen;
  uint32_t count;
};

void setup() {
  Serial.begin(115200);
  delay(100);

  Wire.begin(SDA_PIN, SCL_PIN);
  if (!bme.begin(BME280_ADDRESS)) {
    Serial.println("BME280 initialization failed");
    while (1) delay(1000);
  }

  pinMode(MC38_PIN, INPUT_PULLUP);

  uart2.begin(9600, SERIAL_8N1, LORA_RX, LORA_TX);
  e32ttl.setMode(MODE_CONFIG);
  e32ttl.setAddH(0);
  e32ttl.setAddL(1);
  e32ttl.setChan(13);
  e32ttl.setUARTbaud(UART_BPS_9600);
  e32ttl.setUARTparity(MODE_00_8N1);
  e32ttl.setAirdatarate(AIR_DATA_RATE_010_24);
  e32ttl.setWakeup(WAKE_UP_250);
  e32ttl.setIO_Mode(IO_D_MODE_PUSH_PULLS_PULL_UPS);
  e32ttl.setFEC(FEC_0_OFF);
  e32ttl.setPower(POWER_20);
  e32ttl.setFixedTransmission(FT_FIXED_TRANSMISSION);
  e32ttl.saveParams();
  e32ttl.setMode(MODE_NORMAL);

  esp_sleep_wakeup_cause_t wakeupCause = esp_sleep_get_wakeup_cause();
  if (wakeupCause == ESP_SLEEP_WAKEUP_EXT0 || wakeupCause == ESP_SLEEP_WAKEUP_TIMER) {
    HiveData data;
    strcpy(data.id, "colmeia");
    esp_efuse_mac_get_default(data.mac);
    data.temperature = bme.readTemperature();
    data.humidity = bme.readHumidity();
    data.pressure = bme.readPressure() / 100.0F;
    data.altitude = bme.readAltitude(1013.25);
    data.isOpen = digitalRead(MC38_PIN) == HIGH ? 1 : 0;
    data.count = transmissionCount++;

    int result = e32ttl.sendFixedMessage(0, 3, 13, (uint8_t*)&data, sizeof(data));
    if (result == 0) {
      Serial.println("Transmission successful");
    } else {
      Serial.println("Transmission failed");
    }

    e32ttl.setMode(MODE_CONFIG);
    delay(100);
    e32ttl.setMode(MODE_SLEEP);
    delay(100);
  }

  if (digitalRead(MC38_PIN) == HIGH) {
    esp_sleep_enable_ext0_wakeup(GPIO_NUM_4, 1);
  } else {
    esp_sleep_disable_ext0_wakeup();
  }

  esp_sleep_enable_timer_wakeup(60 * 60 * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {}