import os
import re
import unicodedata

from pathlib import Path

import pandas as pd
import geopandas as gpd

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL
from sqlalchemy import text


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = (
    ROOT_DIR
    / "data"
    / "raw"
    / "inpe"
    / "queimadas"
)


ANO_INICIAL = 2015
ANO_FINAL = 2024

SATELITE_REFERENCIA = "AQUA_M-T"


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


engine = create_engine(url)


# ============================================================
# FUNÇÕES
# ============================================================

def normalizar_nome(valor):

    texto = str(valor)

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        c
        for c in texto
        if not unicodedata.combining(c)
    )

    texto = texto.lower()

    texto = re.sub(
        r"[^a-z0-9]+",
        "_",
        texto,
    )

    return texto.strip("_")


def localizar_coluna(
    colunas,
    candidatos,
):

    for candidato in candidatos:

        if candidato in colunas:
            return candidato

    return None


# ============================================================
# ARQUIVOS
# ============================================================

arquivos = list(
    DATA_DIR.glob("*.csv")
)


if not arquivos:

    raise FileNotFoundError(
        f"Nenhum CSV encontrado em:\n{DATA_DIR}"
    )


print("=" * 70)
print("VERDEPRIORIZA - ETL INPE QUEIMADAS")
print("=" * 70)

print(
    f"\nArquivos encontrados: {len(arquivos)}"
)


frames = []


# ============================================================
# LEITURA
# ============================================================

for arquivo in arquivos:

    print(
        f"Lendo: {arquivo.name}"
    )

    df = pd.read_csv(
        arquivo,
        encoding="utf-8",
        low_memory=False,
    )

    df.columns = [
        normalizar_nome(c)
        for c in df.columns
    ]

    df["arquivo_origem"] = (
        arquivo.name
    )

    frames.append(
        df
    )


df = pd.concat(
    frames,
    ignore_index=True,
)


print(
    f"\nRegistros lidos: {len(df):,}"
)


# ============================================================
# IDENTIFICAR COLUNAS
# ============================================================

col_data = localizar_coluna(
    df.columns,
    [
        "data_pas",
        "datahora",
        "data_hora",
        "data_hora_gmt",
    ],
)


col_satelite = localizar_coluna(
    df.columns,
    [
        "satelite",
        "satellite",
    ],
)

# Os arquivos anuais utilizados já correspondem aos
# focos do satélite de referência. Quando o CSV não
# possui a coluna "satelite", criamos uma coluna
# padronizada para manter compatibilidade com o ETL.

if col_satelite is None:

    df["_satelite_origem"] = SATELITE_REFERENCIA

    col_satelite = "_satelite_origem"


col_estado = localizar_coluna(
    df.columns,
    [
        "estado",
        "state",
    ],
)


col_latitude = localizar_coluna(
    df.columns,
    [
        "latitude",
        "lat",
    ],
)


col_longitude = localizar_coluna(
    df.columns,
    [
        "longitude",
        "lon",
        "long",
    ],
)


col_bioma = localizar_coluna(
    df.columns,
    [
        "bioma",
        "biome",
    ],
)


col_frp = localizar_coluna(
    df.columns,
    [
        "frp",
    ],
)


col_risco = localizar_coluna(
    df.columns,
    [
        "riscofogo",
        "risco_fogo",
    ],
)


col_precipitacao = localizar_coluna(
    df.columns,
    [
        "precipitacao",
        "precipitation",
    ],
)


col_dias_sem_chuva = localizar_coluna(
    df.columns,
    [
        "diasemchuva",
        "dia_sem_chuva",
        "dias_sem_chuva",
    ],
)

print("\nColunas detectadas pelo ETL:")
print("Data:", col_data)
print("Satélite:", col_satelite)
print("Latitude:", col_latitude)
print("Longitude:", col_longitude)

if (
    col_data is None
    or col_satelite is None
    or col_latitude is None
    or col_longitude is None
):

    raise ValueError(
        "Colunas essenciais do INPE não encontradas."
    )


# ============================================================
# DATAS
# ============================================================

df["data_hora"] = pd.to_datetime(
    df[col_data],
    errors="coerce",
    utc=True,
)


df = df[
    df["data_hora"].notna()
].copy()


df["ano"] = (
    df["data_hora"]
    .dt.year
)


df = df[
    df["ano"].between(
        ANO_INICIAL,
        ANO_FINAL,
    )
].copy()


# ============================================================
# FILTRAR SP
# ============================================================

if col_estado is not None:

    estado = (
        df[col_estado]
        .map(normalizar_nome)
    )

    df = df[
        estado.isin(
            [
                "sao_paulo",
                "sp",
            ]
        )
    ].copy()


# ============================================================
# SATÉLITE DE REFERÊNCIA
# ============================================================

satelite = (
    df[col_satelite]
    .astype(str)
    .str.upper()
    .str.strip()
)


df = df[
    satelite == SATELITE_REFERENCIA
].copy()


print(
    "\nRegistros SP / satélite de referência: "
    f"{len(df):,}"
)


# ============================================================
# COORDENADAS
# ============================================================

df["latitude"] = pd.to_numeric(
    df[col_latitude],
    errors="coerce",
)


df["longitude"] = pd.to_numeric(
    df[col_longitude],
    errors="coerce",
)


df = df[
    df["latitude"].notna()
    &
    df["longitude"].notna()
].copy()


# ============================================================
# GEODATAFRAME
# ============================================================

gdf = gpd.GeoDataFrame(

    df,

    geometry=gpd.points_from_xy(
        df["longitude"],
        df["latitude"],
    ),

    crs="EPSG:4674",
)


# ============================================================
# MUNICÍPIOS DO NOSSO BANCO
# ============================================================

municipios = gpd.read_postgis(

    """
    SELECT
        codigo_ibge,
        nome_municipio,
        geom
    FROM core.dim_municipio
    WHERE uf = 'SP';
    """,

    engine,

    geom_col="geom",
)


# ============================================================
# SPATIAL JOIN
# ============================================================

gdf = gpd.sjoin(

    gdf,

    municipios[
        [
            "codigo_ibge",
            "nome_municipio",
            "geom",
        ]
    ],

    how="left",

    predicate="within",
)


sem_municipio = (
    gdf["codigo_ibge"]
    .isna()
    .sum()
)


print(
    f"Focos sem município: {sem_municipio}"
)


# ============================================================
# CAMPOS NUMÉRICOS
# ============================================================

def converter_numerico(
    dataframe,
    coluna,
):

    if coluna is None:

        return pd.Series(
            None,
            index=dataframe.index,
        )

    return pd.to_numeric(
        dataframe[coluna],
        errors="coerce",
    )


gdf["frp"] = converter_numerico(
    gdf,
    col_frp,
)


gdf["risco_fogo"] = converter_numerico(
    gdf,
    col_risco,
)


gdf["precipitacao"] = converter_numerico(
    gdf,
    col_precipitacao,
)


gdf["dia_sem_chuva"] = converter_numerico(
    gdf,
    col_dias_sem_chuva,
)


# ============================================================
# RAW FINAL
# ============================================================

raw_df = gdf[
    [
        "data_hora",
        col_satelite,
        col_estado,
        "codigo_ibge",
        "nome_municipio",
        "ano",
        "latitude",
        "longitude",
        "dia_sem_chuva",
        "precipitacao",
        "risco_fogo",
        "frp",
        "geometry",
        "arquivo_origem",
    ]
].copy()


raw_df = raw_df.rename(
    columns={
        col_satelite:
            "satelite",

        col_estado:
            "estado",

        "nome_municipio":
            "municipio",

        "geometry":
            "geom",
    }
)

raw_df = gpd.GeoDataFrame(
    raw_df,
    geometry="geom",
    crs=gdf.crs,
)


raw_df["pais"] = "Brasil"

raw_df["satelite_referencia"] = True


if col_bioma is not None:

    raw_df["bioma"] = (
        gdf[col_bioma]
    )

else:

    raw_df["bioma"] = None


# ============================================================
# CARGA POSTGIS
# ============================================================

print(
    "\nCarregando raw.inpe_foco_queimada..."
)


with engine.begin() as conn:

    conn.execute(
        text("""
        DELETE
        FROM raw.inpe_foco_queimada
        WHERE ano BETWEEN 2015 AND 2024
          AND satelite_referencia = TRUE;
        """)
    )


raw_df.to_postgis(

    name="inpe_foco_queimada",

    schema="raw",

    con=engine,

    if_exists="append",

    index=False,

    chunksize=5000,
)

print("\nGeoDataFrame RAW:")
print("Geometria ativa:", raw_df.geometry.name)
print("CRS:", raw_df.crs)
print("Registros:", len(raw_df))

print("\nETL INPE finalizado.")