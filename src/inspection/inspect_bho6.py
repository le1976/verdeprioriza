from pathlib import Path
import pyogrio


ROOT_DIR = Path(__file__).resolve().parents[2]

PASTA = (
    ROOT_DIR
    / "data"
    / "raw"
    / "ana"
    / "bho6"
)


arquivos = list(
    PASTA.glob("*.gpkg")
)


for arquivo in arquivos:

    print("\n" + "=" * 70)

    print(
        arquivo.name
    )

    print("=" * 70)

    camadas = pyogrio.list_layers(
        arquivo
    )

    print(camadas)