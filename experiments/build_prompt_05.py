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

PROMPT_05_TEMPLATE = PROMPTS_DIR / "05_receiver.txt"


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
    Verifica se o placeholder existe no template.
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
            "Monta o prompt 05_receiver usando o código "
            "04_integrated gerado por uma LLM."
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
    # CAMINHOS
    # --------------------------------------------------------

    model_dir = (
        RESULTS_DIR
        / model_result_dir
    )

    integrated_code_path = (
        model_dir
        / "04_integrated"
        / "code.ino"
    )

    output_dir = (
        model_dir
        / "05_receiver"
    )

    output_prompt = (
        output_dir
        / "prompt_generated.txt"
    )

    # --------------------------------------------------------
    # VERIFICA PASTA DO MODELO
    # --------------------------------------------------------

    if not model_dir.exists():
        print()
        print(
            "ERRO: pasta do modelo não encontrada:"
        )
        print(model_dir)
        sys.exit(1)

    # --------------------------------------------------------
    # LÊ O CÓDIGO INTEGRADO
    # --------------------------------------------------------

    integrated_code = read_file(
        integrated_code_path
    )

    # --------------------------------------------------------
    # LÊ O TEMPLATE DO PROMPT 05
    # --------------------------------------------------------

    prompt_template = read_file(
        PROMPT_05_TEMPLATE
    )

    # --------------------------------------------------------
    # VERIFICA PLACEHOLDER
    # --------------------------------------------------------

    placeholder = "{{CODIGO_INTEGRADO}}"

    check_placeholder(
        prompt_template,
        placeholder
    )

    # --------------------------------------------------------
    # SUBSTITUI O CÓDIGO
    # --------------------------------------------------------

    final_prompt = prompt_template.replace(
        placeholder,
        integrated_code
    )

    # --------------------------------------------------------
    # CONFIRMA QUE NÃO SOBROU PLACEHOLDER
    # --------------------------------------------------------

    if placeholder in final_prompt:
        print()
        print(
            "ERRO: o placeholder ainda está presente "
            "após a substituição:"
        )
        print(placeholder)
        sys.exit(1)

    # --------------------------------------------------------
    # CRIA PASTA DE SAÍDA
    # --------------------------------------------------------

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # SALVA O PROMPT FINAL
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
        "Prompt 05 criado com sucesso"
    )

    print(
        "----------------------------------------"
    )

    print(
        f"Modelo : {model_result_dir}"
    )

    print()

    print(
        "Código integrado utilizado:"
    )

    print(
        integrated_code_path
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
