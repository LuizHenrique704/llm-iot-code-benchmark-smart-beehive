#include <LoRa_E32.h>

HardwareSerial Serial2(2);
LoRa_E32 e32(&Serial2, 5, 18, 19); // aux, m0, m1

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, 16, 17);
  delay(100);
  e32.begin();

  E32Config cfg = {
    0,                     // ADDH
    1,                     // ADDL
    13,                    // CHAN
    UART_BPS_9600,         // UART baud rate
    MODE_00_8N1,           // UART parity
    AIR_DATA_RATE_010_24,  // Air data rate
    WAKE_UP_250,           // Wireless wake-up time
    IO_D_MODE_PUSH_PULLS_PULL_UPS, // I/O drive mode
    FEC_0_OFF,             // FEC
    POWER_20,              // Transmission power
    FT_FIXED_TRANSMISSION // Fixed transmission mode
  };

  e32.setConfiguration(cfg);
  e32.setMode(NORMAL);
}

void loop() {
  static unsigned long lastSend = 0;
  if (millis() - lastSend >= 5000) {
    lastSend = millis();
    E32ResponseStruct response = e32.sendFixedMessage(0, 3, 13, "teste_lora");
    if (response.status == 0) {
      Serial.println("Transmissão bem-sucedida");
    } else {
      Serial.print("Erro na transmissão, código: ");
      Serial.println(response.status);
    }
  }
}