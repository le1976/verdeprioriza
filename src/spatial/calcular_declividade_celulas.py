import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

from rasterio.merge import merge

from rasterstats import zonal_stats

from shapely.geometry import box

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL
from sqlalchemy import text


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]


RASTER_DIR = (
    ROOT_DIR
    / "data"
    / "raw"
    / "inpe"
    / "topodata"
    / "slope"
)


CRS_METRICO = 5880


# ------------------------------------------------------------
# PRIMEIRO TESTE
# ------------------------------------------------------------

LIMITE_MUNICIPIOS = 20


# Usaremos um valor interno explícito de NoData
# no mosaico temporário.

NODATA_TRABALHO = -9999.0


# ============================================================
# BANCO
# ============================================================

load_dotenv(
    ROOT_DIR / ".env"
)


url = URL.create(

    drivername="postgresql+psycopg",

    username=os.getenv("DB_USER"),

    password=os.getenv("DB_PASSWORD"),

    host=os.getenv("DB_HOST"),

    port=int(
        os.getenv(
            "DB_PORT",
            5432,
        )
    ),

    database=os.getenv("DB_NAME"),
)


engine = create_engine(
    url,
    pool_pre_ping=True,
)


# ============================================================
# ARQUIVOS TOPODATA
# ============================================================

arquivos = sorted(

    RASTER_DIR.glob(
        "*_SN.tif"
    )
)


if not arquivos:

    raise FileNotFoundError(
        f"Nenhum arquivo SN encontrado em:\n"
        f"{RASTER_DIR}"
    )


# ============================================================
# MUNICÍPIOS
# ============================================================

sql_municipios = f"""

SELECT

    codigo_ibge,

    nome_municipio,

    rank_ipa

FROM spatial.municipio_alvo

ORDER BY rank_ipa

LIMIT {LIMITE_MUNICIPIOS};

"""


municipios = pd.read_sql(

    sql_municipios,

    engine,
)


print("=" * 72)
print("VERDEPRIORIZA - DECLIVIDADE")
print("=" * 72)

print(
    f"\nMunicípios a processar: "
    f"{len(municipios)}"
)


resultados_gerais = []


# ============================================================
# LOOP MUNICIPAL
# ============================================================

for _, municipio in municipios.iterrows():


    codigo = municipio[
        "codigo_ibge"
    ]

    nome = municipio[
        "nome_municipio"
    ]


    print(
        "\n" + "-" * 72
    )

    print(
        f"Município: {nome}"
    )

    print(
        f"Código IBGE: {codigo}"
    )


    # ========================================================
    # CÉLULAS DO FUNIL
    # ========================================================

    sql_celulas = text("""

    SELECT

        id_celula,

        codigo_ibge,

        area_ha,

        pct_uso_elegivel,

        vegetacao_entorno_pct,

        geom

    FROM spatial.celula_prioridade

    WHERE

        codigo_ibge = :codigo_ibge

        AND area_ha >= 1

        AND pixels_validos >= 10

        AND pct_uso_elegivel >= 30

        AND pct_area_urbanizada < 20

        AND pct_agua < 50

        AND vegetacao_entorno_pct
            IS NOT NULL

    ORDER BY id_celula;

    """)


    celulas = gpd.read_postgis(

        sql_celulas,

        engine,

        geom_col="geom",

        params={
            "codigo_ibge":
                codigo
        },
    )


    if celulas.empty:

        print(
            "Nenhuma célula encontrada."
        )

        continue


    print(
        f"Células: {len(celulas):,}"
    )


    # ========================================================
    # DESCOBRIR CRS DO PRIMEIRO RASTER
    # ========================================================

    with rasterio.open(
        arquivos[0]
    ) as exemplo:

        raster_crs = exemplo.crs


    if raster_crs is None:

        raise ValueError(
            "TOPODATA sem CRS definido."
        )


    # ========================================================
    # REPROJETAR CÉLULAS PARA O CRS DO TOPODATA
    # ========================================================

    celulas_raster = (

        celulas

        .to_crs(
            raster_crs
        )
    )


    minx, miny, maxx, maxy = (

        celulas_raster
        .total_bounds
    )


    bbox_celulas = box(

        minx,
        miny,
        maxx,
        maxy,
    )


    # ========================================================
    # LOCALIZAR SOMENTE AS FOLHAS QUE INTERSECTAM
    # O MUNICÍPIO
    # ========================================================

    rasters_intersectam = []


    for arquivo in arquivos:

        with rasterio.open(
            arquivo
        ) as src:

            if src.crs != raster_crs:

                raise ValueError(
                    f"CRS diferente em "
                    f"{arquivo.name}"
                )


            bbox_raster = box(
                *src.bounds
            )


            if bbox_raster.intersects(
                bbox_celulas
            ):

                rasters_intersectam.append(
                    arquivo
                )


    if not rasters_intersectam:

        raise ValueError(
            f"Nenhuma folha TOPODATA "
            f"intersecta {nome}."
        )


    print(
        "Folhas utilizadas:"
    )


    for arquivo in rasters_intersectam:

        print(
            f"  - {arquivo.name}"
        )


    # ========================================================
    # ABRIR RASTERS
    # ========================================================

    sources = [

        rasterio.open(
            arquivo
        )

        for arquivo
        in rasters_intersectam
    ]


    try:

        # ====================================================
        # MOSAICO RESTRITO AO MUNICÍPIO
        # ====================================================

        mosaico, transform = merge(

            sources,

            bounds=(
                minx,
                miny,
                maxx,
                maxy,
            ),

            nodata=NODATA_TRABALHO,

            dtype="float32",
        )


        array = mosaico[0]


        print(

            f"Mosaico: "

            f"{array.shape[1]:,} × "

            f"{array.shape[0]:,} pixels"
        )


        # ====================================================
        # ESTATÍSTICAS ZONAIS
        # ====================================================

        estatisticas = zonal_stats(

            celulas_raster.geometry,

            array,

            affine=transform,

            nodata=NODATA_TRABALHO,

            all_touched=False,

            stats=[

                "count",

                "mean",

                "max",

                "percentile_90",
            ],
        )


    finally:

        for src in sources:

            src.close()


    # ========================================================
    # RESULTADOS
    # ========================================================

    resultados = []


    for id_celula, estatistica in zip(

        celulas[
            "id_celula"
        ],

        estatisticas,
    ):


        quantidade = (

            estatistica.get(
                "count",
                0
            )

            or 0
        )


        media = estatistica.get(
            "mean"
        )


        p90 = estatistica.get(
            "percentile_90"
        )


        maximo = estatistica.get(
            "max"
        )


        if quantidade == 0:

            media = None
            p90 = None
            maximo = None


        resultados.append(

            {

                "id_celula":
                    id_celula,

                "declividade_media_pct":
                    media,

                "declividade_p90_pct":
                    p90,

                "declividade_max_pct":
                    maximo,

                "pixels_declividade_validos":
                    int(
                        quantidade
                    ),

                "fonte_relevo":
                    "TOPODATA_SN_INPE",
            }

        )


    resultado_df = pd.DataFrame(
        resultados
    )


    resultados_gerais.append(
        resultado_df
    )


    print(
        f"Células processadas: "
        f"{len(resultado_df):,}"
    )


# ============================================================
# CONSOLIDAR
# ============================================================

if not resultados_gerais:

    raise ValueError(
        "Nenhuma célula foi processada."
    )


resultado_final = pd.concat(

    resultados_gerais,

    ignore_index=True,
)


# ============================================================
# STAGING
# ============================================================

resultado_final.to_sql(

    name="declividade_celula_temp",

    schema="staging",

    con=engine,

    if_exists="replace",

    index=False,
)


# ============================================================
# UPDATE
# ============================================================

sql_update = """

UPDATE spatial.celula_prioridade c

SET

    declividade_media_pct =
        t.declividade_media_pct,

    declividade_p90_pct =
        t.declividade_p90_pct,

    declividade_max_pct =
        t.declividade_max_pct,

    pixels_declividade_validos =
        t.pixels_declividade_validos,

    fonte_relevo =
        t.fonte_relevo,

    data_calculo =
        CURRENT_TIMESTAMP

FROM staging.declividade_celula_temp t

WHERE
    c.id_celula =
    t.id_celula;

"""


with engine.begin() as conn:

    conn.execute(
        text(
            sql_update
        )
    )

    conn.execute(

        text("""
        DROP TABLE IF EXISTS
        staging.declividade_celula_temp;
        """)

    )


print("\n" + "=" * 72)
print("DECLIVIDADE PROCESSADA COM SUCESSO")
print("=" * 72)