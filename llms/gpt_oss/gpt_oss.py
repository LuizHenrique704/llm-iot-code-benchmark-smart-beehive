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
from groq import Groq


# ============================================================
# CONFIGURAÇÃO DO MODELO
# ============================================================

MODEL_DEVELOPER = "OpenAI"
API_PROVIDER = "Groq"

MODEL = "openai/gpt-oss-120b"

# Nome utilizado dentro de results/
RESULT_MODEL_NAME = "gpt-oss-120b"

# Limite máximo que permitimos para uma resposta.
MAX_OUTPUT_TOKENS = 16384
TEMPERATURE = 0.0

# GPT-OSS suporta:
# low
# medium
# high
REASONING_EFFORT = "medium"


# ============================================================
# LOCALIZAÇÃO DA RAIZ DO PROJETO
# ============================================================

def find_project_root() -> Path:
    """
    Localiza automaticamente a raiz do projeto.

    Permite que este arquivo fique em:

    llms/gpt_oss/gpt_oss.py
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

        if has_prompts and has_project_marker:
            return directory

    raise RuntimeError(
        "Não foi possível localizar a raiz do projeto. "
        "Verifique se a pasta prompts/ existe na raiz."
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


def read_prompt(prompt_path: Path) -> str:
    """
    Lê um prompt.
    """

    if not prompt_path.exists():

        print()
        print("ERRO: prompt não encontrado:")
        print(prompt_path)

        sys.exit(1)

    return prompt_path.read_text(
        encoding="utf-8"
    )


def extract_code(response: str) -> str:
    """
    Extrai o código caso a LLM responda usando:

    ```cpp
    ...
    ```

    response.txt permanece intacto.
    code.ino recebe somente o código.
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
    Converte objetos do SDK para dict.
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
    Obtém um campo dentro de dicionários aninhados.
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


def relative_path(path: Path) -> str:
    """
    Tenta apresentar o caminho relativo à raiz.
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
# CHAMADA DA API GROQ
# ============================================================

def run_gpt_oss(prompt: str):
    """
    Executa GPT-OSS 120B via Groq usando streaming.

    Retorna:

    - resposta completa;
    - usage;
    - latência total medida localmente;
    - latência até o primeiro conteúdo;
    - ID da resposta;
    - ID interno da requisição Groq;
    - modelo efetivamente retornado;
    - system fingerprint.
    """

    load_dotenv(
        ENV_FILE
    )

    api_key = os.getenv(
        "GROQ_API_KEY"
    )

    if not api_key:

        print()
        print(
            "ERRO: GROQ_API_KEY não encontrada."
        )

        print()
        print(
            f"Verifique o arquivo: {ENV_FILE}"
        )

        sys.exit(1)

    client = Groq(
        api_key=api_key
    )

    response_parts = []

    usage = None

    response_id = None

    request_id = None

    returned_model = None

    system_fingerprint = None

    first_content_time = None

    start_time = (
        time.perf_counter()
    )

    try:

        stream = (
            client
            .chat
            .completions
            .create(
                model=MODEL,

                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],

                max_completion_tokens=(
                    MAX_OUTPUT_TOKENS
                ),

                temperature=(
                    TEMPERATURE
                ),

                reasoning_effort=(
                    REASONING_EFFORT
                ),

                # Não queremos armazenar o raciocínio
                # textual interno do modelo.
                reasoning_format="hidden",

                stream=True,
            )
        )

        for chunk in stream:

            # =================================================
            # ID DA RESPOSTA
            # =================================================

            chunk_id = getattr(
                chunk,
                "id",
                None
            )

            if chunk_id:
                response_id = chunk_id

            # =================================================
            # MODELO RETORNADO
            # =================================================

            chunk_model = getattr(
                chunk,
                "model",
                None
            )

            if chunk_model:
                returned_model = (
                    chunk_model
                )

            # =================================================
            # SYSTEM FINGERPRINT
            # =================================================

            chunk_fingerprint = getattr(
                chunk,
                "system_fingerprint",
                None
            )

            if chunk_fingerprint:

                system_fingerprint = (
                    chunk_fingerprint
                )

            # =================================================
            # USAGE DIRETO
            # =================================================

            chunk_usage = getattr(
                chunk,
                "usage",
                None
            )

            if chunk_usage is not None:
                usage = chunk_usage

            # =================================================
            # METADADOS ESPECÍFICOS DA GROQ
            # =================================================

            x_groq = getattr(
                chunk,
                "x_groq",
                None
            )

            if x_groq is not None:

                groq_id = getattr(
                    x_groq,
                    "id",
                    None
                )

                if groq_id:
                    request_id = groq_id

                groq_usage = getattr(
                    x_groq,
                    "usage",
                    None
                )

                if groq_usage is not None:
                    usage = groq_usage

            # =================================================
            # CONTEÚDO
            # =================================================

            choices = getattr(
                chunk,
                "choices",
                None
            )

            # O último chunk pode conter apenas usage.
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

            # Primeiro pedaço de conteúdo recebido.
            if first_content_time is None:

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
    # RESPOSTA COMPLETA
    # ========================================================

    response_text = "".join(
        response_parts
    )

    total_latency = (
        end_time
        - start_time
    )

    # ========================================================
    # LATÊNCIA ATÉ PRIMEIRO CONTEÚDO
    # ========================================================

    if first_content_time is not None:

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
        request_id,
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
    request_id,
    returned_model,
    system_fingerprint,
):
    """
    Salva os arquivos produzidos pelo experimento.
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
    # EXTRAI O CÓDIGO
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
    # PROMPT
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

    usage_data = object_to_dict(
        usage
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
    # TEMPOS INTERNOS DA GROQ
    # ========================================================

    queue_time = usage_data.get(
        "queue_time"
    )

    prompt_time = usage_data.get(
        "prompt_time"
    )

    completion_time = usage_data.get(
        "completion_time"
    )

    server_total_time = usage_data.get(
        "total_time"
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

        "groq_request_id":
            request_id,

        "system_fingerprint":
            system_fingerprint,

        # ----------------------------------------------------
        # LATÊNCIA MEDIDA NO COMPUTADOR
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
        # TEMPOS INFORMADOS PELA GROQ
        # ----------------------------------------------------

        "provider_timing": {

            "queue_time_seconds":
                queue_time,

            "prompt_time_seconds":
                prompt_time,

            "completion_time_seconds":
                completion_time,

            "total_time_seconds":
                server_total_time,
        },

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
        # CONFIGURAÇÃO DA GERAÇÃO
        # ----------------------------------------------------

        "generation_config": {

            "max_output_tokens":
                MAX_OUTPUT_TOKENS,

            "temperature":
                TEMPERATURE,

            "reasoning_effort":
                REASONING_EFFORT,

            "reasoning_format":
                "hidden",

            "stream":
                True,
        },

        # ----------------------------------------------------
        # USAGE COMPLETO RETORNADO PELA GROQ
        # ----------------------------------------------------

        "raw_usage":
            usage_data,

        # ----------------------------------------------------
        # HASHES
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

    parser = argparse.ArgumentParser(
        description=(
            "Executa um prompt do benchmark "
            "utilizando GPT-OSS 120B via Groq."
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
    # LOCALIZAÇÃO DO PROMPT
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
        f"Developer : {MODEL_DEVELOPER}"
    )

    print(
        f"Provider  : {API_PROVIDER}"
    )

    print(
        f"Modelo    : {MODEL}"
    )

    print(
        f"Tarefa    : {args.task}"
    )

    print(
        f"Prompt    : {prompt_path}"
    )

    print(
        "----------------------------------------"
    )

    print(
        "Enviando prompt..."
    )

    # ========================================================
    # CHAMADA DA API
    # ========================================================

    try:

        (
            response_text,
            usage,
            latency,
            first_content_latency,
            response_id,
            request_id,
            returned_model,
            system_fingerprint,

        ) = run_gpt_oss(
            prompt
        )

    except Exception as error:

        print()

        print(
            "ERRO durante a chamada da API:"
        )

        print(error)

        sys.exit(1)

    # ========================================================
    # VERIFICA RESPOSTA
    # ========================================================

    if not response_text.strip():

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

            prompt_path=prompt_path,

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

            request_id=(
                request_id
            ),

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
            "ERRO ao salvar os resultados:"
        )

        print(error)

        sys.exit(1)

    # ========================================================
    # RESULTADOS NO TERMINAL
    # ========================================================

    tokens = metadata[
        "tokens"
    ]

    provider_timing = metadata[
        "provider_timing"
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
        "Tempo interno Groq:"
    )

    print(
        "  Fila       : "
        f"{provider_timing['queue_time_seconds']} s"
    )

    print(
        "  Prompt     : "
        f"{provider_timing['prompt_time_seconds']} s"
    )

    print(
        "  Geração    : "
        f"{provider_timing['completion_time_seconds']} s"
    )

    print(
        "  Total API  : "
        f"{provider_timing['total_time_seconds']} s"
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
