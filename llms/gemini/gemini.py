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
from google import genai
from google.genai import types


# ============================================================
# CONFIGURAÇÃO DO MODELO
# ============================================================

PROVIDER = "Google"
MODEL = "gemini-3.8-flash"

THINKING_LEVEL = "medium"
MAX_OUTPUT_TOKENS = 16384


# ============================================================
# LOCALIZAÇÃO DA RAIZ DO PROJETO
# ============================================================

def find_project_root() -> Path:
    """
    Procura automaticamente a raiz do projeto.

    Espera encontrar uma pasta 'prompts' e um dos seguintes:
    - .env
    - .git
    - requirements.txt

    Isso permite manter este arquivo em:
    llms/gemini/gemini.py
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
        "Não foi possível localizar a raiz do projeto. "
        "Verifique se a pasta prompts/ existe na raiz."
    )


PROJECT_ROOT = find_project_root()

ENV_FILE = PROJECT_ROOT / ".env"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
RESULTS_DIR = PROJECT_ROOT / "results"


# ============================================================
# CONFIGURAÇÃO DE GERAÇÃO
# ============================================================

GENERATION_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(
        thinking_level=THINKING_LEVEL
    ),
    max_output_tokens=MAX_OUTPUT_TOKENS,
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def sha256_text(text: str) -> str:
    """
    Gera o SHA-256 do texto.

    Serve para verificar posteriormente se prompt,
    resposta ou código foram modificados.
    """

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def read_prompt(prompt_path: Path) -> str:
    """
    Lê o arquivo do prompt.
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
    Extrai o código da resposta.

    Se a LLM ignorar o prompt e responder usando:

    ```cpp
    código
    ```

    as marcações Markdown são removidas apenas do code.ino.

    response.txt continua contendo a resposta original.
    """

    response = response.strip()

    pattern = r"```(?:cpp|c\+\+|arduino|ino)?\s*(.*?)```"

    match = re.search(
        pattern,
        response,
        flags=re.IGNORECASE | re.DOTALL
    )

    if match:
        return match.group(1).strip()

    return response


def get_usage_value(usage, *fields):
    """
    Obtém uma informação de uso retornada pela API.

    Alguns campos podem variar entre versões do SDK,
    então podemos fornecer mais de um nome possível.
    """

    if usage is None:
        return None

    for field in fields:
        value = getattr(
            usage,
            field,
            None
        )

        if value is not None:
            return value

    return None


# ============================================================
# CHAMADA DA API GEMINI
# ============================================================

def run_gemini(prompt: str):
    """
    Envia o prompt usando streaming.

    Retorna:

    - resposta completa;
    - dados de uso/tokens;
    - latência total;
    - latência até o primeiro trecho da resposta;
    - ID da resposta, quando fornecido pela API.
    """

    load_dotenv(ENV_FILE)

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        print()
        print(
            "ERRO: GEMINI_API_KEY "
            "não encontrada."
        )
        print()
        print(
            f"Verifique o arquivo: {ENV_FILE}"
        )
        sys.exit(1)

    client = genai.Client(
        api_key=api_key
    )

    response_parts = []

    usage = None
    response_id = None

    first_chunk_time = None

    start_time = time.perf_counter()

    try:
        stream = client.models.generate_content_stream(
            model=MODEL,
            contents=prompt,
            config=GENERATION_CONFIG,
        )

        for chunk in stream:

            # --------------------------------------------
            # TEXTO
            # --------------------------------------------

            try:
                text = chunk.text
            except Exception:
                text = None

            if text:

                if first_chunk_time is None:
                    first_chunk_time = (
                        time.perf_counter()
                    )

                response_parts.append(text)

            # --------------------------------------------
            # TOKENS
            # --------------------------------------------

            chunk_usage = getattr(
                chunk,
                "usage_metadata",
                None
            )

            if chunk_usage is not None:
                usage = chunk_usage

            # --------------------------------------------
            # ID DA RESPOSTA
            # --------------------------------------------

            chunk_response_id = getattr(
                chunk,
                "response_id",
                None
            )

            if chunk_response_id:
                response_id = (
                    chunk_response_id
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

    if first_chunk_time is not None:
        first_chunk_latency = (
            first_chunk_time - start_time
        )
    else:
        first_chunk_latency = None

    return (
        response_text,
        usage,
        total_latency,
        first_chunk_latency,
        response_id,
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
    first_chunk_latency,
    response_id,
):
    """
    Salva todos os arquivos da execução.
    """

    result_dir = (
        RESULTS_DIR
        / MODEL
        / task
    )

    result_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    code = extract_code(
        response_text
    )

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

    # ========================================================
    # SALVA O PROMPT EXATO
    # ========================================================

    prompt_output.write_text(
        prompt,
        encoding="utf-8"
    )

    # ========================================================
    # SALVA A RESPOSTA BRUTA
    # ========================================================

    response_output.write_text(
        response_text,
        encoding="utf-8"
    )

    # ========================================================
    # SALVA O CÓDIGO EXTRAÍDO
    # ========================================================

    code_output.write_text(
        code,
        encoding="utf-8"
    )

    # ========================================================
    # TOKENS
    # ========================================================

    input_tokens = get_usage_value(
        usage,
        "prompt_token_count"
    )

    output_tokens = get_usage_value(
        usage,
        "candidates_token_count",
        "response_token_count"
    )

    thought_tokens = get_usage_value(
        usage,
        "thoughts_token_count"
    )

    cached_tokens = get_usage_value(
        usage,
        "cached_content_token_count"
    )

    tool_tokens = get_usage_value(
        usage,
        "tool_use_prompt_token_count"
    )

    total_tokens = get_usage_value(
        usage,
        "total_token_count"
    )

    # ========================================================
    # METADADOS
    # ========================================================

    metadata = {

        "provider": PROVIDER,

        "model": MODEL,

        "task": task,

        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "prompt_file": str(
            prompt_path.relative_to(
                PROJECT_ROOT
            )
        ),

        "response_id": response_id,

        # ----------------------------------------------------
        # LATÊNCIA
        # ----------------------------------------------------

        "latency_seconds": round(
            latency,
            6
        ),

        "first_chunk_latency_seconds": (
            round(
                first_chunk_latency,
                6
            )
            if first_chunk_latency
            is not None
            else None
        ),

        # ----------------------------------------------------
        # TOKENS
        # ----------------------------------------------------

        "tokens": {

            "input": input_tokens,

            "output": output_tokens,

            "thought": thought_tokens,

            "cached": cached_tokens,

            "tool_use": tool_tokens,

            "total": total_tokens,
        },

        # ----------------------------------------------------
        # CONFIGURAÇÃO DO EXPERIMENTO
        # ----------------------------------------------------

        "generation_config": {

            "thinking_level":
                THINKING_LEVEL,

            "max_output_tokens":
                MAX_OUTPUT_TOKENS,
        },

        # ----------------------------------------------------
        # INTEGRIDADE
        # ----------------------------------------------------

        "integrity": {

            "prompt_sha256":
                sha256_text(prompt),

            "response_sha256":
                sha256_text(response_text),

            "code_sha256":
                sha256_text(code),
        },

        # ----------------------------------------------------
        # TAMANHO
        # ----------------------------------------------------

        "response_characters":
            len(response_text),

        "code_characters":
            len(code),
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
            "utilizando Gemini."
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
            "Se omitido, será utilizado "
            "prompts/<task>.txt"
        ),
    )

    args = parser.parse_args()

    # ========================================================
    # LOCALIZAÇÃO DO PROMPT
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
    # INFORMAÇÕES DA EXECUÇÃO
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
        f"Provider : {PROVIDER}"
    )

    print(
        f"Modelo   : {MODEL}"
    )

    print(
        f"Tarefa   : {args.task}"
    )

    print(
        f"Prompt   : {prompt_path}"
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
            first_chunk_latency,
            response_id,

        ) = run_gemini(
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
    # SALVA RESULTADOS
    # ========================================================

    try:

        result_dir, metadata = (
            save_result(
                task=args.task,
                prompt=prompt,
                prompt_path=prompt_path,
                response_text=response_text,
                usage=usage,
                latency=latency,
                first_chunk_latency=(
                    first_chunk_latency
                ),
                response_id=response_id,
            )
        )

    except Exception as error:

        print()
        print(
            "ERRO ao salvar os resultados:"
        )

        print(error)

        sys.exit(1)

    # ========================================================
    # RESULTADO NO TERMINAL
    # ========================================================

    tokens = metadata["tokens"]

    print()
    print(
        "Resposta recebida com sucesso."
    )

    print()

    print(
        f"Latência total: "
        f"{metadata['latency_seconds']} s"
    )

    print(
        "Latência até primeiro trecho: "
        f"{metadata['first_chunk_latency_seconds']} s"
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
        "Tokens de pensamento : "
        f"{tokens['thought']}"
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
