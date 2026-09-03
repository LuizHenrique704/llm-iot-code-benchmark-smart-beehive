#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

#define SDA_PIN 21
#define SCL_PIN 22
#define BME280_ADDRESS 0x76
#define SEALEVELPRESSURE_HPA 1013.25

Adafruit_BME280 bme;

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }

  Wire.begin(SDA_PIN, SCL_PIN);

  if (!bme.begin(BME280_ADDRESS, &Wire)) {
    Serial.println("Falha ao inicializar o sensor BME280 no endereco 0x76. Verifique a ligacao I2C.");
    while (1) {
      delay(1000);
    }
  }

  Serial.println("BME280 inicializado com sucesso.");
  Serial.println("------------------------------------");
}

void loop() {
  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0F;
  float altitude = bme.readAltitude(SEALEVELPRESSURE_HPA);

  if (isnan(temperature) || isnan(humidity) || isnan(pressure) || isnan(altitude)) {
    Serial.println("Erro ao ler dados do sensor BME280.");
  } else {
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

    Serial.println("------------------------------------");
  }

  delay(2000);
}