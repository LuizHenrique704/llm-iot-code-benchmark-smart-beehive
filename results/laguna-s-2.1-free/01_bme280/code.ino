#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

#define SDA_PIN 21
#define SCL_PIN 22
#define BME280_ADDRESS 0x76

Adafruit_BME280 bme;
bool sensorInitialized = false;

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);
  delay(100);

  if (!bme.begin(BME280_ADDRESS)) {
    Serial.println("Erro: Não foi possível inicializar o sensor BME280.");
    sensorInitialized = false;
  } else {
    sensorInitialized = true;
  }
}

void loop() {
  if (!sensorInitialized) {
    return;
  }

  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0F;
  float altitude = bme.readAltitude(1013.25);

  Serial.println(String("Temperatura: ") + String(temperature, 2) + String(" °C"));
  Serial.println(String("Umidade: ") + String(humidity, 2) + String(" %"));
  Serial.println(String("Pressão: ") + String(pressure, 2) + String(" hPa"));
  Serial.println(String("Altitude: ") + String(altitude, 2) + String(" m"));
  Serial.println("-----------------------------");

  delay(2000);
}