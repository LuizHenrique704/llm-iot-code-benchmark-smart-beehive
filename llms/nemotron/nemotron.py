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

MODEL_DEVELOPER = "NVIDIA"
API_PROVIDER = "OpenRouter"
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
RESULT_MODEL_NAME = "nemotron-3-ultra-550b-a55b-free"

MAX_OUTPUT_TOKENS = 16384
TEMPERATURE = 0.0

# ============================================================
# LOCALIZAÇÃO DA RAIZ DO PROJETO
# ============================================================

def find_project_root() -> Path:
    """
    Localiza automaticamente a raiz do projeto.

    Esperado:
    projeto/
    ├── .env
    ├── prompts/
    ├── results/
    └── llms/
        └── llama/
            └── llama.py
    """

    current = Path(__file__).resolve().parent

    for directory in [current, *current.parents]:

        has_prompts = (directory / "prompts").is_dir()

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
    Calcula SHA-256 de um texto.
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
    Extrai código de uma resposta Markdown.

    response.txt permanece bruto.
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
        flags=re.IGNORECASE | re.DOTALL,
    )

    if match:
        return match.group(1).strip()

    return response


def object_to_dict(obj):
    """
    Converte objetos do SDK OpenAI para dicionário.
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


def get_nested_value(data, *keys):
    """
    Obtém valor de dicionários aninhados.
    """

    current = data

    for key in keys:

        if not isinstance(current, dict):
            return None

        current = current.get(key)

        if current is None:
            return None

    return current


def relative_path(path: Path) -> str:
    """
    Retorna caminho relativo à raiz do projeto.
    """

    try:
        return str(
            path.relative_to(PROJECT_ROOT)
        )

    except ValueError:
        return str(path)


# ============================================================
# EXECUÇÃO DO LLAMA
# ============================================================

def run_llama(prompt: str):
    """
    Executa o Llama 3.3 70B via OpenRouter.

    Usa streaming para permitir medir:
    - latência total;
    - latência até o primeiro conteúdo.
    """

    load_dotenv(ENV_FILE)

    api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )

    if not api_key:
        print()
        print(
            "ERRO: OPENROUTER_API_KEY "
            "não encontrada no .env"
        )
        sys.exit(1)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    response_parts = []

    usage = None

    response_id = None
    returned_model = None
    system_fingerprint = None

    first_content_time = None

    start_time = time.perf_counter()

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

            stream_options={
                "include_usage": True
            },
        )

        for chunk in stream:

            # ------------------------------------------------
            # ID DA RESPOSTA
            # ------------------------------------------------

            chunk_id = getattr(
                chunk,
                "id",
                None
            )

            if chunk_id:
                response_id = chunk_id

            # ------------------------------------------------
            # MODELO RETORNADO
            # ------------------------------------------------

            chunk_model = getattr(
                chunk,
                "model",
                None
            )

            if chunk_model:
                returned_model = chunk_model

            # ------------------------------------------------
            # SYSTEM FINGERPRINT
            # ------------------------------------------------

            fingerprint = getattr(
                chunk,
                "system_fingerprint",
                None
            )

            if fingerprint:
                system_fingerprint = fingerprint

            # ------------------------------------------------
            # USAGE
            # ------------------------------------------------

            chunk_usage = getattr(
                chunk,
                "usage",
                None
            )

            if chunk_usage is not None:
                usage = chunk_usage

            # ------------------------------------------------
            # CONTEÚDO
            # ------------------------------------------------

            choices = getattr(
                chunk,
                "choices",
                None
            )

            # Último chunk pode conter apenas usage.
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

            if first_content_time is None:
                first_content_time = (
                    time.perf_counter()
                )

            response_parts.append(
                content
            )

        end_time = time.perf_counter()

    finally:

        client.close()

    response_text = "".join(
        response_parts
    )

    total_latency = (
        end_time - start_time
    )

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
    - prompt.txt
    - response.txt
    - code.ino
    - metadata.json
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

    code = extract_code(
        response_text
    )

    # --------------------------------------------------------
    # ARQUIVOS
    # --------------------------------------------------------

    prompt_output = (
        result_dir / "prompt.txt"
    )

    response_output = (
        result_dir / "response.txt"
    )

    code_output = (
        result_dir / "code.ino"
    )

    metadata_output = (
        result_dir / "metadata.json"
    )

    # --------------------------------------------------------
    # SALVA PROMPT
    # --------------------------------------------------------

    prompt_output.write_text(
        prompt,
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # SALVA RESPOSTA BRUTA
    # --------------------------------------------------------

    response_output.write_text(
        response_text,
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # SALVA CÓDIGO EXTRAÍDO
    # --------------------------------------------------------

    code_output.write_text(
        code,
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # USAGE
    # --------------------------------------------------------

    usage_data = object_to_dict(
        usage
    )

    input_tokens = usage_data.get(
        "prompt_tokens"
    )

    output_tokens = usage_data.get(
        "completion_tokens"
    )

    total_tokens = usage_data.get(
        "total_tokens"
    )

    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    cached_tokens = get_nested_value(
        usage_data,
        "prompt_tokens_details",
        "cached_tokens",
    )

    # --------------------------------------------------------
    # REASONING
    #
    # Normalmente será None/0 no Llama 3.3,
    # mas mantemos o campo para padronização
    # do benchmark.
    # --------------------------------------------------------

    reasoning_tokens = get_nested_value(
        usage_data,
        "completion_tokens_details",
        "reasoning_tokens",
    )

    # --------------------------------------------------------
    # CUSTO INFORMADO PELO OPENROUTER
    #
    # No modelo :free deve ser 0 quando
    # disponibilizado pelo endpoint.
    # --------------------------------------------------------

    cost = usage_data.get(
        "cost"
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
                if first_content_latency is not None
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
        # CUSTO
        # ----------------------------------------------------

        "cost":
            cost,

        # ----------------------------------------------------
        # CONFIGURAÇÃO
        # ----------------------------------------------------

        "generation_config": {

            "max_output_tokens":
                MAX_OUTPUT_TOKENS,

            "temperature":
                TEMPERATURE,

            "stream":
                True,
        },

        # ----------------------------------------------------
        # USAGE COMPLETO
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
            "Executa prompts do benchmark "
            "utilizando Llama 3.3 70B "
            "via OpenRouter."
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
    # PROMPT
    # ========================================================

    if args.prompt:

        prompt_path = args.prompt

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
            system_fingerprint,

        ) = run_llama(
            prompt
        )

    except Exception as error:

        print()

        print(
            "ERRO durante a chamada da API:"
        )

        print(error)

        # Sem retry automático.
        # Um erro da infraestrutura não deve
        # gerar uma segunda execução silenciosa.

        sys.exit(1)

    # ========================================================
    # VALIDA RESPOSTA
    # ========================================================

    if not response_text.strip():

        print()

        print(
            "ERRO: a API retornou "
            "uma resposta vazia."
        )

        sys.exit(1)

    # ========================================================
    # SALVA RESULTADOS
    # ========================================================

    try:

        result_dir, metadata = save_result(

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
    # RESULTADO NO TERMINAL
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
        f"{metadata['first_content_latency_seconds']} s"
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

    print()

    print(
        "Custo informado pelo OpenRouter: "
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
