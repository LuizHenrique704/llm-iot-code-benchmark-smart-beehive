#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

#define SEALEVELPRESSURE_HPA (1013.25)

Adafruit_BME280 bme;

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }

  Wire.begin(21, 22);
  if (!bme.begin(0x76, &Wire)) {
    Serial.println("Erro: BME280 não encontrado no endereço 0x76.");
    while (true) {
      delay(100);
    }
  }
}

void loop() {
  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0F;
  float altitude = bme.readAltitude(SEALEVELPRESSURE_HPA);

  Serial.print("Temperatura: ");
  Serial.print(temperature);
  Serial.println(" *C");

  Serial.print("Umidade: ");
  Serial.print(humidity);
  Serial.println(" %");

  Serial.print("Pressao: ");
  Serial.print(pressure);
  Serial.println(" hPa");

  Serial.print("Altitude: ");
  Serial.print(altitude);
  Serial.println(" m");

  Serial.println("---------------------------");
  delay(2000);
}