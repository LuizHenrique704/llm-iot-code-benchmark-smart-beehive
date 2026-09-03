#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

#define SDA_PIN 21
#define SCL_PIN 22
#define BME280_ADDRESS 0x76
#define SEA_LEVEL_PRESSURE 1013.25

Adafruit_BME280 bme;

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);
  if (!bme.begin(BME280_ADDRESS, &Wire)) {
    Serial.println("BME280 initialization failed. Check wiring and address.");
    while (true) {
      delay(10);
    }
  }
}

void loop() {
  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0F; // hPa
  float altitude = bme.readAltitude(SEA_LEVEL_PRESSURE);

  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.println(" °C");

  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.println(" %");

  Serial.print("Pressure: ");
  Serial.print(pressure);
  Serial.println(" hPa");

  Serial.print("Altitude: ");
  Serial.print(altitude);
  Serial.println(" m");

  Serial.println();
  delay(2000);
}