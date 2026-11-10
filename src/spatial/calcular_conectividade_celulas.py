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

CRS_METRICO = 5880


# ============================================================
# CONECTIVIDADE
# ============================================================

RAIO_ENTORNO_M = 1000


# ------------------------------------------------------------
# TESTE
#
# Comece com 1 município.
# Depois altere para 20.
# ------------------------------------------------------------

LIMITE_MUNICIPIOS = 20


# ============================================================
# CLASSES NATURAIS
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


# Classes que não devem entrar no denominador
# da estatística.

CLASSES_IGNORAR = {

    0,
    255,
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

def limpar_estatistica(
    estatistica,
    nodata,
):

    resultado = {}


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


        if nodata is not None:

            try:

                if classe_int == int(
                    nodata
                ):

                    continue

            except (
                ValueError,
                TypeError,
            ):

                pass


        if classe_int in CLASSES_IGNORAR:

            continue


        resultado[
            classe_int
        ] = quantidade


    return resultado


def contar_classes(
    estatistica,
    classes,
):

    return sum(

        quantidade

        for classe, quantidade
        in estatistica.items()

        if classe in classes
    )


# ============================================================
# ARQUIVO
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
print("VERDEPRIORIZA - CONECTIVIDADE")
print("=" * 72)


print(
    f"\nMunicípios a processar: "
    f"{len(municipios)}"
)


resultados_gerais = []


# ============================================================
# RASTER
# ============================================================

with rasterio.open(
    RASTER_MAPBIOMAS
) as src:


    if src.crs is None:

        raise ValueError(
            "O raster MapBiomas não possui CRS."
        )


    raster_crs = src.crs


    # --------------------------------------------------------
    # O arquivo MapBiomas pode não trazer NoData explícito.
    #
    # Para impedir que rasterstats utilize automaticamente
    # valores como -999, usamos 255 quando necessário.
    #
    # 255 não corresponde às classes que estamos utilizando.
    # --------------------------------------------------------

    if src.nodata is None:

        nodata_trabalho = 255

    else:

        nodata_trabalho = src.nodata


    print(
        f"\nCRS do raster: {raster_crs}"
    )


    print(
        f"NoData usado: {nodata_trabalho}"
    )


    # ========================================================
    # LOOP MUNICIPAL
    # ========================================================

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


        # ====================================================
        # CÉLULAS PRÉ-SELECIONADAS
        # ====================================================

        sql_celulas = text("""

        SELECT

            id_celula,

            codigo_ibge,

            area_ha,

            pct_vegetacao_natural,

            pct_uso_elegivel,

            geom

        FROM spatial.celula_prioridade

        WHERE

            codigo_ibge = :codigo_ibge

            AND ano_mapbiomas = 2024

            AND area_ha >= 1

            AND pixels_validos >= 10

            AND pct_uso_elegivel >= 30

            AND pct_area_urbanizada < 20

            AND pct_agua < 50

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
                "Nenhuma célula pré-selecionada."
            )

            continue


        print(
            f"Células pré-selecionadas: "
            f"{len(celulas):,}"
        )


        # ====================================================
        # GARANTIR CRS MÉTRICO
        # ====================================================

        if celulas.crs.to_epsg() != CRS_METRICO:

            celulas = celulas.to_crs(
                epsg=CRS_METRICO
            )


        # ====================================================
        # CRIAR ANEL DE 1 KM
        # ====================================================

        buffers = (

            celulas.geometry

            .buffer(
                RAIO_ENTORNO_M
            )
        )


        aneis = (

            buffers

            .difference(
                celulas.geometry
            )
        )


        entornos = gpd.GeoDataFrame(

            {

                "id_celula":
                    celulas[
                        "id_celula"
                    ].values,

            },

            geometry=aneis,

            crs=f"EPSG:{CRS_METRICO}",
        )


        # Área real do entorno em hectares.

        entornos[
            "area_entorno_ha"
        ] = (

            entornos.geometry.area

            /
            10000.0
        )


        # ====================================================
        # REPROJETAR APENAS OS ANÉIS
        # ====================================================

        entornos_raster = (

            entornos

            .to_crs(
                raster_crs
            )
        )


        # ====================================================
        # JANELA DO RASTER
        # ====================================================

        minx, miny, maxx, maxy = (

            entornos_raster
            .total_bounds
        )


        janela = from_bounds(

            minx,
            miny,
            maxx,
            maxy,

            transform=src.transform,
        )


        janela = (

            janela
            .round_offsets()
            .round_lengths()
        )


        array = src.read(

            1,

            window=janela,

            boundless=True,

            fill_value=nodata_trabalho,
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


        # ====================================================
        # ZONAL STATS
        # ====================================================

        estatisticas = zonal_stats(

            entornos_raster.geometry,

            array,

            affine=transform_janela,

            categorical=True,

            nodata=nodata_trabalho,

            all_touched=False,
        )


        # ====================================================
        # RESULTADOS
        # ====================================================

        resultados_municipio = []


        for (

            id_celula,

            area_entorno_ha,

            estatistica

        ) in zip(

            entornos[
                "id_celula"
            ],

            entornos[
                "area_entorno_ha"
            ],

            estatisticas,

        ):


            estatistica = (

                limpar_estatistica(

                    estatistica,

                    nodata_trabalho,
                )
            )


            total_pixels = sum(

                estatistica.values()
            )


            if total_pixels == 0:

                resultados_municipio.append(

                    {

                        "id_celula":
                            id_celula,

                        "area_entorno_ha":
                            area_entorno_ha,

                        "vegetacao_entorno_ha":
                            None,

                        "vegetacao_entorno_pct":
                            None,

                        "pixels_entorno_validos":
                            0,

                        "raio_conectividade_m":
                            RAIO_ENTORNO_M,
                    }

                )

                continue


            pixels_naturais = (

                contar_classes(

                    estatistica,

                    CLASSES_NATURAIS,
                )
            )


            vegetacao_pct = (

                pixels_naturais

                /
                total_pixels

                *
                100
            )


            # Estimativa de área natural do entorno.
            #
            # A porcentagem vem do raster.
            # A área total do entorno vem da geometria
            # métrica em EPSG:5880.

            vegetacao_ha = (

                area_entorno_ha

                *
                vegetacao_pct

                /
                100
            )


            resultados_municipio.append(

                {

                    "id_celula":
                        id_celula,

                    "area_entorno_ha":
                        round(
                            area_entorno_ha,
                            4
                        ),

                    "vegetacao_entorno_ha":
                        round(
                            vegetacao_ha,
                            4
                        ),

                    "vegetacao_entorno_pct":
                        round(
                            vegetacao_pct,
                            2
                        ),

                    "pixels_entorno_validos":
                        int(
                            total_pixels
                        ),

                    "raio_conectividade_m":
                        RAIO_ENTORNO_M,

                }

            )


        resultado_df = pd.DataFrame(

            resultados_municipio
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


print(

    "\nTotal de células com análise "
    f"de entorno: {len(resultado_final):,}"
)


# ============================================================
# STAGING
# ============================================================

resultado_final.to_sql(

    name="conectividade_celula_temp",

    schema="staging",

    con=engine,

    if_exists="replace",

    index=False,
)


# ============================================================
# ATUALIZAR SPATIAL
# ============================================================

sql_update = """

UPDATE spatial.celula_prioridade c

SET

    area_entorno_ha =
        t.area_entorno_ha,

    vegetacao_entorno_ha =
        t.vegetacao_entorno_ha,

    vegetacao_entorno_pct =
        t.vegetacao_entorno_pct,

    pixels_entorno_validos =
        t.pixels_entorno_validos,

    raio_conectividade_m =
        t.raio_conectividade_m,

    data_calculo =
        CURRENT_TIMESTAMP

FROM staging.conectividade_celula_temp t

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
        staging.conectividade_celula_temp;
        """)

    )


print("\n" + "=" * 72)
print("CONECTIVIDADE PROCESSADA COM SUCESSO")
print("=" * 72)
