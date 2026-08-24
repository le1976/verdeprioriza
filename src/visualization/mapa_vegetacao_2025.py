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

    i.vegetacao_nativa_pct,

    m.geom

FROM core.dim_municipio m

JOIN analytics.indicador_municipio i
    ON i.codigo_ibge = m.codigo_ibge

WHERE i.ano = 2025;
"""


gdf = gpd.read_postgis(

    sql,

    engine,

    geom_col="geom",
)


fig, ax = plt.subplots(
    figsize=(12, 10)
)


gdf.plot(

    column="vegetacao_nativa_pct",

    legend=True,

    edgecolor="black",

    linewidth=0.15,

    ax=ax,

    legend_kwds={
        "label":
        "Cobertura natural estimada (%)"
    },
)


ax.set_title(
    "VerdePrioriza — Cobertura Natural por Município\n"
    "São Paulo — MapBiomas Coleção 11 — 2025"
)


ax.set_axis_off()


saida = (

    ROOT_DIR
    / "outputs"
    / "maps"
    / "cobertura_natural_sp_2025.png"
)


saida.parent.mkdir(
    parents=True,
    exist_ok=True
)


plt.savefig(

    saida,

    dpi=300,

    bbox_inches="tight",
)


plt.show()


print(
    f"Mapa salvo em:\n{saida}"
)