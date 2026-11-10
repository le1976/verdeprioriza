from pathlib import Path

import rasterio


ROOT_DIR = Path(__file__).resolve().parents[2]

PASTA = (
    ROOT_DIR
    / "data"
    / "raw"
    / "inpe"
    / "topodata"
    / "slope"
)


arquivos = sorted(
    PASTA.glob("*_SN.tif")
)


if not arquivos:

    raise FileNotFoundError(
        "Nenhum raster SN encontrado."
    )


print("=" * 72)
print("VERDEPRIORIZA - INSPEÇÃO TOPODATA")
print("=" * 72)


for arquivo in arquivos:

    with rasterio.open(
        arquivo
    ) as src:

        print(
            "\n" + "-" * 72
        )

        print(
            f"Arquivo: {arquivo.name}"
        )

        print(
            f"CRS: {src.crs}"
        )

        print(
            f"Resolução: {src.res}"
        )

        print(
            f"NoData: {src.nodata}"
        )

        print(
            f"Tipo: {src.dtypes}"
        )

        print(
            f"Limites: {src.bounds}"
        )