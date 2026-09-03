import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# CONFIGURAÇÃO DO MODELO
# ============================================================

MODEL_DEVELOPER = "Zhipu AI"
API_PROVIDER = "Cloudflare Workers AI"

MODEL = "@cf/zai-org/glm-4.7-flash"

# Nome utilizado dentro de results/
RESULT_MODEL_NAME = "glm-4.7-flash"

# Mesmo limite utilizado nos outros modelos
MAX_OUTPUT_TOKENS = 16384

# Padronização da aleatoriedade.
# Depois devemos aplicar o mesmo valor aos outros modelos
# sempre que a API suportar.
TEMPERATURE = 0.0

# GLM suporta controle de reasoning.
REASONING_EFFORT = "medium"

# Timeout máximo da requisição
REQUEST_TIMEOUT_SECONDS = 300


# ============================================================
# LOCALIZAÇÃO DA RAIZ DO PROJETO
# ============================================================

def find_project_root() -> Path:
    """
    Localiza automaticamente a raiz do projeto.

    Estrutura esperada:

    projeto/
    ├── .env
    ├── prompts/
    ├── results/
    └── llms/
        └── glm/
            └── glm.py
    """

    current = Path(__file__).resolve().parent

    for directory in [current, *current.parents]:

        has_prompts = (
            directory / "prompts"
        ).is_dir()

        has_project_marker = (
            (directory / ".env").exists()
            or (directory / ".git").exists()
            or (directory / "requirements.txt").exists()
        )

        if has_prompts and has_project_marker:
            return directory

    raise RuntimeError(
        "Não foi possível localizar a raiz do projeto."
    )


PROJECT_ROOT = find_project_root()

ENV_FILE = PROJECT_ROOT / ".env"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
RESULTS_DIR = PROJECT_ROOT / "results"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def sha256_text(text: str) -> str:
    """
    Calcula SHA-256 do texto.
    """

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def read_prompt(path: Path) -> str:
    """
    Lê um arquivo de prompt.
    """

    if not path.exists():

        print()
        print("ERRO: prompt não encontrado:")
        print(path)

        sys.exit(1)

    return path.read_text(
        encoding="utf-8"
    )


def extract_code(response: str) -> str:
    """
    Extrai código Arduino caso a LLM responda dentro de:

    ```cpp
    ...
    ```

    response.txt permanece com a resposta original da LLM.
    code.ino recebe apenas o código.
    """

    response = response.strip()

    pattern = (
        r"```(?:cpp|c\+\+|arduino|ino)?"
        r"\s*(.*?)```"
    )

    match = re.search(
        pattern,
        response,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if match:
        return (
            match
            .group(1)
            .strip()
        )

    return response


def relative_path(path: Path) -> str:
    """
    Retorna o caminho relativo à raiz do projeto.
    """

    try:
        return str(
            path.relative_to(
                PROJECT_ROOT
            )
        )

    except ValueError:
        return str(path)


# ============================================================
# EXECUÇÃO DO GLM
# ============================================================

def run_glm(prompt: str):
    """
    Executa GLM-4.7-Flash através da REST API direta
    do Cloudflare Workers AI.

    Não utiliza streaming devido aos erros de
    incomplete chunked read observados durante os testes.

    Retorna:
    - conteúdo da resposta
    - usage
    - latência total
    - latência até primeiro conteúdo
    - response_id
    - modelo retornado
    - system fingerprint
    """

    load_dotenv(
        ENV_FILE
    )

    account_id = os.getenv(
        "CLOUDFLARE_ACCOUNT_ID"
    )

    api_token = os.getenv(
        "CLOUDFLARE_API_TOKEN"
    )

    # ========================================================
    # VALIDA CREDENCIAIS
    # ========================================================

    if not account_id:

        print()
        print(
            "ERRO: CLOUDFLARE_ACCOUNT_ID "
            "não encontrado no .env"
        )

        sys.exit(1)

    if not api_token:

        print()
        print(
            "ERRO: CLOUDFLARE_API_TOKEN "
            "não encontrado no .env"
        )

        sys.exit(1)

    # ========================================================
    # ENDPOINT
    # ========================================================

    url = (
        "https://api.cloudflare.com/client/v4/"
        f"accounts/{account_id}/ai/run/{MODEL}"
    )

    headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Connection": "close",
}

    # ========================================================
    # PAYLOAD
    # ========================================================

    payload = {

        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],

        "max_completion_tokens":
            MAX_OUTPUT_TOKENS,

        "temperature":
            TEMPERATURE,

        "reasoning_effort":
            REASONING_EFFORT,

        "stream":
            False,
    }

    # ========================================================
    # CHAMADA DA API
    # ========================================================

    start_time = (
        time.perf_counter()
    )

    response = requests.post(
    url,
    headers=headers,
    json=payload,
    timeout=(30, 300),
)

    end_time = (
        time.perf_counter()
    )

    # ========================================================
    # VALIDA HTTP
    # ========================================================

    if not response.ok:

        raise RuntimeError(
            f"HTTP {response.status_code}: "
            f"{response.text}"
        )

    # ========================================================
    # DECODIFICA JSON
    # ========================================================

    try:

        data = response.json()

    except requests.exceptions.JSONDecodeError:

        raise RuntimeError(
            "A Cloudflare retornou uma resposta "
            "que não é JSON válido."
        )

    # ========================================================
    # VALIDA RESPOSTA CLOUDFLARE
    # ========================================================

    if not data.get(
        "success",
        False
    ):

        raise RuntimeError(
            "Cloudflare retornou erro: "
            f"{data}"
        )

    result = data.get(
        "result",
        {}
    )

    if not result:

        raise RuntimeError(
            "Cloudflare retornou success=true, "
            "mas result está vazio."
        )

    # ========================================================
    # CONTEÚDO
    # ========================================================

    response_text = ""

    choices = result.get(
        "choices",
        []
    )

    if choices:

        message = (
            choices[0]
            .get(
                "message",
                {}
            )
        )

        # Pegamos apenas o conteúdo final.
        #
        # Não incluímos:
        # reasoning
        # reasoning_content
        #
        # Isso evita inserir raciocínio interno no code.ino.
        response_text = (
            message.get(
                "content",
                ""
            )
            or ""
        )

    # ========================================================
    # USAGE
    # ========================================================

    usage = result.get(
        "usage",
        {}
    )

    # ========================================================
    # IDENTIFICADORES
    # ========================================================

    response_id = result.get(
        "id"
    )

    returned_model = result.get(
        "model"
    )

    system_fingerprint = result.get(
        "system_fingerprint"
    )

    # ========================================================
    # LATÊNCIA
    # ========================================================

    total_latency = (
        end_time
        - start_time
    )

    # Sem streaming não conseguimos medir
    # o tempo até o primeiro token.
    first_content_latency = None

    return (
        response_text,
        usage,
        total_latency,
        first_content_latency,
        response_id,
        returned_model,
        system_fingerprint,
    )


# ============================================================
# SALVAMENTO DOS RESULTADOS
# ============================================================

def save_result(
    task: str,
    prompt: str,
    prompt_path: Path,
    response_text: str,
    usage,
    latency: float,
    first_content_latency,
    response_id,
    returned_model,
    system_fingerprint,
):
    """
    Salva:

    prompt.txt
    response.txt
    code.ino
    metadata.json
    """

    result_dir = (
        RESULTS_DIR
        / RESULT_MODEL_NAME
        / task
    )

    result_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # EXTRAI CÓDIGO
    # ========================================================

    code = extract_code(
        response_text
    )

    # ========================================================
    # CAMINHOS
    # ========================================================

    prompt_output = (
        result_dir
        / "prompt.txt"
    )

    response_output = (
        result_dir
        / "response.txt"
    )

    code_output = (
        result_dir
        / "code.ino"
    )

    metadata_output = (
        result_dir
        / "metadata.json"
    )

    # ========================================================
    # SALVA PROMPT
    # ========================================================

    prompt_output.write_text(
        prompt,
        encoding="utf-8"
    )

    # ========================================================
    # SALVA RESPOSTA ORIGINAL DA LLM
    # ========================================================

    response_output.write_text(
        response_text,
        encoding="utf-8"
    )

    # ========================================================
    # SALVA CÓDIGO EXTRAÍDO
    # ========================================================

    code_output.write_text(
        code,
        encoding="utf-8"
    )

    # ========================================================
    # TOKENS
    # ========================================================

    input_tokens = usage.get(
        "prompt_tokens"
    )

    output_tokens = usage.get(
        "completion_tokens"
    )

    total_tokens = usage.get(
        "total_tokens"
    )

    prompt_details = usage.get(
        "prompt_tokens_details",
        {}
    ) or {}

    cached_tokens = (
        prompt_details.get(
            "cached_tokens"
        )
    )

    # A Cloudflare atualmente não fornece
    # separadamente reasoning_tokens no mesmo
    # formato dos outros provedores.
    reasoning_tokens = None

    # ========================================================
    # NEURONS
    # ========================================================

    neurons = usage.get(
        "neurons"
    )

    # ========================================================
    # METADADOS
    # ========================================================

    metadata = {

        "model_developer":
            MODEL_DEVELOPER,

        "api_provider":
            API_PROVIDER,

        "requested_model":
            MODEL,

        "returned_model":
            returned_model,

        "task":
            task,

        "timestamp_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "prompt_file":
            relative_path(
                prompt_path
            ),

        "response_id":
            response_id,

        "system_fingerprint":
            system_fingerprint,

        # ----------------------------------------------------
        # LATÊNCIA
        # ----------------------------------------------------

        "latency_seconds":
            round(
                latency,
                6
            ),

        "first_content_latency_seconds":
            (
                round(
                    first_content_latency,
                    6
                )
                if first_content_latency
                is not None
                else None
            ),

        # ----------------------------------------------------
        # TOKENS
        # ----------------------------------------------------

        "tokens": {

            "input":
                input_tokens,

            "output":
                output_tokens,

            "reasoning":
                reasoning_tokens,

            "cached":
                cached_tokens,

            "total":
                total_tokens,
        },

        # ----------------------------------------------------
        # MÉTRICA CLOUDFLARE
        # ----------------------------------------------------

        "neurons":
            neurons,

        # ----------------------------------------------------
        # CONFIGURAÇÃO DA GERAÇÃO
        # ----------------------------------------------------

        "generation_config": {

            "max_output_tokens":
                MAX_OUTPUT_TOKENS,

            "temperature":
                TEMPERATURE,

            "reasoning_effort":
                REASONING_EFFORT,

            "stream":
                False,
        },

        # ----------------------------------------------------
        # USAGE COMPLETO
        # ----------------------------------------------------

        "raw_usage":
            usage,

        # ----------------------------------------------------
        # INTEGRIDADE
        # ----------------------------------------------------

        "integrity": {

            "prompt_sha256":
                sha256_text(
                    prompt
                ),

            "response_sha256":
                sha256_text(
                    response_text
                ),

            "code_sha256":
                sha256_text(
                    code
                ),
        },

        # ----------------------------------------------------
        # TAMANHOS
        # ----------------------------------------------------

        "prompt_characters":
            len(
                prompt
            ),

        "response_characters":
            len(
                response_text
            ),

        "code_characters":
            len(
                code
            ),
    }

    # ========================================================
    # SALVA METADATA
    # ========================================================

    metadata_output.write_text(

        json.dumps(
            metadata,
            indent=4,
            ensure_ascii=False
        ),

        encoding="utf-8"
    )

    return (
        result_dir,
        metadata
    )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Executa prompts do benchmark utilizando "
            "GLM-4.7-Flash via Cloudflare Workers AI."
        )
    )

    parser.add_argument(
        "task",
        help=(
            "Nome da tarefa. "
            "Exemplo: 01_bme280"
        ),
    )

    parser.add_argument(
        "--prompt",
        type=Path,
        help=(
            "Arquivo de prompt personalizado. "
            "Se omitido será usado "
            "prompts/<task>.txt"
        ),
    )

    args = parser.parse_args()

    # ========================================================
    # LOCALIZA PROMPT
    # ========================================================

    if args.prompt:

        prompt_path = (
            args.prompt
        )

        if not prompt_path.is_absolute():

            prompt_path = (
                PROJECT_ROOT
                / prompt_path
            )

    else:

        prompt_path = (
            PROMPTS_DIR
            / f"{args.task}.txt"
        )

    # ========================================================
    # LÊ PROMPT
    # ========================================================

    prompt = read_prompt(
        prompt_path
    )

    # ========================================================
    # INFORMAÇÕES
    # ========================================================

    print()

    print(
        "----------------------------------------"
    )

    print(
        "LLM IoT Code Benchmark"
    )

    print(
        "----------------------------------------"
    )

    print(
        f"Developer   : {MODEL_DEVELOPER}"
    )

    print(
        f"Provider    : {API_PROVIDER}"
    )

    print(
        f"Modelo      : {MODEL}"
    )

    print(
        f"Tarefa      : {args.task}"
    )

    print(
        f"Temperature : {TEMPERATURE}"
    )

    print(
        f"Reasoning   : {REASONING_EFFORT}"
    )

    print(
        f"Prompt      : {prompt_path}"
    )

    print(
        "----------------------------------------"
    )

    print(
        "Enviando prompt..."
    )

    # ========================================================
    # CHAMADA
    # ========================================================

    try:

        (
            response_text,
            usage,
            latency,
            first_content_latency,
            response_id,
            returned_model,
            system_fingerprint,

        ) = run_glm(
            prompt
        )

    except Exception as error:

        print()

        print(
            "ERRO durante a chamada da API:"
        )

        print(error)

        # Sem retry automático.
        #
        # Erros de API/infraestrutura não devem
        # gerar automaticamente uma nova geração.

        sys.exit(1)

    # ========================================================
    # VALIDA CONTEÚDO
    # ========================================================

    if not response_text.strip():

        print()

        print(
            "ERRO: a API retornou "
            "uma resposta sem conteúdo."
        )

        sys.exit(1)

    # ========================================================
    # SALVA
    # ========================================================

    try:

        (
            result_dir,
            metadata

        ) = save_result(

            task=args.task,

            prompt=prompt,

            prompt_path=prompt_path,

            response_text=response_text,

            usage=usage,

            latency=latency,

            first_content_latency=(
                first_content_latency
            ),

            response_id=response_id,

            returned_model=(
                returned_model
            ),

            system_fingerprint=(
                system_fingerprint
            ),
        )

    except Exception as error:

        print()

        print(
            "ERRO ao salvar resultados:"
        )

        print(error)

        sys.exit(1)

    # ========================================================
    # RESULTADOS
    # ========================================================

    tokens = metadata[
        "tokens"
    ]

    print()

    print(
        "Resposta recebida com sucesso."
    )

    print()

    print(
        "Latência total: "
        f"{metadata['latency_seconds']} s"
    )

    print(
        "Latência até primeiro conteúdo: "
        f"{metadata['first_content_latency_seconds']}"
    )

    print()

    print(
        "Tokens de entrada   : "
        f"{tokens['input']}"
    )

    print(
        "Tokens de saída     : "
        f"{tokens['output']}"
    )

    print(
        "Tokens de reasoning : "
        f"{tokens['reasoning']}"
    )

    print(
        "Tokens em cache     : "
        f"{tokens['cached']}"
    )

    print(
        "Tokens totais       : "
        f"{tokens['total']}"
    )

    print(
        "Neurons Cloudflare  : "
        f"{metadata['neurons']}"
    )

    print()

    print(
        "Modelo retornado: "
        f"{metadata['returned_model']}"
    )

    print()

    print(
        "Arquivos salvos em:"
    )

    print(
        result_dir
    )

    print()

    print(
        "  prompt.txt"
    )

    print(
        "  response.txt"
    )

    print(
        "  code.ino"
    )

    print(
        "  metadata.json"
    )

    print()


if __name__ == "__main__":
    main()