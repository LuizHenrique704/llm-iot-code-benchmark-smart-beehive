# LLM IoT Code Benchmark - Smart Beehive

Projeto experimental para avaliação de códigos de sistemas embarcados gerados por diferentes Large Language Models (LLMs).

O objetivo é comparar a capacidade de diferentes modelos de gerar código Arduino/C++ para um sistema IoT baseado em ESP32 aplicado ao monitoramento de colmeias.

## Objetivo

O experimento avalia códigos gerados por LLMs para diferentes componentes de um sistema de monitoramento de colmeias.

São utilizadas cinco tarefas progressivas:

1. Leitura do sensor BME280.
2. Comunicação LoRa utilizando o módulo E32-TTL-100.
3. Detecção de abertura da colmeia utilizando o sensor magnético MC-38.
4. Integração dos três componentes em um único firmware transmissor.
5. Criação de um firmware receptor compatível com o transmissor gerado.

As etapas 04 e 05 utilizam os códigos previamente gerados pela própria LLM, sem correção manual.

---

## Modelos avaliados

Os seguintes modelos são utilizados no experimento:

| Modelo | Desenvolvedor | Provedor da API |
|---|---|---|
| Gemini 3.8 Flash | Google | Google Gemini API |
| Laguna S 2.1 | Poolside | OpenRouter |
| GPT-OSS 120B | OpenAI | Groq |
| Nemotron 3 Ultra | NVIDIA | OpenRouter |
| GLM-4.7-Flash | Zhipu AI | Cloudflare Workers AI |

Todas as APIs utilizadas possuem acesso gratuito ou free tier durante a realização do experimento.

---

## Hardware

### Microcontrolador

- ESP32 Dev Module

### BME280

- SDA: GPIO 21
- SCL: GPIO 22
- Endereço I2C: `0x76`
- Biblioteca: `Adafruit_BME280`

### MC-38

- GPIO: 4
- Configuração: `INPUT_PULLUP`
- HIGH: colmeia aberta
- LOW: colmeia fechada

### LoRa E32-TTL-100

- UART: UART2
- RX: GPIO 16
- TX: GPIO 17
- AUX: GPIO 5
- M0: GPIO 18
- M1: GPIO 19
- Baud rate: 9600
- Canal: 13
- Biblioteca: `LoRa_E32`

Endereço do transmissor:

```text
ADDH = 0
ADDL = 1
```

Endereço do receptor:

```text
ADDH = 0
ADDL = 3
```

---

## Estrutura do projeto

```text
llm-iot-code-benchmark-smart-beehive/
├── llms/
│   ├── gemini/
│   │   └── gemini.py
│   ├── laguna/
│   │   └── laguna.py
│   ├── gpt_oss/
│   │   └── gpt_oss.py
│   ├── nemotron/
│   │   └── nemotron.py
│   └── glm/
│       └── glm.py
│
├── prompts/
│   ├── 01_bme280.txt
│   ├── 02_lora.txt
│   ├── 03_mc38.txt
│   ├── 04_integrated.txt
│   └── 05_receiver.txt
│
├── experiments/
│   ├── build_prompt_04.py
│   └── build_prompt_05.py
│
├── results/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

# Configuração do ambiente

## 1. Clonar o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd llm-iot-code-benchmark-smart-beehive
```

---

## 2. Criar ambiente virtual

```bash
python3 -m venv .venv
```

### Bash/Zsh

```bash
source .venv/bin/activate
```

### Fish

```fish
source .venv/bin/activate.fish
```

---

## 3. Instalar dependências

```bash
pip install -r requirements.txt
```

As principais dependências são:

```text
google-genai
python-dotenv
openai
groq
requests
```

---

## 4. Configurar as APIs

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Preencha o `.env`:

```env
GEMINI_API_KEY=

OPENROUTER_API_KEY=

GROQ_API_KEY=

CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_TOKEN=
```

O arquivo `.env` contém credenciais privadas e não deve ser enviado para o GitHub.

---

# Configuração experimental

Para reduzir diferenças relacionadas à aleatoriedade da geração, os modelos são configurados com:

```text
temperature = 0.0
```

quando esse parâmetro é suportado pelo modelo e pela API.

Também é utilizado:

```text
max_output_tokens = 16384
```

Os modelos que disponibilizam controle explícito de reasoning utilizam configuração equivalente ao nível médio quando aplicável.

Falhas de infraestrutura, como HTTP 429, HTTP 503, timeouts ou indisponibilidade do provedor, não são consideradas falhas da LLM e não produzem resultados válidos.

Não são realizados retries automáticos.

---

# Execução do experimento

Cada modelo deve executar inicialmente as tarefas 01, 02 e 03.

## Gemini

```bash
python3 llms/gemini/gemini.py 01_bme280
python3 llms/gemini/gemini.py 02_lora
python3 llms/gemini/gemini.py 03_mc38
```

## Laguna

```bash
python3 llms/laguna/laguna.py 01_bme280
python3 llms/laguna/laguna.py 02_lora
python3 llms/laguna/laguna.py 03_mc38
```

## GPT-OSS

```bash
python3 llms/gpt_oss/gpt_oss.py 01_bme280
python3 llms/gpt_oss/gpt_oss.py 02_lora
python3 llms/gpt_oss/gpt_oss.py 03_mc38
```

## Nemotron

```bash
python3 llms/nemotron/nemotron.py 01_bme280
python3 llms/nemotron/nemotron.py 02_lora
python3 llms/nemotron/nemotron.py 03_mc38
```

## GLM

```bash
python3 llms/glm/glm.py 01_bme280
python3 llms/glm/glm.py 02_lora
python3 llms/glm/glm.py 03_mc38
```

---

# Geração da tarefa 04

A tarefa 04 utiliza automaticamente os códigos produzidos nas tarefas:

```text
01_bme280
02_lora
03_mc38
```

O script:

```text
experiments/build_prompt_04.py
```

substitui os placeholders:

```text
{{CODIGO_BME280}}
{{CODIGO_LORA}}
{{CODIGO_MC38}}
```

pelos códigos produzidos pela própria LLM.

Exemplo:

```bash
python3 experiments/build_prompt_04.py gpt-oss-120b
```

O prompt final será criado em:

```text
results/gpt-oss-120b/04_integrated/prompt_generated.txt
```

Depois execute:

```bash
python3 llms/gpt_oss/gpt_oss.py 04_integrated \
  --prompt results/gpt-oss-120b/04_integrated/prompt_generated.txt
```

---

# Geração da tarefa 05

A tarefa 05 utiliza o firmware produzido na tarefa 04.

O script:

```text
experiments/build_prompt_05.py
```

substitui:

```text
{{CODIGO_INTEGRADO}}
```

pelo código gerado em `04_integrated`.

Exemplo:

```bash
python3 experiments/build_prompt_05.py gpt-oss-120b
```

Depois:

```bash
python3 llms/gpt_oss/gpt_oss.py 05_receiver \
  --prompt results/gpt-oss-120b/05_receiver/prompt_generated.txt
```

---

# Diretórios dos modelos

Os nomes utilizados pelos scripts de construção dos prompts são:

```text
gemini-3.8-flash
laguna-s-2.1-free
gpt-oss-120b
nemotron-3-ultra-550b-a55b-free
glm-4.7-flash
```

Exemplo:

```bash
python3 experiments/build_prompt_04.py glm-4.7-flash
```

---

# Resultados

Cada geração é armazenada em:

```text
results/<modelo>/<tarefa>/
```

Exemplo:

```text
results/
└── gpt-oss-120b/
    ├── 01_bme280/
    ├── 02_lora/
    ├── 03_mc38/
    ├── 04_integrated/
    └── 05_receiver/
```

Normalmente cada execução armazena:

```text
prompt.txt
response.txt
code.ino
metadata.json
```

Alguns adaptadores podem salvar informações adicionais fornecidas pela API, como:

```text
reasoning.txt
```

Esses dados são mantidos separadamente do código extraído.

---

# Metadados

Os scripts armazenam informações sobre cada execução, incluindo quando disponibilizadas:

- modelo solicitado;
- modelo retornado pelo provedor;
- provedor da API;
- timestamp;
- temperatura;
- configuração de reasoning;
- limite máximo de tokens;
- tokens de entrada;
- tokens de saída;
- tokens totais;
- tokens de reasoning;
- tokens em cache;
- latência total;
- latência até o primeiro conteúdo;
- custo informado pela API;
- hashes SHA-256;
- tamanho do prompt;
- tamanho da resposta;
- tamanho do código.

---

# Critérios de avaliação

Os códigos gerados são avaliados utilizando os seguintes critérios.

## Corretude funcional

Verificação do funcionamento do código e da integração com os componentes físicos.

## Estrutura do código

Análise estática utilizando:

```text
cppcheck
```

## Code smells

Análise utilizando:

```text
clang-tidy
```

## Uso de recursos

São analisados recursos utilizados no ESP32, incluindo:

- memória Flash;
- RAM;
- variáveis globais.

## Tempo de resposta da API

É registrada a latência da requisição até o término da geração.

Quando o transporte permite, também é registrada a latência até o primeiro conteúdo recebido.

## Consumo de tokens

Quando disponibilizado pelo provedor:

- tokens de entrada;
- tokens de saída;
- tokens de reasoning;
- tokens em cache;
- tokens totais.

## Grau de alucinação

São observados problemas como:

- funções inexistentes;
- bibliotecas inexistentes;
- APIs incorretas;
- recursos inexistentes no hardware;
- comportamento incorreto dos sensores;
- configurações incompatíveis com os componentes utilizados.

---

# Reprodutibilidade

Os códigos retornados pelas LLMs não devem ser corrigidos manualmente antes da avaliação.

O arquivo `response.txt` preserva a resposta recebida da API e o arquivo `code.ino` contém o código extraído para avaliação.

As tarefas 04 e 05 são montadas automaticamente para evitar alterações humanas durante a transferência dos códigos entre as etapas.

---

# Segurança

Nunca envie arquivos contendo chaves de API ao repositório.

O arquivo:

```text
.env
```

deve permanecer no `.gitignore`.

Utilize apenas:

```text
.env.example
```

para documentar as variáveis necessárias.
