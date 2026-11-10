import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

from rasterio.windows import from_bounds
from rasterstats import zonal_stats

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL
from sqlalchemy import text


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]


RASTER_MAPBIOMAS = (

    ROOT_DIR
    / "data"
    / "raw"
    / "mapbiomas"
    / "collection11"
    / "raster"
    / "brazil_coverage-col11_2024.tif"
)


ANO_MAPBIOMAS = 2024

COLECAO_MAPBIOMAS = "11"


# ------------------------------------------------------------
# PRIMEIRO TESTE
#
# Comece com 1.
# Após validar, altere para 20.
# ------------------------------------------------------------

LIMITE_MUNICIPIOS = 20


# ============================================================
# CLASSES MAPBIOMAS
# ============================================================


CLASSES_NATURAIS = {

    1,
    3,
    4,
    5,
    6,
    7,

    10,
    11,
    12,

    49,
    50,
    77,
    84,
}


CLASSES_USO_CANDIDATO = {

    9,

    14,
    15,

    18,
    19,
    20,
    21,

    35,
    36,
    39,
    40,
    41,

    46,
    47,
    48,

    62,
}


CLASSES_AGUA = {

    26,
    31,
    33,
}


CLASSES_URBANAS = {

    24,
}


# ============================================================
# NOMES DAS CLASSES
# ============================================================

NOMES_CLASSES = {

    1:
        "Formação Florestal",

    3:
        "Formação Florestal",

    4:
        "Formação Savânica",

    5:
        "Mangue",

    6:
        "Floresta Alagável",

    7:
        "Savana Alagada",

    10:
        "Vegetação Herbácea e Arbustiva",

    11:
        "Campo Alagado e Área Pantanosa",

    12:
        "Formação Campestre",

    49:
        "Restinga Arbórea",

    50:
        "Restinga Herbácea/Arbustiva",

    77:
        "Formação Herbácea Arbustiva",

    84:
        "Marisma",

    9:
        "Silvicultura",

    14:
        "Agropecuária",

    15:
        "Pastagem",

    18:
        "Agricultura",

    19:
        "Lavoura Temporária",

    20:
        "Cana",

    21:
        "Mosaico de Usos",

    35:
        "Dendê",

    36:
        "Lavoura Perene",

    39:
        "Soja",

    40:
        "Arroz",

    41:
        "Outras Lavouras Temporárias",

    46:
        "Café",

    47:
        "Citrus",

    48:
        "Outras Lavouras Perenes",

    62:
        "Algodão",

    22:
        "Área não vegetada",

    23:
        "Praia, Duna e Areal",

    24:
        "Área urbanizada",

    25:
        "Outras Áreas Não Vegetadas",

    30:
        "Mineração",

    75:
        "Usina Fotovoltaica",

    91:
        "Parque Eólico",

    26:
        "Corpo d'Água",

    31:
        "Aquicultura",

    33:
        "Rio, Lago e Oceano",
}


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
# FUNÇÕES
# ============================================================


def soma_classes(
    estatistica,
    classes,
):

    total = 0

    for classe, quantidade in estatistica.items():

        try:

            classe_int = int(
                classe
            )

        except (
            TypeError,
            ValueError,
        ):

            continue


        if classe_int in classes:

            total += quantidade


    return total


def classe_predominante(
    estatistica
):

    if not estatistica:

        return None


    itens = []


    for classe, quantidade in estatistica.items():

        try:

            classe_int = int(
                classe
            )

        except (
            TypeError,
            ValueError,
        ):

            continue


        itens.append(

            (
                classe_int,
                quantidade,
            )

        )


    if not itens:

        return None


    return max(

        itens,

        key=lambda x: x[1],

    )[0]


# ============================================================
# VALIDAÇÃO DO ARQUIVO
# ============================================================

if not RASTER_MAPBIOMAS.exists():

    raise FileNotFoundError(

        f"Raster não encontrado:\n"
        f"{RASTER_MAPBIOMAS}"
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
print("VERDEPRIORIZA - MAPBIOMAS CÉLULAS")
print("=" * 72)

print(
    f"\nMunicípios a processar: "
    f"{len(municipios)}"
)


# ============================================================
# ABRIR RASTER UMA ÚNICA VEZ
# ============================================================

with rasterio.open(
    RASTER_MAPBIOMAS
) as src:


    if src.crs is None:

        raise ValueError(
            "O raster MapBiomas não possui CRS definido."
        )


    raster_crs = src.crs

    nodata = src.nodata

    NODATA_STATS = -999


    print(
        f"\nCRS do raster: {raster_crs}"
    )

    print(
        f"NoData: {nodata}"
    )


    resultados_gerais = []


    # ========================================================
    # LOOP MUNICIPAL
    # ========================================================

    for _, mun in municipios.iterrows():


        codigo = mun[
            "codigo_ibge"
        ]

        nome = mun[
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


        # ----------------------------------------------------
        # CARREGAR CÉLULAS
        # ----------------------------------------------------

        sql_celulas = text("""

        SELECT

            id_celula,

            codigo_ibge,

            area_ha,

            geom

        FROM spatial.celula_prioridade

        WHERE codigo_ibge = :codigo_ibge

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


        # ----------------------------------------------------
        # REPROJETAR CÉLULAS PARA CRS DO RASTER
        # ----------------------------------------------------

        celulas_raster = (

            celulas

            .to_crs(
                raster_crs
            )

        )


        # ----------------------------------------------------
        # BOUNDING BOX MUNICIPAL
        # ----------------------------------------------------

        minx, miny, maxx, maxy = (

            celulas_raster
            .total_bounds

        )


        # ----------------------------------------------------
        # JANELA DO RASTER
        # ----------------------------------------------------

        janela = from_bounds(

            minx,
            miny,
            maxx,
            maxy,

            transform=src.transform,
        )


        # Adicionamos pequena margem
        # para evitar efeitos numéricos
        # na borda.

        janela = (

            janela
            .round_offsets()
            .round_lengths()

        )


        # ----------------------------------------------------
        # LER SOMENTE RECORTE NECESSÁRIO
        # ----------------------------------------------------

        array = (
    src.read(
        1,
        window=janela,
        boundless=True,
        masked=True,
    )
    .astype(
        np.int16
    )
    .filled(
        NODATA_STATS
    )
)


        transform_janela = (

            src.window_transform(
                janela
            )

        )


        print(
            f"Janela raster: "
            f"{array.shape[1]:,} × "
            f"{array.shape[0]:,} pixels"
        )


        # ----------------------------------------------------
        # ESTATÍSTICA CATEGÓRICA
        # ----------------------------------------------------

        estatisticas = zonal_stats(

            celulas_raster.geometry,

            array,

            affine=transform_janela,

            categorical=True,

            nodata=NODATA_STATS,

            all_touched=False,
        )


        # ----------------------------------------------------
        # PROCESSAR CADA CÉLULA
        # ----------------------------------------------------

        resultados_municipio = []


        for (
            id_celula,
            area_ha,
            estatistica
        ) in zip(

            celulas[
                "id_celula"
            ],

            celulas[
                "area_ha"
            ],

            estatisticas,

        ):


            # ----------------------------------------------
            # REMOVER POSSÍVEL NODATA
            # ----------------------------------------------

            estatistica_limpa = {}


            for classe, qtd in estatistica.items():

                try:

                    classe_int = int(
                        classe
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    continue


                if (
                    classe_int
                    ==
                    NODATA_STATS
                ):

                    continue


                estatistica_limpa[
                    classe_int
                ] = qtd


            total_pixels = sum(

                estatistica_limpa
                .values()

            )


            if total_pixels == 0:

                resultados_municipio.append(

                    {
                        "id_celula":
                            id_celula,

                        "pct_vegetacao_natural":
                            None,

                        "pct_uso_elegivel":
                            None,

                        "pct_agua":
                            None,

                        "pct_area_urbanizada":
                            None,

                        "classe_predominante":
                            None,

                        "uso_predominante":
                            None,

                        "pixels_validos":
                            0,

                        "score_elegibilidade":
                            None,

                        "ano_mapbiomas":
                            ANO_MAPBIOMAS,

                        "colecao_mapbiomas":
                            COLECAO_MAPBIOMAS,
                    }
                )

                continue


            pixels_naturais = (

                soma_classes(

                    estatistica_limpa,

                    CLASSES_NATURAIS,
                )
            )


            pixels_candidatos = (

                soma_classes(

                    estatistica_limpa,

                    CLASSES_USO_CANDIDATO,
                )
            )


            pixels_agua = (

                soma_classes(

                    estatistica_limpa,

                    CLASSES_AGUA,
                )
            )


            pixels_urbanos = (

                soma_classes(

                    estatistica_limpa,

                    CLASSES_URBANAS,
                )
            )


            pct_natural = (

                pixels_naturais

                /
                total_pixels

                *
                100
            )


            pct_candidato = (

                pixels_candidatos

                /
                total_pixels

                *
                100
            )


            pct_agua = (

                pixels_agua

                /
                total_pixels

                *
                100
            )


            pct_urbano = (

                pixels_urbanos

                /
                total_pixels

                *
                100
            )


            classe_dom = (

                classe_predominante(
                    estatistica_limpa
                )
            )


            nome_classe = (

                NOMES_CLASSES.get(

                    classe_dom,

                    f"Classe {classe_dom}"
                )

                if classe_dom
                is not None

                else None
            )


            # ----------------------------------------------
            # SCORE DE ELEGIBILIDADE
            #
            # Nesta primeira versão, o score é diretamente
            # o percentual de uso candidato.
            # ----------------------------------------------

            score_elegibilidade = (
                pct_candidato
            )


            resultados_municipio.append(

                {

                    "id_celula":
                        id_celula,

                    "pct_vegetacao_natural":
                        round(
                            pct_natural,
                            2
                        ),

                    "pct_uso_elegivel":
                        round(
                            pct_candidato,
                            2
                        ),

                    "pct_agua":
                        round(
                            pct_agua,
                            2
                        ),

                    "pct_area_urbanizada":
                        round(
                            pct_urbano,
                            2
                        ),

                    "classe_predominante":
                        classe_dom,

                    "uso_predominante":
                        nome_classe,

                    "pixels_validos":
                        int(
                            total_pixels
                        ),

                    "score_elegibilidade":
                        round(
                            score_elegibilidade,
                            2
                        ),

                    "ano_mapbiomas":
                        ANO_MAPBIOMAS,

                    "colecao_mapbiomas":
                        COLECAO_MAPBIOMAS,
                }

            )


        resultado_df = pd.DataFrame(

            resultados_municipio

        )


        resultados_gerais.append(
            resultado_df
        )


        print(
            "Células processadas: "
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


print(
    "\nTotal processado: "
    f"{len(resultado_final):,}"
)


# ============================================================
# STAGING
# ============================================================

resultado_final.to_sql(

    name="mapbiomas_celula_temp",

    schema="staging",

    con=engine,

    if_exists="replace",

    index=False,
)


# ============================================================
# ATUALIZAR TABELA PRINCIPAL
# ============================================================

sql_update = """

UPDATE spatial.celula_prioridade c

SET

    pct_vegetacao_natural =
        t.pct_vegetacao_natural,

    pct_uso_elegivel =
        t.pct_uso_elegivel,

    pct_agua =
        t.pct_agua,

    pct_area_urbanizada =
        t.pct_area_urbanizada,

    classe_predominante =
        t.classe_predominante,

    uso_predominante =
        t.uso_predominante,

    pixels_validos =
        t.pixels_validos,

    score_elegibilidade =
        t.score_elegibilidade,

    ano_mapbiomas =
        t.ano_mapbiomas,

    colecao_mapbiomas =
        t.colecao_mapbiomas,

    data_calculo =
        CURRENT_TIMESTAMP

FROM staging.mapbiomas_celula_temp t

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
        staging.mapbiomas_celula_temp;
        """)
    )


print("\n" + "=" * 72)
print("MAPBIOMAS 2024 PROCESSADO COM SUCESSO")
print("=" * 72)
