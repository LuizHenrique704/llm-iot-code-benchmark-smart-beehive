#include <Wire.h>
#include <Adafruit_BME280.h>
#include <Adafruit_Sensor.h>

#define SEALEVELPRESSURE_HPA 1013.25

Adafruit_BME280 bme;

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);

  if (!bme.begin(0x76)) {
    Serial.println("Could not find a valid BME280 sensor, check wiring!");
    while (1);
  }
}

void loop() {
  delay(2000);

  Serial.print("Temperature = ");
  Serial.print(bme.readTemperature());
  Serial.println(" *C");

  Serial.print("Humidity = ");
  Serial.print(bme.readHumidity());
  Serial.println(" %");

  Serial.print("Pressure = ");
  Serial.print(bme.readPressure());
  Serial.println(" hPa");

  Serial.print("Approx altitude = ");
  Serial.print(bme.readAltitude(SEALEVELPRESSURE_HPA));
  Serial.println(" m");

  Serial.println();
}