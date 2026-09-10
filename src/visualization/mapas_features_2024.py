import os

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL


ROOT_DIR = Path(__file__).resolve().parents[2]


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


engine = create_engine(url)


sql = """
SELECT

    m.codigo_ibge,

    m.nome_municipio,

    f.score_baixa_cobertura,

    f.score_perda_vegetacao,

    f.score_pressao_agropecuaria,

    f.score_fogo_media_5a,

    f.score_fogo_carga_10a,

    m.geom

FROM core.dim_municipio m

JOIN analytics.feature_municipio f

    ON f.codigo_ibge = m.codigo_ibge

WHERE
    f.ano_referencia = 2024

    AND f.versao_features = 'v1.0';
"""


gdf = gpd.read_postgis(

    sql,

    engine,

    geom_col="geom",
)


OUTPUT_DIR = (

    ROOT_DIR
    / "outputs"
    / "maps"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


mapas = {

    "score_baixa_cobertura":
        (
            "score_baixa_cobertura_sp_2024.png",
            "Pressão por Baixa Cobertura Natural"
        ),

    "score_perda_vegetacao":
        (
            "score_perda_vegetacao_sp_2024.png",
            "Pressão por Redução Líquida de Cobertura"
        ),

    "score_pressao_agropecuaria":
        (
            "score_pressao_agropecuaria_sp_2024.png",
            "Pressão de Uso Agropecuário"
        ),

    "score_fogo_media_5a":
        (
            "score_fogo_recente_sp_2024.png",
            "Pressão Recente do Fogo"
        ),
}


for coluna, (
    arquivo,
    titulo
) in mapas.items():

    fig, ax = plt.subplots(
        figsize=(12, 10)
    )

    gdf.plot(

        column=coluna,

        vmin=0,

        vmax=100,

        legend=True,

        edgecolor="black",

        linewidth=0.15,

        ax=ax,

        legend_kwds={
            "label":
            "Score relativo de pressão (0–100)"
        },
    )


    ax.set_title(

        f"VerdePrioriza — {titulo}\n"
        "São Paulo — Referência 2024"
    )


    ax.set_axis_off()


    caminho = (
        OUTPUT_DIR
        /
        arquivo
    )


    plt.savefig(

        caminho,

        dpi=300,

        bbox_inches="tight",
    )


    plt.close()


    print(
        f"Mapa salvo: {caminho}"
    )