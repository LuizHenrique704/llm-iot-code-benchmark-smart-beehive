#include <LoRa_E32.h>

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
    Serial.println("LoRa begin error");
    while (true);
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
    while (true);
  }

  lora.setMode(MODE_0_NORMAL);
}

void loop() {
  static unsigned long lastTime = 0;
  if (millis() - lastTime >= 5000) {
    lastTime = millis();
    const char *msg = "teste_lora";
    int ret = lora.sendFixedMessage(0, 3, 13, msg);
    if (ret == 0) {
      Serial.println("Transmission successful");
    } else {
      Serial.print("Transmission error: ");
      Serial.println(ret);
    }
  }
}