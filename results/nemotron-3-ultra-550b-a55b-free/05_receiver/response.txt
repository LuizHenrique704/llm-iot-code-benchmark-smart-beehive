#include <Arduino.h>
#include <LoRa_E32.h>

#define RX_PIN 16
#define TX_PIN 17
#define AUX_PIN 5
#define M0_PIN 18
#define M1_PIN 19

#pragma pack(push, 1)
struct Payload {
  char identifier[8];
  uint8_t mac[6];
  float temperature;
  float humidity;
  float pressure;
  float altitude;
  uint8_t hiveState;
  uint32_t txCounter;
};
#pragma pack(pop)

HardwareSerial LoRaSerial(2);
LoRa_E32 e32ttl(&LoRaSerial, AUX_PIN, M0_PIN, M1_PIN);

void setupLoRaConfig() {
  ResponseStructContainer c = e32ttl.getConfiguration();
  if (c.status.code != 1) {
    Serial.println("Erro ao ler configuracao do modulo LoRa");
    if (c.data) c.close();
    return;
  }
  Configuration configuration = *(Configuration*)c.data;
  c.close();

  configuration.ADDH = 0x00;
  configuration.ADDL = 0x03;
  configuration.CHAN = 0x0D;

  configuration.SPED.uartBaudRate = UART_BPS_9600;
  configuration.SPED.uartParity = MODE_00_8N1;
  configuration.SPED.airDataRate = AIR_DATA_RATE_010_24;

  configuration.OPTION.wirelessWakeupTime = WAKE_UP_250;
  configuration.OPTION.ioDriveMode = IO_D_MODE_PUSH_PULLS_PULL_UPS;
  configuration.OPTION.fec = FEC_0_OFF;
  configuration.OPTION.transmissionPower = POWER_20;
  configuration.OPTION.fixedTransmission = FT_FIXED_TRANSMISSION;

  ResponseStatus rs = e32ttl.setConfiguration(configuration, WRITE_CFG_PWR_DWN_SAVE);
  if (rs.code != 1) {
    Serial.println("Erro ao gravar configuracao no modulo LoRa");
  }
  e32ttl.setMode(MODE_0_NORMAL);
}

void printPayload(const Payload &data) {
  Serial.printf("MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                data.mac[0], data.mac[1], data.mac[2],
                data.mac[3], data.mac[4], data.mac[5]);
  Serial.printf("Temperatura: %.2f C\n", data.temperature);
  Serial.printf("Umidade: %.2f %%\n", data.humidity);
  Serial.printf("Pressao: %.2f hPa\n", data.pressure);
  Serial.printf("Altitude: %.2f m\n", data.altitude);
  Serial.printf("Estado: %s\n", data.hiveState == 1 ? "ABERTA" : "FECHADA");
  Serial.printf("Contador: %lu\n", data.txCounter);
  Serial.println("----------------------------");
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("Iniciando Receptor LoRa E32...");

  LoRaSerial.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);
  if (!e32ttl.begin()) {
    Serial.println("Falha ao inicializar comunicacao com modulo LoRa");
    while (true) delay(1000);
  }

  setupLoRaConfig();
  Serial.println("Receptor pronto. Aguardando pacotes...");
  Serial.println("----------------------------");
}

void loop() {
  if (e32ttl.available() > 1) {
    ResponseContainer rc = e32ttl.receiveMessage(sizeof(Payload));

    if (rc.status.code != 1) {
      Serial.printf("Erro na recepcao: %s\n", rc.status.getResponseDescription().c_str());
      return;
    }

    if (rc.data.size() != sizeof(Payload)) {
      Serial.printf("Tamanho de pacote invalido: %d (esperado %d)\n", rc.data.size(), sizeof(Payload));
      return;
    }

    Payload receivedData;
    memcpy(&receivedData, rc.data.c_str(), sizeof(Payload));

    if (strncmp(receivedData.identifier, "colmeia", 7) != 0) {
      Serial.println("Identificador invalido recebido");
      return;
    }

    printPayload(receivedData);
  }
  delay(10);
}