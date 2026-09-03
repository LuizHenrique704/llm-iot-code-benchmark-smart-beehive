#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

#define I2C_SDA 21
#define I2C_SCL 22
#define BME280_ADDR 0x76
#define SEALEVELPRESSURE_HPA (1013.25)

Adafruit_BME280 bme;

void setup() {
  Serial.begin(115200);
  delay(1000);

  Wire.begin(I2C_SDA, I2C_SCL);

  if (!bme.begin(BME280_ADDR, &Wire)) {
    Serial.println("Erro: Nao foi possivel encontrar o sensor BME280 no endereco 0x76.");
    Serial.println("Verifique a alimentacao e as conexoes I2C (SDA=GPIO21, SCL=GPIO22).");
    while (1) {
      delay(1000);
    }
  }

  Serial.println("BME280 inicializado com sucesso.");
}

void loop() {
  float temperatura = bme.readTemperature();
  float umidade = bme.readHumidity();
  float pressao = bme.readPressure() / 100.0F;
  float altitude = bme.readAltitude(SEALEVELPRESSURE_HPA);

  if (isnan(temperatura) || isnan(umidade) || isnan(pressao)) {
    Serial.println("Falha na leitura dos dados do sensor BME280.");
  } else {
    Serial.print("Temperatura: ");
    Serial.print(temperatura);
    Serial.println(" °C");

    Serial.print("Umidade: ");
    Serial.print(umidade);
    Serial.println(" %");

    Serial.print("Pressao: ");
    Serial.print(pressao);
    Serial.println(" hPa");

    Serial.print("Altitude Estimada: ");
    Serial.print(altitude);
    Serial.println(" m");

    Serial.println("------------------------------------");
  }

  delay(2000);
}