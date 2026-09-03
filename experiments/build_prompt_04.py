import argparse
import sys
from pathlib import Path


# ============================================================
# LOCALIZAÇÃO DA RAIZ DO PROJETO
# ============================================================

def find_project_root() -> Path:
    """
    Procura automaticamente a raiz do projeto.

    A raiz deve conter:
    - prompts/
    - results/
    """

    current = Path(__file__).resolve().parent

    for directory in [current, *current.parents]:
        has_prompts = (directory / "prompts").is_dir()
        has_results = (directory / "results").is_dir()

        if has_prompts and has_results:
            return directory

    raise RuntimeError(
        "Não foi possível localizar a raiz do projeto. "
        "Verifique se as pastas prompts/ e results/ existem."
    )


PROJECT_ROOT = find_project_root()

PROMPTS_DIR = PROJECT_ROOT / "prompts"
RESULTS_DIR = PROJECT_ROOT / "results"

PROMPT_04_TEMPLATE = PROMPTS_DIR / "04_integrated.txt"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def read_file(path: Path) -> str:
    """
    Lê um arquivo de texto.

    Encerra o programa caso o arquivo não exista.
    """

    if not path.exists():
        print()
        print("ERRO: arquivo não encontrado:")
        print(path)
        sys.exit(1)

    return path.read_text(
        encoding="utf-8"
    )


def check_placeholder(
    prompt: str,
    placeholder: str
):
    """
    Verifica se um placeholder existe no template.
    """

    if placeholder not in prompt:
        print()
        print(
            "ERRO: placeholder não encontrado no prompt:"
        )
        print(placeholder)
        sys.exit(1)


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # ARGUMENTOS
    # --------------------------------------------------------

    parser = argparse.ArgumentParser(
        description=(
            "Monta o prompt 04_integrated usando os códigos "
            "01_bme280, 02_lora e 03_mc38 gerados por uma LLM."
        )
    )

    parser.add_argument(
        "model",
        help=(
            "Nome da pasta do modelo dentro de results/. "
            "Exemplo: laguna-s-2.1-free"
        ),
    )

    args = parser.parse_args()

    model_result_dir = args.model

    # --------------------------------------------------------
    # CAMINHOS DOS RESULTADOS
    # --------------------------------------------------------

    model_dir = (
        RESULTS_DIR
        / model_result_dir
    )

    bme280_path = (
        model_dir
        / "01_bme280"
        / "code.ino"
    )

    lora_path = (
        model_dir
        / "02_lora"
        / "code.ino"
    )

    mc38_path = (
        model_dir
        / "03_mc38"
        / "code.ino"
    )

    output_dir = (
        model_dir
        / "04_integrated"
    )

    output_prompt = (
        output_dir
        / "prompt_generated.txt"
    )

    # --------------------------------------------------------
    # VERIFICA SE A PASTA DO MODELO EXISTE
    # --------------------------------------------------------

    if not model_dir.exists():
        print()
        print(
            "ERRO: pasta do modelo não encontrada:"
        )
        print(model_dir)
        sys.exit(1)

    # --------------------------------------------------------
    # LÊ OS TRÊS CÓDIGOS
    # --------------------------------------------------------

    bme280_code = read_file(
        bme280_path
    )

    lora_code = read_file(
        lora_path
    )

    mc38_code = read_file(
        mc38_path
    )

    # --------------------------------------------------------
    # LÊ O TEMPLATE DO PROMPT 04
    # --------------------------------------------------------

    prompt_template = read_file(
        PROMPT_04_TEMPLATE
    )

    # --------------------------------------------------------
    # VERIFICA OS PLACEHOLDERS
    # --------------------------------------------------------

    check_placeholder(
        prompt_template,
        "{{CODIGO_BME280}}"
    )

    check_placeholder(
        prompt_template,
        "{{CODIGO_LORA}}"
    )

    check_placeholder(
        prompt_template,
        "{{CODIGO_MC38}}"
    )

    # --------------------------------------------------------
    # SUBSTITUI OS CÓDIGOS
    # --------------------------------------------------------

    final_prompt = prompt_template.replace(
        "{{CODIGO_BME280}}",
        bme280_code
    )

    final_prompt = final_prompt.replace(
        "{{CODIGO_LORA}}",
        lora_code
    )

    final_prompt = final_prompt.replace(
        "{{CODIGO_MC38}}",
        mc38_code
    )

    # --------------------------------------------------------
    # VERIFICA SE ALGUM PLACEHOLDER RESTOU
    # --------------------------------------------------------

    remaining_placeholders = [
        "{{CODIGO_BME280}}",
        "{{CODIGO_LORA}}",
        "{{CODIGO_MC38}}",
    ]

    for placeholder in remaining_placeholders:
        if placeholder in final_prompt:
            print()
            print(
                "ERRO: placeholder ainda presente "
                "após a substituição:"
            )
            print(placeholder)
            sys.exit(1)

    # --------------------------------------------------------
    # CRIA A PASTA DE SAÍDA
    # --------------------------------------------------------

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # SALVA O PROMPT GERADO
    # --------------------------------------------------------

    output_prompt.write_text(
        final_prompt,
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    print()
    print(
        "----------------------------------------"
    )

    print(
        "Prompt 04 criado com sucesso"
    )

    print(
        "----------------------------------------"
    )

    print(
        f"Modelo : {model_result_dir}"
    )

    print()

    print(
        "Arquivos utilizados:"
    )

    print(
        f"BME280 : {bme280_path}"
    )

    print(
        f"LoRa   : {lora_path}"
    )

    print(
        f"MC-38  : {mc38_path}"
    )

    print()

    print(
        "Prompt gerado:"
    )

    print(
        output_prompt
    )

    print()

    print(
        f"Tamanho do prompt: "
        f"{len(final_prompt)} caracteres"
    )

    print()


if __name__ == "__main__":
    main()