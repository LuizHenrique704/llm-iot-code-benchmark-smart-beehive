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

RESULT_MODEL_NAME = "glm-4.7-flash"

MAX_OUTPUT_TOKENS = 16384

# Vamos posteriormente padronizar os outros modelos também.
TEMPERATURE = 0.0

REASONING_EFFORT = "medium"


# ============================================================
# LOCALIZAÇÃO DA RAIZ DO PROJETO
# ============================================================

def find_project_root() -> Path:
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
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def read_prompt(path: Path) -> str:
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
    Extrai código caso a resposta venha dentro de Markdown.

    response.txt permanece com a resposta original.
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
        return match.group(1).strip()

    return response


def relative_path(path: Path) -> str:
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
    Executa GLM-4.7-Flash diretamente pela REST API
    da Cloudflare usando streaming SSE.

    O reasoning do modelo é ignorado.
    Apenas message.content é armazenado.
    """

    load_dotenv(ENV_FILE)

    account_id = os.getenv(
        "CLOUDFLARE_ACCOUNT_ID"
    )

    api_token = os.getenv(
        "CLOUDFLARE_API_TOKEN"
    )

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
        "Accept": "text/event-stream",
    }

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
            True,
    }

    # ========================================================
    # VARIÁVEIS
    # ========================================================

    response_parts = []

    usage = {}

    response_id = None
    returned_model = None
    system_fingerprint = None

    first_content_time = None

    start_time = time.perf_counter()

    print(
        "Aguardando conexão com a Cloudflare...",
        flush=True
    )

    # ========================================================
    # REQUISIÇÃO
    # ========================================================

    try:

        with requests.post(
            url,
            headers=headers,
            json=payload,
            stream=True,

            # 30 s para conectar
            # 300 s esperando entre dados recebidos
            timeout=(30, 300),

        ) as response:

            # =================================================
            # ERRO HTTP
            # =================================================

            if not response.ok:

                raise RuntimeError(
                    f"HTTP {response.status_code}: "
                    f"{response.text}"
                )

            print(
                f"Conexão estabelecida "
                f"(HTTP {response.status_code}).",
                flush=True
            )

            print(
                "Gerando resposta...",
                flush=True
            )

            # =================================================
            # LEITURA DO STREAM SSE
            # =================================================

            for raw_line in response.iter_lines(
                chunk_size=1,
                decode_unicode=True,
            ):

                if not raw_line:
                    continue

                line = raw_line.strip()

                # SSE:
                #
                # data: {...}
                # data: [DONE]

                if not line.startswith("data:"):
                    continue

                event_data = (
                    line[len("data:"):]
                    .strip()
                )

                # =================================================
                # FIM DO STREAM
                # =================================================

                if event_data == "[DONE]":

                    print()
                    print(
                        "Streaming finalizado.",
                        flush=True
                    )

                    break

                # =================================================
                # JSON
                # =================================================

                try:

                    chunk = json.loads(
                        event_data
                    )

                except json.JSONDecodeError:

                    continue

                # Algumas respostas podem vir encapsuladas.
                if (
                    isinstance(chunk, dict)
                    and "result" in chunk
                    and isinstance(
                        chunk["result"],
                        dict
                    )
                ):
                    chunk = chunk["result"]

                if not isinstance(
                    chunk,
                    dict
                ):
                    continue

                # =================================================
                # ID
                # =================================================

                chunk_id = chunk.get(
                    "id"
                )

                if chunk_id:
                    response_id = chunk_id

                # =================================================
                # MODELO
                # =================================================

                chunk_model = chunk.get(
                    "model"
                )

                if chunk_model:
                    returned_model = (
                        chunk_model
                    )

                # =================================================
                # SYSTEM FINGERPRINT
                # =================================================

                fingerprint = chunk.get(
                    "system_fingerprint"
                )

                if fingerprint is not None:
                    system_fingerprint = (
                        fingerprint
                    )

                # =================================================
                # USAGE
                # =================================================

                chunk_usage = chunk.get(
                    "usage"
                )

                if isinstance(
                    chunk_usage,
                    dict
                ):
                    usage = chunk_usage

                # =================================================
                # CHOICES
                # =================================================

                choices = chunk.get(
                    "choices",
                    []
                )

                if not choices:
                    continue

                first_choice = choices[0]

                if not isinstance(
                    first_choice,
                    dict
                ):
                    continue

                delta = first_choice.get(
                    "delta",
                    {}
                )

                if not isinstance(
                    delta,
                    dict
                ):
                    continue

                # =================================================
                # CONTEÚDO
                #
                # Não armazenamos:
                # - reasoning
                # - reasoning_content
                # =================================================

                content = delta.get(
                    "content"
                )

                if not content:
                    continue

                # =================================================
                # PRIMEIRO CONTEÚDO
                # =================================================

                if first_content_time is None:

                    first_content_time = (
                        time.perf_counter()
                    )

                    print(
                        "Primeiro conteúdo recebido.",
                        flush=True
                    )

                    print(
                        "Recebendo resposta: ",
                        end="",
                        flush=True
                    )

                # Apenas indicador visual.
                # Não entra no resultado salvo.
                print(
                    ".",
                    end="",
                    flush=True
                )

                response_parts.append(
                    content
                )

    # ========================================================
    # ERROS DE REDE
    # ========================================================

    except requests.exceptions.ConnectTimeout as error:

        raise RuntimeError(
            "Timeout ao conectar com a Cloudflare."
        ) from error

    except requests.exceptions.ReadTimeout as error:

        raise RuntimeError(
            "Timeout aguardando dados da Cloudflare."
        ) from error

    except requests.exceptions.ChunkedEncodingError as error:

        raise RuntimeError(
            "A Cloudflare encerrou o streaming "
            "antes de completar a resposta."
        ) from error

    except requests.exceptions.ConnectionError as error:

        raise RuntimeError(
            "A conexão com a Cloudflare foi encerrada."
        ) from error

    # ========================================================
    # TEMPO FINAL
    # ========================================================

    end_time = time.perf_counter()

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
    # PROMPT
    # ========================================================

    prompt_output.write_text(
        prompt,
        encoding="utf-8"
    )

    # ========================================================
    # RESPOSTA
    # ========================================================

    response_output.write_text(
        response_text,
        encoding="utf-8"
    )

    # ========================================================
    # CÓDIGO
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

    prompt_details = (
        usage.get(
            "prompt_tokens_details",
            {}
        )
        or {}
    )

    cached_tokens = (
        prompt_details.get(
            "cached_tokens"
        )
    )

    # Cloudflare não necessariamente fornece
    # reasoning_tokens separadamente.
    reasoning_tokens = None

    # ========================================================
    # NEURONS
    # ========================================================

    neurons = usage.get(
        "neurons"
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
        # CLOUDFLARE
        # ----------------------------------------------------

        "neurons":
            neurons,

        # ----------------------------------------------------
        # CONFIGURAÇÃO
        # ----------------------------------------------------

        "generation_config": {

            "max_output_tokens":
                MAX_OUTPUT_TOKENS,

            "temperature":
                TEMPERATURE,

            "reasoning_effort":
                REASONING_EFFORT,

            "stream":
                True,
        },

        # ----------------------------------------------------
        # USAGE BRUTO
        # ----------------------------------------------------

        "raw_usage":
            usage,

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
        "Enviando prompt...",
        flush=True
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
        sys.exit(1)

    # ========================================================
    # RESPOSTA VAZIA
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