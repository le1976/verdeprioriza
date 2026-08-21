import os
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

from shapely.geometry import MultiPolygon

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL
from sqlalchemy import text

from geoalchemy2 import Geometry


# =====================================================
# CONFIGURAÇÕES
# =====================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

ARQUIVO_ZIP = (
    ROOT_DIR
    / "data"
    / "raw"
    / "ibge"
    / "2025"
    / "SP_Municipios_2025.zip"
)

PASTA_EXTRAIDA = (
    ROOT_DIR
    / "data"
    / "raw"
    / "ibge"
    / "2025"
    / "SP_Municipios_2025"
)


# =====================================================
# CONEXÃO COM O BANCO
# =====================================================

load_dotenv(ROOT_DIR / ".env")

url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 5432)),
    database=os.getenv("DB_NAME"),
)

engine = create_engine(url)


# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================

def localizar_coluna(colunas, candidatos):
    """
    Localiza uma coluna considerando diferentes nomes
    utilizados pelo IBGE ao longo das edições.
    """

    for candidato in candidatos:
        if candidato in colunas:
            return candidato

    return None


def converter_multipolygon(geom):
    """
    Garante que geometrias Polygon sejam convertidas
    para MultiPolygon.
    """

    if geom is None:
        return None

    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])

    if geom.geom_type == "MultiPolygon":
        return geom

    raise ValueError(
        f"Tipo de geometria inesperado: {geom.geom_type}"
    )


# =====================================================
# 1. EXTRAÇÃO
# =====================================================

print("=" * 60)
print("VERDEPRIORIZA - ETL IBGE")
print("=" * 60)

if not ARQUIVO_ZIP.exists():
    raise FileNotFoundError(
        f"Arquivo não encontrado:\n{ARQUIVO_ZIP}"
    )

print("\n[1/7] Arquivo ZIP localizado.")


PASTA_EXTRAIDA.mkdir(
    parents=True,
    exist_ok=True
)

with zipfile.ZipFile(ARQUIVO_ZIP, "r") as zip_ref:
    zip_ref.extractall(PASTA_EXTRAIDA)

print("[2/7] Arquivo descompactado.")


# =====================================================
# 2. LOCALIZAR SHAPEFILE
# =====================================================

shapefiles = list(
    PASTA_EXTRAIDA.rglob("*.shp")
)

if len(shapefiles) == 0:
    raise FileNotFoundError(
        "Nenhum arquivo .shp encontrado."
    )

arquivo_shp = shapefiles[0]

print(f"[3/7] Shapefile encontrado: {arquivo_shp.name}")


# =====================================================
# 3. LEITURA
# =====================================================

gdf = gpd.read_file(arquivo_shp)

print("\nColunas encontradas:")

for coluna in gdf.columns:
    print(f" - {coluna}")

print(f"\nCRS original: {gdf.crs}")
print(f"Registros encontrados: {len(gdf)}")


# =====================================================
# 4. IDENTIFICAÇÃO DAS COLUNAS
# =====================================================

col_codigo = localizar_coluna(
    gdf.columns,
    [
        "CD_MUN",
        "CD_GEOCMU",
        "CD_GEOCODI",
    ],
)

col_nome = localizar_coluna(
    gdf.columns,
    [
        "NM_MUN",
        "NM_MUNICIP",
        "NM_MUNICIPIO",
    ],
)

col_uf = localizar_coluna(
    gdf.columns,
    [
        "SIGLA_UF",
        "UF",
    ],
)

col_area = localizar_coluna(
    gdf.columns,
    [
        "AREA_KM2",
        "AREA_KM",
    ],
)


if col_codigo is None:
    raise ValueError(
        "Não foi possível identificar a coluna do código IBGE."
    )

if col_nome is None:
    raise ValueError(
        "Não foi possível identificar a coluna do nome do município."
    )


# =====================================================
# 5. TRANSFORMAÇÃO
# =====================================================

# Garantir SIRGAS 2000 - EPSG:4674
if gdf.crs is None:
    raise ValueError(
        "O arquivo não possui sistema de coordenadas definido."
    )

if gdf.crs.to_epsg() != 4674:
    print("\nConvertendo CRS para EPSG:4674...")
    gdf = gdf.to_crs(epsg=4674)


# Código IBGE
gdf["codigo_ibge"] = (
    gdf[col_codigo]
    .astype(str)
    .str.strip()
    .str.zfill(7)
)


# Nome
gdf["nome_municipio"] = (
    gdf[col_nome]
    .astype(str)
    .str.strip()
)


# UF
if col_uf is not None:
    gdf["uf"] = (
        gdf[col_uf]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    gdf = gdf[
        gdf["uf"] == "SP"
    ].copy()

else:
    gdf["uf"] = "SP"


# Área
if col_area is not None:

    gdf["area_km2"] = pd.to_numeric(
        gdf[col_area],
        errors="coerce",
    )

else:

    print(
        "\nAREA_KM2 não encontrada."
        " Calculando área como alternativa."
    )

    gdf_projetado = gdf.to_crs(
        epsg=5880
    )

    gdf["area_km2"] = (
        gdf_projetado.geometry.area
        / 1_000_000
    )


# =====================================================
# GEOMETRIA
# =====================================================

if gdf.geometry.isna().any():
    raise ValueError(
        "Existem municípios sem geometria."
    )


geometrias_invalidas = (
    ~gdf.geometry.is_valid
).sum()

if geometrias_invalidas > 0:
    raise ValueError(
        f"Foram encontradas "
        f"{geometrias_invalidas} "
        f"geometrias inválidas."
    )


gdf["geometry"] = (
    gdf.geometry
    .apply(converter_multipolygon)
)


# =====================================================
# SELEÇÃO FINAL
# =====================================================

gdf = gdf[
    [
        "codigo_ibge",
        "nome_municipio",
        "uf",
        "area_km2",
        "geometry",
    ]
].copy()


# =====================================================
# 6. VALIDAÇÕES
# =====================================================

print("\nExecutando validações...")


quantidade = len(gdf)

print(
    f"Municípios encontrados: {quantidade}"
)


if quantidade != 645:
    raise ValueError(
        f"Esperávamos 645 municípios, "
        f"mas encontramos {quantidade}."
    )


duplicados = (
    gdf["codigo_ibge"]
    .duplicated()
    .sum()
)

if duplicados > 0:
    raise ValueError(
        f"Foram encontrados "
        f"{duplicados} códigos IBGE duplicados."
    )


if gdf["codigo_ibge"].isna().any():
    raise ValueError(
        "Existem códigos IBGE nulos."
    )


print("Validações concluídas com sucesso.")


# =====================================================
# 7. CARGA - STAGING
# =====================================================

print(
    "\n[6/7] Gravando staging.ibge_municipio_sp..."
)


gdf = gdf.rename_geometry(
    "geom"
)


gdf.to_postgis(
    name="ibge_municipio_sp",
    con=engine,
    schema="staging",
    if_exists="replace",
    index=False,
    dtype={
        "geom": Geometry(
            geometry_type="MULTIPOLYGON",
            srid=4674,
        )
    },
)


# =====================================================
# 8. UPSERT NA TABELA CORE
# =====================================================

sql_upsert = """
INSERT INTO core.dim_municipio (
    codigo_ibge,
    nome_municipio,
    uf,
    area_km2,
    geom,
    data_carga
)

SELECT
    codigo_ibge,
    nome_municipio,
    uf,
    area_km2,
    ST_Multi(geom)::geometry(MULTIPOLYGON, 4674),
    CURRENT_TIMESTAMP

FROM staging.ibge_municipio_sp

ON CONFLICT (codigo_ibge)

DO UPDATE SET
    nome_municipio = EXCLUDED.nome_municipio,
    uf = EXCLUDED.uf,
    area_km2 = EXCLUDED.area_km2,
    geom = EXCLUDED.geom,
    data_carga = CURRENT_TIMESTAMP;
"""


with engine.begin() as conn:

    conn.execute(
        text(sql_upsert)
    )


print(
    "[7/7] Dados carregados em core.dim_municipio."
)


print("\n" + "=" * 60)
print("ETL FINALIZADO COM SUCESSO")
print("=" * 60)