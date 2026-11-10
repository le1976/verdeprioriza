import os
from pathlib import Path

import geopandas as gpd
import requests

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL

from pystac_client import Client


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    ROOT_DIR
    / "data"
    / "raw"
    / "inpe"
    / "topodata"
    / "slope"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


STAC_URL = (
    "https://data.inpe.br/bdc/stac/v1"
)

COLLECTION = "topodata-1"

ASSET_DECLIVIDADE = "SN"


# ------------------------------------------------------------
# PRIMEIRO TESTE
# ------------------------------------------------------------

LIMITE_MUNICIPIOS = 20


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
# MUNICÍPIOS
# ============================================================

sql = f"""
SELECT

    codigo_ibge,

    nome_municipio,

    rank_ipa,

    geom

FROM spatial.municipio_alvo

ORDER BY rank_ipa

LIMIT {LIMITE_MUNICIPIOS};
"""


municipios = gpd.read_postgis(

    sql,

    engine,

    geom_col="geom",
)


municipios = municipios.to_crs(
    epsg=4326
)

COLUNA_GEOMETRIA = municipios.geometry.name


# ============================================================
# STAC
# ============================================================

catalog = Client.open(
    STAC_URL
)


ids_processados = set()


print("=" * 72)
print("VERDEPRIORIZA - DOWNLOAD TOPODATA SN")
print("=" * 72)


for _, municipio in municipios.iterrows():

    nome = municipio[
        "nome_municipio"
    ]


    codigo = municipio[
        "codigo_ibge"
    ]


    geometria_municipio = municipio[
    COLUNA_GEOMETRIA
]

    bbox = list(
        geometria_municipio.bounds
    )


    print(
        "\n" + "-" * 72
    )

    print(
        f"Município: {nome}"
    )

    print(
        f"Código: {codigo}"
    )

    print(
        f"BBOX: {bbox}"
    )


    busca = catalog.search(

        collections=[
            COLLECTION
        ],

        bbox=bbox,
    )


    items = list(
        busca.items()
    )


    print(
        f"Folhas encontradas: {len(items)}"
    )


    for item in items:

        if item.id in ids_processados:

            continue


        if ASSET_DECLIVIDADE not in item.assets:

            print(
                f"  {item.id}: "
                "asset SN não encontrado."
            )

            continue


        asset = item.assets[
            ASSET_DECLIVIDADE
        ]


        href = (
            asset.get_absolute_href()
            or
            asset.href
        )


        arquivo_saida = (

            OUTPUT_DIR
            /
            f"{item.id}_SN.tif"
        )


        if arquivo_saida.exists():

            print(
                f"  Já existe: "
                f"{arquivo_saida.name}"
            )

            ids_processados.add(
                item.id
            )

            continue


        print(
            f"  Baixando: {item.id}"
        )


        with requests.get(

            href,

            stream=True,

            timeout=300,

        ) as resposta:


            resposta.raise_for_status()


            with open(
                arquivo_saida,
                "wb",
            ) as f:


                for bloco in resposta.iter_content(
                    chunk_size=1024 * 1024
                ):

                    if bloco:

                        f.write(
                            bloco
                        )


        print(
            f"  Salvo: {arquivo_saida.name}"
        )


        ids_processados.add(
            item.id
        )


print("\n" + "=" * 72)
print("DOWNLOAD CONCLUÍDO")
print("=" * 72)