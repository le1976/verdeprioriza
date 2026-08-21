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
    port=int(os.getenv("DB_PORT", 5432)),
    database=os.getenv("DB_NAME"),
)


engine = create_engine(url)


sql = """
SELECT
    codigo_ibge,
    nome_municipio,
    area_km2,
    geom
FROM core.dim_municipio;
"""


gdf = gpd.read_postgis(
    sql,
    engine,
    geom_col="geom",
)


fig, ax = plt.subplots(
    figsize=(10, 10)
)


gdf.plot(
    ax=ax,
    edgecolor="black",
    linewidth=0.25,
)


ax.set_title(
    "VerdePrioriza - Municípios do Estado de São Paulo"
)


ax.set_axis_off()


pasta_saida = (
    ROOT_DIR
    / "outputs"
    / "maps"
)

pasta_saida.mkdir(
    parents=True,
    exist_ok=True
)


arquivo_saida = (
    pasta_saida
    / "municipios_sp.png"
)


plt.savefig(
    arquivo_saida,
    dpi=300,
    bbox_inches="tight",
)


plt.show()


print(
    f"Mapa salvo em: {arquivo_saida}"
)