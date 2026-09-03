#include <Arduino.h>
#include <LoRa_E32.h>

#define RX_PIN 16
#define TX_PIN 17
#define AUX_PIN 5
#define M0_PIN 18
#define M1_PIN 19

HardwareSerial LoRaSerial(2);
LoRa_E32 e32ttl(&LoRaSerial, AUX_PIN, M0_PIN, M1_PIN);

void printParameters(struct Configuration configuration);
void printModuleInformation(struct ModuleInformation moduleInformation);

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }
  Serial.println("Iniciando teste LoRa E32-TTL-100...");

  LoRaSerial.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);
  
  if (!e32ttl.begin()) {
    Serial.println("Falha ao inicializar o modulo E32!");
    while (1) delay(1000);
  }
  Serial.println("Modulo E32 inicializado.");

  ResponseStructContainer c = e32ttl.getConfiguration();
  if (c.status.code != 1) {
    Serial.print("Erro ao ler configuracao: ");
    Serial.println(c.status.getResponseDescription());
    while (1) delay(1000);
  }
  Configuration configuration = *(Configuration*)c.data;
  c.close();

  configuration.ADDH = 0x00;
  configuration.ADDL = 0x01;
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
    Serial.print("Erro ao salvar configuracao: ");
    Serial.println(rs.getResponseDescription());
    while (1) delay(1000);
  }
  Serial.println("Configuracao aplicada e salva com sucesso.");
  printParameters(configuration);

  ResponseStatus rsMode = e32ttl.setMode(MODE_0_NORMAL);
  if (rsMode.code != 1) {
    Serial.print("Erro ao definir modo normal: ");
    Serial.println(rsMode.getResponseDescription());
  } else {
    Serial.println("Modo Normal (MODE_0) ativado.");
  }
  
  Serial.println("--- Iniciando loop de transmissao (a cada 5s) ---");
}

void loop() {
  static unsigned long lastSend = 0;
  const unsigned long interval = 5000;

  if (millis() - lastSend >= interval) {
    lastSend = millis();

    Serial.print("Enviando 'teste_lora' para ADDH=0, ADDL=3, CHAN=13... ");
    
    ResponseStatus rs = e32ttl.sendFixedMessage(0x00, 0x03, 0x0D, "teste_lora");
    
    if (rs.code == 1) {
      Serial.println("SUCESSO");
    } else {
      Serial.print("FALHA - Codigo: ");
      Serial.print(rs.code);
      Serial.print(" - ");
      Serial.println(rs.getResponseDescription());
    }
  }
}

void printParameters(struct Configuration configuration) {
  Serial.println("----------------------------------------");
  Serial.print("HEAD: "); Serial.print(configuration.HEAD, HEX); Serial.print(" "); Serial.print(configuration.HEAD, BIN); Serial.println();
  Serial.print("ADDH: "); Serial.println(configuration.ADDH, HEX);
  Serial.print("ADDL: "); Serial.println(configuration.ADDL, HEX);
  Serial.print("CHAN: "); Serial.println(configuration.CHAN, HEX);
  Serial.println("--- SPED ---");
  Serial.print("uartParity: "); Serial.println(configuration.SPED.uartParity, BIN);
  Serial.print("uartBaudRate: "); Serial.println(configuration.SPED.uartBaudRate, BIN);
  Serial.print("airDataRate: "); Serial.println(configuration.SPED.airDataRate, BIN);
  Serial.println("--- OPTION ---");
  Serial.print("fixedTransmission: "); Serial.println(configuration.OPTION.fixedTransmission, BIN);
  Serial.print("ioDriveMode: "); Serial.println(configuration.OPTION.ioDriveMode, BIN);
  Serial.print("wirelessWakeupTime: "); Serial.println(configuration.OPTION.wirelessWakeupTime, BIN);
  Serial.print("fec: "); Serial.println(configuration.OPTION.fec, BIN);
  Serial.print("transmissionPower: "); Serial.println(configuration.OPTION.transmissionPower, BIN);
  Serial.println("----------------------------------------");
}