import os

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL


ROOT_DIR = Path(__file__).resolve().parents[2]

load_dotenv(
    ROOT_DIR / ".env",
    override=True,
)


url = URL.create(

    drivername="postgresql+psycopg",

    username=os.getenv("DB_USER"),

    password=os.getenv("DB_PASSWORD"),

    host=os.getenv("DB_HOST"),

    port=int(
        os.getenv(
            "DB_PORT",
            5433,
        )
    ),

    database=os.getenv("DB_NAME"),
)


engine = create_engine(url)

from sqlalchemy import text

with engine.connect() as conn:

    diagnostico = conn.execute(
        text("""
            SELECT
                current_database() AS banco,
                current_user AS usuario,
                inet_server_port() AS porta
        """)
    ).fetchone()

    registros = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM staging.inpe_fogo_municipio_ano
            WHERE ano = 2024
        """)
    ).scalar()

print("\nCONEXÃO UTILIZADA PELO PYTHON")
print("=" * 50)
print("Banco:", diagnostico.banco)
print("Usuário:", diagnostico.usuario)
print("Porta:", diagnostico.porta)
print("Registros INPE 2024:", registros)

sql = """
SELECT

    m.codigo_ibge,

    m.nome_municipio,

    COALESCE(
        f.focos_por_100_km2,
        0
    ) AS focos_por_100_km2,

    m.geom

FROM core.dim_municipio m

LEFT JOIN staging.inpe_fogo_municipio_ano f

    ON f.codigo_ibge = m.codigo_ibge
    AND f.ano = 2024

WHERE m.uf = 'SP';
"""


gdf = gpd.read_postgis(

    sql,

    engine,

    geom_col="geom",
)

print("\nVALIDAÇÃO DOS DADOS DO MAPA")
print("=" * 50)

print("Municípios:", len(gdf))

print(
    "Municípios com focos:",
    (gdf["focos_por_100_km2"] > 0).sum()
)

print(
    "Valor mínimo:",
    gdf["focos_por_100_km2"].min()
)

print(
    "Valor máximo:",
    gdf["focos_por_100_km2"].max()
)

print("\n10 maiores valores:")

print(
    gdf[
        [
            "nome_municipio",
            "focos_por_100_km2",
        ]
    ]
    .sort_values(
        "focos_por_100_km2",
        ascending=False,
    )
    .head(10)
    .to_string(index=False)
)


fig, ax = plt.subplots(
    figsize=(12, 10)
)


gdf.plot(

    column="focos_por_100_km2",

    legend=True,

    linewidth=0.15,

    edgecolor="black",

    ax=ax,

    legend_kwds={
        "label":
        "Focos do satélite de referência por 100 km²"
    },
)


ax.set_title(
    "VerdePrioriza — Pressão por Focos de Fogo\n"
    "Estado de São Paulo — INPE — 2024"
)


ax.set_axis_off()


saida = (

    ROOT_DIR
    / "outputs"
    / "maps"
    / "focos_fogo_sp_2024.png"
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