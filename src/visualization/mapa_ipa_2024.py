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

    i.ipa,

    i.classificacao,

    i.rank_ipa,

    i.estabilidade,

    m.geom

FROM core.dim_municipio m

JOIN analytics.ipa_municipio i

    ON i.codigo_ibge = m.codigo_ibge

WHERE

    i.ano_referencia = 2024

    AND i.versao_modelo = 'ipa_v1.0_2024';
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

    column="ipa",

    vmin=0,

    vmax=100,

    legend=True,

    linewidth=0.15,

    edgecolor="black",

    ax=ax,

    legend_kwds={
        "label":
        "Índice de Prioridade Ambiental — IPA (0–100)"
    },
)


ax.set_title(

    "VerdePrioriza — Índice de Prioridade Ambiental\n"
    "Estado de São Paulo — Referência 2024"
)


ax.set_axis_off()


saida = (

    ROOT_DIR

    / "outputs"

    / "maps"

    / "ipa_sp_2024.png"
)


saida.parent.mkdir(

    parents=True,

    exist_ok=True,
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