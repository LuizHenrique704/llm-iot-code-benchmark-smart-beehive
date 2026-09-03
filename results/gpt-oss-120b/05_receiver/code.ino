#include <Arduino.h>
#include <LoRa_E32.h>
#include <ArduinoJson.h>

#define LORA_RX 16
#define LORA_TX 17
#define LORA_AUX 5
#define LORA_M0 18
#define LORA_M1 19

HardwareSerial SerialLora(2);
LoRa_E32 lora(&SerialLora, LORA_AUX, LORA_M0, LORA_M1);

void setup() {
  Serial.begin(115200);
  SerialLora.begin(9600, SERIAL_8N1, LORA_RX, LORA_TX);
  delay(200);

  if (lora.begin() != 0) {
    Serial.println("LoRa init error");
    while (true) delay(100);
  }

  Configuration cfg;
  cfg.ADDH = 0;
  cfg.ADDL = 3;
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
    while (true) delay(100);
  }

  lora.setMode(MODE_0_NORMAL);
}

void loop() {
  uint8_t buffer[256];
  uint16_t len = sizeof(buffer);
  int ret = lora.receiveMessage(buffer, &len);
  if (ret == 0) {
    if (len >= sizeof(buffer)) len = sizeof(buffer) - 1;
    buffer[len] = 0; // null‑terminate

    StaticJsonDocument<256> doc;
    DeserializationError err = deserializeJson(doc, (char *)buffer);
    if (err) {
      Serial.print("JSON parse error: ");
      Serial.println(err.c_str());
      return;
    }

    const char *id = doc["id"];
    if (!id || strcmp(id, "colmeia") != 0) {
      // not a hive packet
      return;
    }

    const char *mac = doc["mac"];
    float temp = doc["temp"];
    float hum  = doc["hum"];
    float pres = doc["pres"];
    float alt  = doc["alt"];
    const char *estado = doc["estado"];
    unsigned long cnt = doc["cnt"];

    Serial.print("MAC: ");
    Serial.println(mac ? mac : "N/A");

    Serial.print("Temperatura: ");
    Serial.print(temp, 2);
    Serial.println(" C");

    Serial.print("Umidade: ");
    Serial.print(hum, 2);
    Serial.println(" %");

    Serial.print("Pressao: ");
    Serial.print(pres, 2);
    Serial.println(" hPa");

    Serial.print("Altitude: ");
    Serial.print(alt, 2);
    Serial.println(" m");

    Serial.print("Estado: ");
    if (estado && strcmp(estado, "aberta") == 0) {
      Serial.println("ABERTA");
    } else {
      Serial.println("FECHADA");
    }

    Serial.print("Contador: ");
    Serial.println(cnt);
  } else {
    Serial.print("Receive error: ");
    Serial.println(ret);
  }

  delay(10);
}