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
    Serial.println("Erro ao obter configuracao LoRa");
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
    Serial.println("Erro ao salvar configuracao LoRa");
  }
  e32ttl.setMode(MODE_0_NORMAL);
}

void printPayload(const Payload &data) {
  Serial.print("MAC: ");
  for (int i = 0; i < 6; i++) {
    if (data.mac[i] < 0x10) Serial.print('0');
    Serial.print(data.mac[i], HEX);
    if (i < 5) Serial.print(':');
  }
  Serial.println();

  Serial.print("Temperatura: ");
  Serial.print(data.temperature, 2);
  Serial.println(" C");

  Serial.print("Umidade: ");
  Serial.print(data.humidity, 2);
  Serial.println(" %");

  Serial.print("Pressao: ");
  Serial.print(data.pressure, 2);
  Serial.println(" hPa");

  Serial.print("Altitude: ");
  Serial.print(data.altitude, 2);
  Serial.println(" m");

  Serial.print("Estado: ");
  Serial.println(data.hiveState == 1 ? "ABERTA" : "FECHADA");

  Serial.print("Contador: ");
  Serial.println(data.txCounter);
  Serial.println("----------------------------");
}

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("Receptor LoRa E32 Iniciado");

  LoRaSerial.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);
  if (!e32ttl.begin()) {
    Serial.println("Falha ao inicializar modulo LoRa");
    while (1) delay(1000);
  }

  setupLoRaConfig();
  Serial.println("Aguardando pacotes...");
}

void loop() {
  if (e32ttl.available() > 1) {
    ResponseContainer rc = e32ttl.receiveMessage(sizeof(Payload));
    
    if (rc.status.code != 1) {
      Serial.print("Erro recepcao: ");
      Serial.println(rc.status.getResponseDescription());
      return;
    }

    if (rc.data.size() != sizeof(Payload)) {
      Serial.println("Tamanho pacote invalido");
      return;
    }

    Payload receivedData;
    memcpy(&receivedData, rc.data.data(), sizeof(Payload));

    if (strncmp(receivedData.identifier, "colmeia", 7) == 0) {
      printPayload(receivedData);
    } else {
      Serial.println("Identificador desconhecido ignorado");
    }
  }
}