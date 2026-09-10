import os

from pathlib import Path

import numpy as np
import pandas as pd

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL
from sqlalchemy import text


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

ANO_REFERENCIA = 2024

ANO_COBERTURA = 2025
ANO_FOGO = 2024
ANO_INPE = 2024

VERSAO_FEATURES = "v1.0"


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
# FUNÇÕES DE SCORE
# ============================================================

def score_maior_pior(
    serie,
    zero_sem_pressao=False,
):
    """
    Transforma a variável em score relativo 0-100.

    Maior valor bruto = maior pressão.
    """

    serie = pd.to_numeric(
        serie,
        errors="coerce",
    )

    n = serie.notna().sum()

    if n <= 1:

        return pd.Series(
            np.nan,
            index=serie.index,
        )

    ranking = serie.rank(
        method="average",
        ascending=True,
    )

    score = (
        (ranking - 1)
        /
        (n - 1)
        *
        100
    )

    if zero_sem_pressao:

        score = score.mask(
            serie <= 0,
            0,
        )

    return score.clip(
        lower=0,
        upper=100,
    )


def score_menor_pior(
    serie,
):
    """
    Menor valor bruto = maior pressão.

    Exemplo:
    cobertura natural.
    """

    score = (
        100
        -
        score_maior_pior(
            serie
        )
    )

    return score.clip(
        lower=0,
        upper=100,
    )


# ============================================================
# EXTRAÇÃO
# ============================================================

sql = """
SELECT
    m.codigo_ibge,
    m.nome_municipio,
    m.area_km2,

    i.vegetacao_nativa_pct,
    i.agropecuaria_pct,
    i.variacao_liquida_vegetacao_ha_10a,

    f.media_anual_queimada_5a_pct,
    f.carga_fogo_10a_pct,

    COALESCE(
        inp.focos_por_100_km2,
        0
    ) AS focos_inpe_100km2

FROM core.dim_municipio m

LEFT JOIN analytics.indicador_municipio i
    ON i.codigo_ibge = m.codigo_ibge
    AND i.ano = %(ano_cobertura)s

LEFT JOIN analytics.fogo_municipio f
    ON f.codigo_ibge = m.codigo_ibge
    AND f.ano_referencia = %(ano_fogo)s

LEFT JOIN staging.inpe_fogo_municipio_ano inp
    ON inp.codigo_ibge = m.codigo_ibge
    AND inp.ano = %(ano_inpe)s

WHERE m.uf = 'SP'

ORDER BY m.codigo_ibge;
"""


df = pd.read_sql(
    sql,
    engine,
    params={
        "ano_cobertura": ANO_COBERTURA,
        "ano_fogo": ANO_FOGO,
        "ano_inpe": ANO_INPE,
    },
)

# ============================================================
# VALIDAÇÕES
# ============================================================

if len(df) != 645:

    raise ValueError(
        f"Esperávamos 645 municípios, "
        f"mas encontramos {len(df)}."
    )


if df["codigo_ibge"].duplicated().any():

    raise ValueError(
        "Existem municípios duplicados."
    )


colunas_criticas = [

    "vegetacao_nativa_pct",

    "agropecuaria_pct",

    "variacao_liquida_vegetacao_ha_10a",

    "media_anual_queimada_5a_pct",

    "carga_fogo_10a_pct",
]


nulos = (
    df[colunas_criticas]
    .isna()
    .sum()
)


print("\nValores nulos:")

print(
    nulos.to_string()
)


if nulos.sum() > 0:

    raise ValueError(
        "Existem valores faltantes nas "
        "variáveis ambientais críticas."
    )


# ============================================================
# FEATURE 1
# COBERTURA NATURAL
# ============================================================

df["cobertura_natural_pct"] = (
    df["vegetacao_nativa_pct"]
)


# ============================================================
# FEATURE 2
# PERDA LÍQUIDA DE VEGETAÇÃO
# ============================================================

df["area_municipio_ha"] = (
    df["area_km2"]
    *
    100
)


# Variação negativa significa redução.
#
# Exemplo:
#
# 2015 -> 5.000 ha
# 2024 -> 4.000 ha
#
# variação = -1.000 ha
#
# perda = +1.000 ha


df["perda_liquida_vegetacao_10a_ha"] = (

    -df[
        "variacao_liquida_vegetacao_ha_10a"
    ]

).clip(
    lower=0
)


df[
    "perda_liquida_vegetacao_10a_pct"
] = (

    df[
        "perda_liquida_vegetacao_10a_ha"
    ]

    /

    df["area_municipio_ha"]

    *

    100
)


# ============================================================
# FEATURE 3
# PRESSÃO AGROPECUÁRIA
# ============================================================

df["agropecuaria_pct"] = (
    df["agropecuaria_pct"]
)


# ============================================================
# FEATURES DE FOGO
# ============================================================

df["fogo_media_5a_pct"] = (
    df["media_anual_queimada_5a_pct"]
)


df["fogo_carga_10a_pct"] = (
    df["carga_fogo_10a_pct"]
)


# ============================================================
# SCORES 0-100
# ============================================================

df["score_baixa_cobertura"] = (

    score_menor_pior(
        df["cobertura_natural_pct"]
    )
)


df["score_perda_vegetacao"] = (

    score_maior_pior(

        df[
            "perda_liquida_vegetacao_10a_pct"
        ],

        zero_sem_pressao=True,
    )
)


df["score_pressao_agropecuaria"] = (

    score_maior_pior(
        df["agropecuaria_pct"]
    )
)


df["score_fogo_media_5a"] = (

    score_maior_pior(

        df["fogo_media_5a_pct"],

        zero_sem_pressao=True,
    )
)


df["score_fogo_carga_10a"] = (

    score_maior_pior(

        df["fogo_carga_10a_pct"],

        zero_sem_pressao=True,
    )
)


df["score_focos_inpe"] = (

    score_maior_pior(

        df["focos_inpe_100km2"],

        zero_sem_pressao=True,
    )
)


# ============================================================
# RESUMO ESTATÍSTICO
# ============================================================

variaveis = [

    "cobertura_natural_pct",

    "perda_liquida_vegetacao_10a_pct",

    "agropecuaria_pct",

    "fogo_media_5a_pct",

    "fogo_carga_10a_pct",

    "focos_inpe_100km2",
]


resumo = (

    df[variaveis]

    .describe(

        percentiles=[
            0.05,
            0.10,
            0.25,
            0.50,
            0.75,
            0.90,
            0.95,
        ]

    )

    .T
)


print("\n" + "=" * 70)
print("RESUMO ESTATÍSTICO")
print("=" * 70)

print(
    resumo.to_string()
)


# ============================================================
# OUTLIERS - MÉTODO IQR
# ============================================================

outliers = []


for coluna in variaveis:

    q1 = df[coluna].quantile(
        0.25
    )

    q3 = df[coluna].quantile(
        0.75
    )

    iqr = q3 - q1

    limite_inferior = (
        q1
        -
        1.5
        *
        iqr
    )

    limite_superior = (
        q3
        +
        1.5
        *
        iqr
    )


    quantidade = (

        (
            df[coluna]
            <
            limite_inferior
        )

        |

        (
            df[coluna]
            >
            limite_superior
        )

    ).sum()


    outliers.append(

        {
            "variavel":
                coluna,

            "q1":
                q1,

            "q3":
                q3,

            "iqr":
                iqr,

            "limite_inferior":
                limite_inferior,

            "limite_superior":
                limite_superior,

            "quantidade_outliers":
                quantidade,
        }

    )


outliers_df = pd.DataFrame(
    outliers
)


print("\n" + "=" * 70)
print("DIAGNÓSTICO DE OUTLIERS")
print("=" * 70)

print(
    outliers_df.to_string(
        index=False
    )
)


# ============================================================
# CORRELAÇÃO DE SPEARMAN
# ============================================================

# Spearman equivale à correlação de Pearson
# aplicada aos rankings.

rank_df = (
    df[variaveis]
    .rank()
)


correlacao = (
    rank_df
    .corr(
        method="pearson"
    )
)


print("\n" + "=" * 70)
print("CORRELAÇÃO DE SPEARMAN")
print("=" * 70)

print(
    correlacao.round(3)
)


# ============================================================
# PREPARAR TABELA FINAL
# ============================================================

features = df[
    [

        "codigo_ibge",

        "cobertura_natural_pct",

        "perda_liquida_vegetacao_10a_pct",

        "agropecuaria_pct",

        "fogo_media_5a_pct",

        "fogo_carga_10a_pct",

        "focos_inpe_100km2",

        "score_baixa_cobertura",

        "score_perda_vegetacao",

        "score_pressao_agropecuaria",

        "score_fogo_media_5a",

        "score_fogo_carga_10a",

        "score_focos_inpe",
    ]
].copy()


features["ano_referencia"] = (
    ANO_REFERENCIA
)


features["versao_features"] = (
    VERSAO_FEATURES
)


# ============================================================
# SALVAR RELATÓRIOS
# ============================================================

OUTPUT_DIR = (

    ROOT_DIR
    / "outputs"
    / "reports"
    / "module6"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


df.to_csv(

    OUTPUT_DIR
    / "features_ambientais_2024.csv",

    index=False,

    encoding="utf-8-sig",
)


resumo.to_csv(

    OUTPUT_DIR
    / "resumo_estatistico_2024.csv",

    encoding="utf-8-sig",
)


outliers_df.to_csv(

    OUTPUT_DIR
    / "outliers_2024.csv",

    index=False,

    encoding="utf-8-sig",
)


correlacao.to_csv(

    OUTPUT_DIR
    / "correlacao_spearman_2024.csv",

    encoding="utf-8-sig",
)


# ============================================================
# STAGING TEMPORÁRIO
# ============================================================

features.to_sql(

    name="feature_municipio_temp",

    schema="staging",

    con=engine,

    if_exists="replace",

    index=False,
)


# ============================================================
# UPSERT ANALYTICS
# ============================================================

sql_upsert = """
INSERT INTO analytics.feature_municipio (

    codigo_ibge,

    ano_referencia,

    versao_features,

    cobertura_natural_pct,

    perda_liquida_vegetacao_10a_pct,

    agropecuaria_pct,

    fogo_media_5a_pct,

    fogo_carga_10a_pct,

    focos_inpe_100km2,

    score_baixa_cobertura,

    score_perda_vegetacao,

    score_pressao_agropecuaria,

    score_fogo_media_5a,

    score_fogo_carga_10a,

    score_focos_inpe

)

SELECT

    codigo_ibge,

    ano_referencia,

    versao_features,

    cobertura_natural_pct,

    perda_liquida_vegetacao_10a_pct,

    agropecuaria_pct,

    fogo_media_5a_pct,

    fogo_carga_10a_pct,

    focos_inpe_100km2,

    score_baixa_cobertura,

    score_perda_vegetacao,

    score_pressao_agropecuaria,

    score_fogo_media_5a,

    score_fogo_carga_10a,

    score_focos_inpe

FROM staging.feature_municipio_temp

ON CONFLICT (

    codigo_ibge,

    ano_referencia,

    versao_features

)

DO UPDATE SET

    cobertura_natural_pct =
        EXCLUDED.cobertura_natural_pct,

    perda_liquida_vegetacao_10a_pct =
        EXCLUDED.perda_liquida_vegetacao_10a_pct,

    agropecuaria_pct =
        EXCLUDED.agropecuaria_pct,

    fogo_media_5a_pct =
        EXCLUDED.fogo_media_5a_pct,

    fogo_carga_10a_pct =
        EXCLUDED.fogo_carga_10a_pct,

    focos_inpe_100km2 =
        EXCLUDED.focos_inpe_100km2,

    score_baixa_cobertura =
        EXCLUDED.score_baixa_cobertura,

    score_perda_vegetacao =
        EXCLUDED.score_perda_vegetacao,

    score_pressao_agropecuaria =
        EXCLUDED.score_pressao_agropecuaria,

    score_fogo_media_5a =
        EXCLUDED.score_fogo_media_5a,

    score_fogo_carga_10a =
        EXCLUDED.score_fogo_carga_10a,

    score_focos_inpe =
        EXCLUDED.score_focos_inpe,

    data_calculo =
        CURRENT_TIMESTAMP;
"""


with engine.begin() as conn:

    conn.execute(
        text(sql_upsert)
    )

    conn.execute(
        text("""
            DROP TABLE IF EXISTS
            staging.feature_municipio_temp;
        """)
    )


print("\n" + "=" * 70)

print(
    "FEATURES AMBIENTAIS CRIADAS COM SUCESSO"
)

print("=" * 70)

