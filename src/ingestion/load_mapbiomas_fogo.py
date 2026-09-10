from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL, text


BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(
    BASE_DIR / ".env",
    override=True,
)


arquivo = (
    BASE_DIR
    / "data"
    / "processed"
    / "mapbiomas"
    / "fire_collection5"
    / "mapbiomas_fogo_col5_sp_municipio_1985_2025_long.csv"
)


print("=" * 70)
print("VERDEPRIORIZA - CARGA MAPBIOMAS FOGO")
print("=" * 70)

print("\nArquivo:")
print(arquivo)


df = pd.read_csv(
    arquivo,
    dtype={
        "codigo_ibge": str,
        "municipio": str,
        "ano": int,
    },
)


df["codigo_ibge"] = (
    df["codigo_ibge"]
    .astype(str)
    .str.zfill(7)
)

df["colecao"] = "5"


print(f"\nRegistros para carga: {len(df):,}")
print(
    "Municípios:",
    df["codigo_ibge"].nunique(),
)
print(
    "Período:",
    df["ano"].min(),
    "-",
    df["ano"].max(),
)


url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 5433)),
    database=os.getenv("DB_NAME"),
)

engine = create_engine(url)


# Remove somente a Coleção 5 antes de recarregar.
# Isso permite executar o ETL novamente sem duplicar registros.
with engine.begin() as conn:

    conn.execute(
        text("""
            DELETE
            FROM staging.mapbiomas_fogo_municipio_ano
            WHERE colecao = '5';
        """)
    )


df.to_sql(
    name="mapbiomas_fogo_municipio_ano",
    con=engine,
    schema="staging",
    if_exists="append",
    index=False,
    chunksize=5000,
    method="multi",
)


print("\nCarga concluída.")


with engine.connect() as conn:

    resultado = conn.execute(
        text("""
            SELECT
                MIN(ano) AS primeiro_ano,
                MAX(ano) AS ultimo_ano,
                COUNT(DISTINCT ano) AS quantidade_anos,
                COUNT(DISTINCT codigo_ibge) AS municipios,
                COUNT(*) AS registros
            FROM staging.mapbiomas_fogo_municipio_ano
            WHERE colecao = '5';
        """)
    ).fetchone()


print("\nValidação no PostgreSQL:")
print(resultado)