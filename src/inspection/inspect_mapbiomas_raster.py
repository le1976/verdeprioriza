from pathlib import Path

import rasterio


ROOT_DIR = Path(__file__).resolve().parents[2]

RASTER = (
    ROOT_DIR
    / "data"
    / "raw"
    / "mapbiomas"
    / "collection11"
    / "raster"
    / "brazil_coverage-col11_2024.tif"
)


if not RASTER.exists():

    raise FileNotFoundError(
        f"Raster não encontrado:\n{RASTER}"
    )


print("=" * 72)
print("VERDEPRIORIZA - INSPEÇÃO MAPBIOMAS RASTER")
print("=" * 72)


with rasterio.open(RASTER) as src:

    print(
        f"\nArquivo: {RASTER.name}"
    )

    print(
        f"CRS: {src.crs}"
    )

    print(
        f"Largura: {src.width:,} pixels"
    )

    print(
        f"Altura: {src.height:,} pixels"
    )

    print(
        f"Bandas: {src.count}"
    )

    print(
        f"Tipo: {src.dtypes}"
    )

    print(
        f"NoData: {src.nodata}"
    )

    print(
        f"Resolução: {src.res}"
    )

    print(
        f"Limites: {src.bounds}"
    )

    print(
        f"Transformação:\n{src.transform}"
    )