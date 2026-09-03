import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# CONFIGURAÇÃO DO MODELO
# ============================================================

MODEL_DEVELOPER = "Poolside"
API_PROVIDER = "OpenRouter"

MODEL = "poolside/laguna-s-2.1:free"

RESULT_MODEL_NAME = "laguna-s-2.1-free"

MAX_OUTPUT_TOKENS = 16384
TEMPERATURE = 0.0

# ============================================================
# LOCALIZAÇÃO DA RAIZ DO PROJETO
# ============================================================

def find_project_root() -> Path:
    """
    Localiza automaticamente a raiz do projeto.

    Isso permite manter este arquivo em:

    llms/deepseek/deepseek.py
    """

    current = Path(__file__).resolve().parent

    for directory in [current, *current.parents]:

        has_prompts = (
            directory / "prompts"
        ).is_dir()

        has_project_marker = (
            (directory / ".env").exists()
            or (directory / ".git").exists()
            or (
                directory
                / "requirements.txt"
            ).exists()
        )

        if (
            has_prompts
            and has_project_marker
        ):
            return directory

    raise RuntimeError(
        "Não foi possível localizar a raiz "
        "do projeto. Verifique se a pasta "
        "prompts/ existe na raiz."
    )


PROJECT_ROOT = find_project_root()

ENV_FILE = (
    PROJECT_ROOT / ".env"
)

PROMPTS_DIR = (
    PROJECT_ROOT / "prompts"
)

RESULTS_DIR = (
    PROJECT_ROOT / "results"
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def sha256_text(text: str) -> str:
    """
    Calcula SHA-256.

    Permite verificar posteriormente
    se prompt, resposta ou código
    foram alterados.
    """

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def read_prompt(
    prompt_path: Path
) -> str:
    """
    Lê o prompt armazenado em arquivo.
    """

    if not prompt_path.exists():

        print()
        print(
            "ERRO: prompt não encontrado:"
        )
        print(prompt_path)

        sys.exit(1)

    return prompt_path.read_text(
        encoding="utf-8"
    )


def extract_code(
    response: str
) -> str:
    """
    Extrai código da resposta.

    Se a LLM retornar:

    ```cpp
    código
    ```

    as marcações Markdown são removidas
    somente do code.ino.

    response.txt permanece exatamente
    com a resposta recebida da API.
    """

    response = response.strip()

    pattern = (
        r"```(?:cpp|c\+\+|arduino|ino)?"
        r"\s*(.*?)```"
    )

    match = re.search(
        pattern,
        response,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        )
    )

    if match:
        return (
            match
            .group(1)
            .strip()
        )

    return response


def object_to_dict(obj):
    """
    Converte objetos retornados pelo
    SDK para dicionário quando possível.
    """

    if obj is None:
        return {}

    if isinstance(obj, dict):
        return obj

    if hasattr(obj, "model_dump"):

        try:
            return obj.model_dump()
        except Exception:
            pass

    if hasattr(obj, "dict"):

        try:
            return obj.dict()
        except Exception:
            pass

    return {}


def get_nested_value(
    data,
    *keys
):
    """
    Busca valores em dicionários aninhados.
    """

    current = data

    for key in keys:

        if not isinstance(
            current,
            dict
        ):
            return None

        current = current.get(key)

        if current is None:
            return None

    return current


# ============================================================
# CHAMADA DA API
# ============================================================

def run_deepseek(
    prompt: str
):
    """
    Executa o DeepSeek V4 Flash através
    do OpenRouter utilizando streaming.

    Retorna:

    - texto completo;
    - informações de uso;
    - latência total;
    - latência até o primeiro conteúdo;
    - ID da resposta;
    - modelo efetivamente retornado.
    """

    load_dotenv(
        ENV_FILE
    )

    api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )

    if not api_key:

        print()

        print(
            "ERRO: OPENROUTER_API_KEY "
            "não encontrada."
        )

        print()

        print(
            f"Verifique o arquivo: "
            f"{ENV_FILE}"
        )

        sys.exit(1)

    # ========================================================
    # CLIENTE OPENROUTER
    # ========================================================

    client = OpenAI(
        base_url=(
            "https://openrouter.ai/api/v1"
        ),
        api_key=api_key,
    )

    response_parts = []

    usage = None

    response_id = None

    returned_model = None

    first_content_time = None

    start_time = (
        time.perf_counter()
    )

    try:

        stream = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": prompt,
        }
    ],
    max_tokens=MAX_OUTPUT_TOKENS,
    temperature=TEMPERATURE,
    stream=True,
)

        for chunk in stream:

            # ================================================
            # ID DA RESPOSTA
            # ================================================

            chunk_id = getattr(
                chunk,
                "id",
                None
            )

            if chunk_id:
                response_id = chunk_id

            # ================================================
            # MODELO RETORNADO
            # ================================================

            chunk_model = getattr(
                chunk,
                "model",
                None
            )

            if chunk_model:
                returned_model = (
                    chunk_model
                )

            # ================================================
            # TOKENS / USAGE
            # ================================================

            chunk_usage = getattr(
                chunk,
                "usage",
                None
            )

            if chunk_usage is not None:
                usage = chunk_usage

            # ================================================
            # CONTEÚDO
            # ================================================

            choices = getattr(
                chunk,
                "choices",
                None
            )

            if not choices:
                continue

            delta = getattr(
                choices[0],
                "delta",
                None
            )

            if delta is None:
                continue

            content = getattr(
                delta,
                "content",
                None
            )

            if not content:
                continue

            if (
                first_content_time
                is None
            ):

                first_content_time = (
                    time.perf_counter()
                )

            response_parts.append(
                content
            )

        end_time = (
            time.perf_counter()
        )

    finally:

        client.close()

    # ========================================================
    # RESPOSTA FINAL
    # ========================================================

    response_text = "".join(
        response_parts
    )

    total_latency = (
        end_time
        - start_time
    )

    if (
        first_content_time
        is not None
    ):

        first_content_latency = (
            first_content_time
            - start_time
        )

    else:

        first_content_latency = None

    return (
        response_text,
        usage,
        total_latency,
        first_content_latency,
        response_id,
        returned_model,
    )


# ============================================================
# SALVAMENTO
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
):
    """
    Salva os resultados da execução.
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
    # PROMPT UTILIZADO
    # ========================================================

    prompt_output.write_text(
        prompt,
        encoding="utf-8"
    )

    # ========================================================
    # RESPOSTA BRUTA
    # ========================================================

    response_output.write_text(
        response_text,
        encoding="utf-8"
    )

    # ========================================================
    # CÓDIGO EXTRAÍDO
    # ========================================================

    code_output.write_text(
        code,
        encoding="utf-8"
    )

    # ========================================================
    # USAGE
    # ========================================================

    usage_data = (
        object_to_dict(
            usage
        )
    )

    input_tokens = (
        usage_data.get(
            "prompt_tokens"
        )
    )

    output_tokens = (
        usage_data.get(
            "completion_tokens"
        )
    )

    total_tokens = (
        usage_data.get(
            "total_tokens"
        )
    )

    # ========================================================
    # REASONING TOKENS
    # ========================================================

    reasoning_tokens = (
        get_nested_value(
            usage_data,
            "completion_tokens_details",
            "reasoning_tokens",
        )
    )

    # ========================================================
    # TOKENS EM CACHE
    # ========================================================

    cached_tokens = (
        get_nested_value(
            usage_data,
            "prompt_tokens_details",
            "cached_tokens",
        )
    )

    # ========================================================
    # CUSTO
    # ========================================================

    # OpenRouter pode retornar informações
    # adicionais de custo no objeto usage.
    cost = usage_data.get(
        "cost"
    )

    cost_details = (
        usage_data.get(
            "cost_details"
        )
    )

    # ========================================================
    # METADATA
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
            str(
                prompt_path
                .relative_to(
                    PROJECT_ROOT
                )
            ),

        "response_id":
            response_id,

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
                if (
                    first_content_latency
                    is not None
                )
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
        # CUSTO INFORMADO PELO OPENROUTER
        # ----------------------------------------------------

        "cost": cost,

        "cost_details":
            cost_details,

        # ----------------------------------------------------
        # CONFIGURAÇÃO
        # ----------------------------------------------------

"generation_config": {
    "max_output_tokens": MAX_OUTPUT_TOKENS,
    "temperature": TEMPERATURE,
    "stream": True,
},

        # ----------------------------------------------------
        # USAGE ORIGINAL
        # ----------------------------------------------------

        "raw_usage":
            usage_data,

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
        # TAMANHO
        # ----------------------------------------------------

        "response_characters":
            len(
                response_text
            ),

        "code_characters":
            len(
                code
            ),
    }

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
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    parser = (
        argparse.ArgumentParser(
            description=(
                "Executa um prompt do "
                "benchmark utilizando "
                "DeepSeek V4 Flash "
                "via OpenRouter."
            )
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
            "Arquivo de prompt opcional. "
            "Se omitido será utilizado "
            "prompts/<task>.txt"
        ),
    )

    args = parser.parse_args()

    # ========================================================
    # PROMPT
    # ========================================================

    if args.prompt:

        prompt_path = (
            args.prompt
        )

        if (
            not
            prompt_path.is_absolute()
        ):

            prompt_path = (
                PROJECT_ROOT
                / prompt_path
            )

    else:

        prompt_path = (
            PROMPTS_DIR
            / f"{args.task}.txt"
        )

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
        f"Developer : "
        f"{MODEL_DEVELOPER}"
    )

    print(
        f"Provider  : "
        f"{API_PROVIDER}"
    )

    print(
        f"Modelo    : "
        f"{MODEL}"
    )

    print(
        f"Tarefa    : "
        f"{args.task}"
    )

    print(
        f"Prompt    : "
        f"{prompt_path}"
    )

    print(
        "----------------------------------------"
    )

    print(
        "Enviando prompt..."
    )

    # ========================================================
    # API
    # ========================================================

    try:

        (
            response_text,
            usage,
            latency,
            first_content_latency,
            response_id,
            returned_model,

        ) = run_deepseek(
            prompt
        )

    except Exception as error:

        print()

        print(
            "ERRO durante a chamada "
            "da API:"
        )

        print(error)

        sys.exit(1)

    # ========================================================
    # RESPOSTA VAZIA
    # ========================================================

    if (
        not
        response_text.strip()
    ):

        print()

        print(
            "ERRO: a API retornou "
            "uma resposta vazia."
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

            prompt_path=(
                prompt_path
            ),

            response_text=(
                response_text
            ),

            usage=usage,

            latency=latency,

            first_content_latency=(
                first_content_latency
            ),

            response_id=(
                response_id
            ),

            returned_model=(
                returned_model
            ),
        )

    except Exception as error:

        print()

        print(
            "ERRO ao salvar "
            "os resultados:"
        )

        print(error)

        sys.exit(1)

    # ========================================================
    # RESULTADO NO TERMINAL
    # ========================================================

    tokens = (
        metadata["tokens"]
    )

    print()

    print(
        "Resposta recebida "
        "com sucesso."
    )

    print()

    print(
        "Latência total: "
        f"{metadata['latency_seconds']} s"
    )

    print(
        "Latência até primeiro conteúdo: "
        f"{metadata['first_content_latency_seconds']} s"
    )

    print()

    print(
        "Tokens de entrada    : "
        f"{tokens['input']}"
    )

    print(
        "Tokens de saída      : "
        f"{tokens['output']}"
    )

    print(
        "Tokens de reasoning  : "
        f"{tokens['reasoning']}"
    )

    print(
        "Tokens em cache      : "
        f"{tokens['cached']}"
    )

    print(
        "Tokens totais        : "
        f"{tokens['total']}"
    )

    print()

    print(
        "Custo informado pela API: "
        f"{metadata['cost']}"
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
