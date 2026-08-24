from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = (
    ROOT_DIR
    / "data"
    / "raw"
    / "mapbiomas"
    / "collection11"
)


arquivos = list(DATA_DIR.glob("*.xlsx"))

if not arquivos:
    raise FileNotFoundError(
        f"Nenhum arquivo .xlsx encontrado em:\n{DATA_DIR}"
    )


arquivo = arquivos[0]

print("=" * 70)
print("VERDEPRIORIZA - INSPEÇÃO MAPBIOMAS")
print("=" * 70)

print(f"\nArquivo: {arquivo.name}")


excel = pd.ExcelFile(arquivo)

print("\nPlanilhas encontradas:")

for nome in excel.sheet_names:
    print(f" - {nome}")


for nome in excel.sheet_names:

    print("\n" + "=" * 70)
    print(f"PLANILHA: {nome}")
    print("=" * 70)

    preview = pd.read_excel(
        arquivo,
        sheet_name=nome,
        header=None,
        nrows=10,
    )

    print(preview.to_string())