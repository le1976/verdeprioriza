import os
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]


OUTPUT_DIR = (
    ROOT_DIR
    / "outputs"
    / "maps"
    / "module9i"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


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

sql_municipios = """

SELECT

    m.codigo_ibge,

    m.nome_municipio,

    ST_Transform(
        m.geom,
        5880
    ) AS geom

FROM core.dim_municipio m

JOIN spatial.municipio_alvo a

    ON a.codigo_ibge =
       m.codigo_ibge;

"""


municipios = gpd.read_postgis(
    sql_municipios,
    engine,
    geom_col="geom",
    crs="EPSG:5880",
)


# ============================================================
# ÁREAS FINAIS
# ============================================================

sql_areas = """

SELECT *

FROM spatial.vw_areas_finais_9i

WHERE
    status_validacao =
        'Aprovada';

"""


areas = gpd.read_postgis(
    sql_areas,
    engine,
    geom_col="geom",
    crs="EPSG:5880",
)


if areas.empty:

    raise ValueError(
        "Nenhuma área aprovada foi encontrada "
        "em spatial.vw_areas_finais_9i."
    )


# ============================================================
# MAPA 1
# PRIORIDADE RELATIVA
# ============================================================

fig, ax = plt.subplots(
    figsize=(15, 12)
)


municipios.boundary.plot(

    ax=ax,

    linewidth=0.6,

    alpha=0.6,
)


areas.plot(

    ax=ax,

    column="percentil_prioridade",

    cmap="viridis",

    legend=True,

    linewidth=0.2,
)


ax.set_title(

    "VerdePrioriza — Áreas Prioritárias\n"
    "20 municípios-alvo | Referência 2024",

    fontsize=16,
)


ax.set_axis_off()


fig.tight_layout()


saida_prioridade = (

    OUTPUT_DIR
    / "areas_prioritarias_percentil_2024.png"
)


fig.savefig(

    saida_prioridade,

    dpi=300,

    bbox_inches="tight",
)


plt.close(fig)



# ============================================================
# MAPA 2
# ROBUSTEZ
# ============================================================

# ============================================================
# MAPA 2
# ROBUSTEZ
# ============================================================

fig, ax = plt.subplots(
    figsize=(15, 12)
)


municipios.boundary.plot(

    ax=ax,

    linewidth=0.6,

    alpha=0.6,
)


areas.plot(

    ax=ax,

    column="robustez_area",

    categorical=True,

    legend=True,

    linewidth=0.2,

    legend_kwds={
        "title": "Robustez",
    },
)


ax.set_title(

    "VerdePrioriza — Robustez das Áreas Prioritárias\n"
    "Referência 2024",

    fontsize=16,
)


ax.set_axis_off()


fig.tight_layout()


saida_robustez = (

    OUTPUT_DIR
    / "areas_prioritarias_robustez_2024.png"
)


fig.savefig(

    saida_robustez,

    dpi=300,

    bbox_inches="tight",
)


plt.close(fig)

# ============================================================
# TOP 30
# ============================================================

top30 = (

    areas

    .sort_values(
        "rank_area_geral"
    )

    .head(30)

    .copy()
)


fig, ax = plt.subplots(
    figsize=(15, 12)
)


municipios.boundary.plot(

    ax=ax,

    linewidth=0.5,

    alpha=0.5,
)


areas.boundary.plot(

    ax=ax,

    linewidth=0.25,

    alpha=0.4,
)


top30.plot(

    ax=ax,

    column="rank_area_geral",

    legend=True,

    cmap="viridis_r",

    linewidth=0.5,
)


for _, area in top30.head(10).iterrows():

    ponto = (
        area["geom"]
        .representative_point()
    )


    ax.annotate(

        str(
            int(
                area["rank_area_geral"]
            )
        ),

        xy=(
            ponto.x,
            ponto.y,
        ),

        fontsize=6,

        ha="center",
    )


ax.set_title(

    "VerdePrioriza — Top 30 Áreas Prioritárias\n"
    "Ranking operacional | 2024",

    fontsize=16,
)


ax.set_axis_off()


fig.tight_layout()


saida_top30 = (

    OUTPUT_DIR
    / "top30_areas_prioritarias_2024.png"
)


fig.savefig(

    saida_top30,

    dpi=300,

    bbox_inches="tight",
)


plt.close(fig)



# ============================================================
# FINALIZAÇÃO
# ============================================================

print("=" * 72)

print(
    "VERDEPRIORIZA - MAPAS TÉCNICOS 9I"
)

print("=" * 72)


print(
    f"\nMunicípios: "
    f"{municipios['codigo_ibge'].nunique()}"
)


print(
    f"Áreas aprovadas: "
    f"{len(areas)}"
)


print(
    "\nArquivos:"
)


print(
    saida_prioridade
)


print(
    saida_robustez
)


print(
    saida_top30
)