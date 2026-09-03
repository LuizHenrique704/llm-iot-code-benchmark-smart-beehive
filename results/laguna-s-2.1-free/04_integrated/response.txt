#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <LoRa_E32.h>
#include <HardwareSerial.h>
#include "esp_sleep.h"

#define SDA_PIN 21
#define SCL_PIN 22
#define BME280_ADDRESS 0x76
#define SENSOR_PIN 4
#define UART_RX 16
#define UART_TX 17

HardwareSerial uart2(2);
LoRa_E32 e32ttl(&uart2, 5, 18, 19);

Adafruit_BME280 bme;
bool sensorInitialized = false;

static uint32_t transmissionCount = 0;

typedef struct __attribute__((packed)) {
    char identifier[8];
    uint8_t mac[6];
    float temperature;
    float humidity;
    float pressure;
    float altitude;
    uint8_t hiveState;
    uint32_t transmissions;
} TelemetryData;

void setup() {
    Serial.begin(115200);
    delay(100);

    Wire.begin(SDA_PIN, SCL_PIN);
    delay(100);

    if (!bme.begin(BME280_ADDRESS)) {
        Serial.println("BME280 not found");
        esp_deep_sleep_start();
    }

    sensorInitialized = true;
    pinMode(SENSOR_PIN, INPUT_PULLUP);
    int hiveState = digitalRead(SENSOR_PIN);

    uart2.begin(9600, SERIAL_8N1, UART_RX, UART_TX);
    delay(100);

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

    float temperature = bme.readTemperature();
    float humidity = bme.readHumidity();
    float pressure = bme.readPressure() / 100.0F;
    float altitude = bme.readAltitude(1013.25);

    TelemetryData data;
    strcpy(data.identifier, "colmeia");
    uint64_t chipId = ESP.getEfuseMac();
    memcpy(data.mac, &chipId, 6);
    data.temperature = temperature;
    data.humidity = humidity;
    data.pressure = pressure;
    data.altitude = altitude;
    data.hiveState = (hiveState == HIGH) ? 1 : 0;
    data.transmissions = transmissionCount++;

    int result = e32ttl.sendFixedMessage(0, 3, 13, (uint8_t*)&data, sizeof(data));
    if (result == 0) {
        Serial.println("Transmission successful");
    } else {
        Serial.println("Transmission error");
    }

    e32ttl.setMode(MODE_SLEEP);

    esp_sleep_enable_timer_wakeup(60 * 60 * 1e6);
    esp_sleep_enable_ext0_wakeup(GPIO_NUM_4, 1);
    esp_deep_sleep_start();
}

void loop() {}