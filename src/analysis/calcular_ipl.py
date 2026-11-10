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

VERSAO_IPA = "ipa_v1.0_2024"

VERSAO_IPL = "ipl_v1.0_2024"


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
# DADOS
# ============================================================

sql = """
SELECT

    c.id_celula,

    c.codigo_ibge,

    m.nome_municipio,

    c.area_ha,

    c.score_hidrologia,

    c.score_conectividade,

    c.score_declividade,

    c.score_elegibilidade,

    c.pct_vegetacao_natural,

    c.pct_uso_elegivel,

    c.vegetacao_entorno_pct,

    c.distancia_drenagem_m,

    c.declividade_media_pct,

    c.uso_predominante,

    i.ipa

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m
    ON m.codigo_ibge = c.codigo_ibge

JOIN analytics.ipa_municipio i
    ON i.codigo_ibge = c.codigo_ibge
    AND i.ano_referencia = 2024
    AND i.versao_modelo = 'ipa_v1.0_2024'

WHERE

    -- qualidade mínima da célula

    c.area_ha >= 1

    AND c.pixels_validos >= 10

    -- funil territorial

    AND c.pct_uso_elegivel >= 30

    AND c.pct_area_urbanizada < 20

    AND c.pct_agua < 50

    -- quatro componentes completos

    AND c.score_hidrologia IS NOT NULL

    AND c.score_conectividade IS NOT NULL

    AND c.score_declividade IS NOT NULL

    AND c.score_elegibilidade IS NOT NULL

ORDER BY
    c.codigo_ibge,
    c.id_celula;
"""


df = pd.read_sql(
    sql,
    engine,
)


print("=" * 72)
print("VERDEPRIORIZA - IPL")
print("=" * 72)

print(
    f"\nCélulas carregadas: {len(df):,}"
)

print(
    f"Municípios: "
    f"{df['codigo_ibge'].nunique()}"
)


if df.empty:

    raise ValueError(
        "Nenhuma célula disponível para cálculo."
    )


# ============================================================
# VALIDAÇÕES
# ============================================================

componentes = [

    "score_hidrologia",

    "score_conectividade",

    "score_declividade",

    "score_elegibilidade",
]


for coluna in componentes:

    if df[coluna].isna().any():

        raise ValueError(
            f"Existem valores nulos em {coluna}."
        )


    if (
        (df[coluna] < 0).any()
        or
        (df[coluna] > 100).any()
    ):

        raise ValueError(
            f"{coluna} possui valores fora de 0-100."
        )


# ============================================================
# CORRELAÇÃO ENTRE COMPONENTES
# ============================================================

correlacao = (

    df[componentes]

    .rank()

    .corr()
)


print("\n" + "=" * 72)
print("CORRELAÇÃO DE SPEARMAN ENTRE COMPONENTES")
print("=" * 72)

print(
    correlacao.round(3)
)


# ============================================================
# IPL PRINCIPAL
#
# H = 35%
# C = 25%
# S = 20%
# E = 20%
# ============================================================

df["prioridade_local"] = (

    0.35
    *
    df["score_hidrologia"]

    +

    0.25
    *
    df["score_conectividade"]

    +

    0.20
    *
    df["score_declividade"]

    +

    0.20
    *
    df["score_elegibilidade"]
)


# ============================================================
# CENÁRIO HIDROLÓGICO
#
# H = 50%
# C = 20%
# S = 15%
# E = 15%
# ============================================================

df["ipl_cenario_hidrologico"] = (

    0.50
    *
    df["score_hidrologia"]

    +

    0.20
    *
    df["score_conectividade"]

    +

    0.15
    *
    df["score_declividade"]

    +

    0.15
    *
    df["score_elegibilidade"]
)


# ============================================================
# CENÁRIO PAISAGEM
#
# H = 25%
# C = 40%
# S = 15%
# E = 20%
# ============================================================

df["ipl_cenario_paisagem"] = (

    0.25
    *
    df["score_hidrologia"]

    +

    0.40
    *
    df["score_conectividade"]

    +

    0.15
    *
    df["score_declividade"]

    +

    0.20
    *
    df["score_elegibilidade"]
)


# ============================================================
# SENSIBILIDADE
# ============================================================

cenarios = [

    "prioridade_local",

    "ipl_cenario_hidrologico",

    "ipl_cenario_paisagem",
]


df["ipl_media_cenarios"] = (

    df[cenarios]
    .mean(
        axis=1
    )
)


df["amplitude_ipl"] = (

    df[cenarios]
    .max(
        axis=1
    )

    -

    df[cenarios]
    .min(
        axis=1
    )
)


# ============================================================
# RANKING DOS TRÊS CENÁRIOS
# DENTRO DE CADA MUNICÍPIO
# ============================================================

df["rank_principal_temp"] = (

    df.groupby(
        "codigo_ibge"
    )[
        "prioridade_local"
    ]

    .rank(
        method="min",
        ascending=False,
    )
)


df["rank_hidro_temp"] = (

    df.groupby(
        "codigo_ibge"
    )[
        "ipl_cenario_hidrologico"
    ]

    .rank(
        method="min",
        ascending=False,
    )
)


df["rank_paisagem_temp"] = (

    df.groupby(
        "codigo_ibge"
    )[
        "ipl_cenario_paisagem"
    ]

    .rank(
        method="min",
        ascending=False,
    )
)


ranks_cenarios = [

    "rank_principal_temp",

    "rank_hidro_temp",

    "rank_paisagem_temp",
]


df["amplitude_rank_local"] = (

    df[ranks_cenarios]
    .max(
        axis=1
    )

    -

    df[ranks_cenarios]
    .min(
        axis=1
    )
)


# ============================================================
# ESTABILIDADE
# ============================================================

df["estabilidade_ipl"] = np.select(

    [

        df["amplitude_ipl"] <= 5,

        df["amplitude_ipl"] <= 10,

    ],

    [

        "Alta",

        "Media",

    ],

    default="Baixa",
)


# ============================================================
# PRIORIDADE INTEGRADA
#
# 75% IPL
# 25% IPA MUNICIPAL
# ============================================================

df["prioridade_integrada"] = (

    0.75
    *
    df["prioridade_local"]

    +

    0.25
    *
    df["ipa"]
)


# ============================================================
# RANKINGS
# ============================================================

df["rank_ipl_municipio"] = (

    df.groupby(
        "codigo_ibge"
    )[
        "prioridade_local"
    ]

    .rank(
        method="min",
        ascending=False,
    )

    .astype(int)
)


df["rank_integrada_municipio"] = (

    df.groupby(
        "codigo_ibge"
    )[
        "prioridade_integrada"
    ]

    .rank(
        method="min",
        ascending=False,
    )

    .astype(int)
)


df["rank_integrada_geral"] = (

    df["prioridade_integrada"]

    .rank(
        method="min",
        ascending=False,
    )

    .astype(int)
)


# ============================================================
# CLASSIFICAÇÕES
# ============================================================

def classificar(valor):

    if valor <= 20:
        return "Muito baixa"

    if valor <= 40:
        return "Baixa"

    if valor <= 60:
        return "Media"

    if valor <= 80:
        return "Alta"

    return "Muito alta"


df["classificacao_ipl"] = (

    df["prioridade_local"]
    .apply(
        classificar
    )
)


df["classificacao_integrada"] = (

    df["prioridade_integrada"]
    .apply(
        classificar
    )
)


df["versao_ipl"] = (
    VERSAO_IPL
)


# ============================================================
# ARREDONDAMENTO
# ============================================================

colunas_round = [

    "prioridade_local",

    "ipl_cenario_hidrologico",

    "ipl_cenario_paisagem",

    "ipl_media_cenarios",

    "amplitude_ipl",

    "prioridade_integrada",
]


df[colunas_round] = (

    df[colunas_round]
    .round(2)
)


df["amplitude_rank_local"] = (

    df["amplitude_rank_local"]
    .round()
    .astype(int)
)


# ============================================================
# RESUMO
# ============================================================

print("\n" + "=" * 72)
print("RESUMO IPL")
print("=" * 72)


print(

    df["prioridade_local"]

    .describe()

    .round(2)
)


print("\nClassificação IPL:")

print(

    df["classificacao_ipl"]

    .value_counts()
)


print("\nEstabilidade:")

print(

    df["estabilidade_ipl"]

    .value_counts()
)


# ============================================================
# TOP 20 GERAL
# ============================================================

top20 = (

    df

    .sort_values(
        "prioridade_integrada",
        ascending=False,
    )

    .head(20)
)


print("\n" + "=" * 72)
print("TOP 20 - PRIORIDADE INTEGRADA")
print("=" * 72)


print(

    top20[
        [

            "rank_integrada_geral",

            "nome_municipio",

            "id_celula",

            "prioridade_local",

            "ipa",

            "prioridade_integrada",

            "estabilidade_ipl",

            "uso_predominante",

        ]
    ]

    .to_string(
        index=False
    )
)


# ============================================================
# ARQUIVOS
# ============================================================

OUTPUT_DIR = (

    ROOT_DIR
    / "outputs"
    / "reports"
    / "module9e"
)


OUTPUT_DIR.mkdir(

    parents=True,

    exist_ok=True,
)


df.to_csv(

    OUTPUT_DIR
    / "ipl_celulas_2024.csv",

    index=False,

    encoding="utf-8-sig",
)


top20.to_csv(

    OUTPUT_DIR
    / "top20_prioridade_integrada_2024.csv",

    index=False,

    encoding="utf-8-sig",
)


correlacao.to_csv(

    OUTPUT_DIR
    / "correlacao_componentes_ipl_2024.csv",

    encoding="utf-8-sig",
)


# ============================================================
# STAGING
# ============================================================

resultado = df[
    [

        "id_celula",

        "prioridade_local",

        "prioridade_integrada",

        "ipl_cenario_hidrologico",

        "ipl_cenario_paisagem",

        "ipl_media_cenarios",

        "amplitude_ipl",

        "rank_ipl_municipio",

        "rank_integrada_municipio",

        "rank_integrada_geral",

        "amplitude_rank_local",

        "estabilidade_ipl",

        "classificacao_ipl",

        "classificacao_integrada",

        "versao_ipl",

    ]
].copy()


resultado.to_sql(

    name="ipl_celula_temp",

    schema="staging",

    con=engine,

    if_exists="replace",

    index=False,
)


# ============================================================
# UPDATE
# ============================================================

sql_update = """

UPDATE spatial.celula_prioridade c

SET

    prioridade_local =
        t.prioridade_local,

    prioridade_integrada =
        t.prioridade_integrada,

    ipl_cenario_hidrologico =
        t.ipl_cenario_hidrologico,

    ipl_cenario_paisagem =
        t.ipl_cenario_paisagem,

    ipl_media_cenarios =
        t.ipl_media_cenarios,

    amplitude_ipl =
        t.amplitude_ipl,

    rank_ipl_municipio =
        t.rank_ipl_municipio,

    rank_integrada_municipio =
        t.rank_integrada_municipio,

    rank_integrada_geral =
        t.rank_integrada_geral,

    amplitude_rank_local =
        t.amplitude_rank_local,

    estabilidade_ipl =
        t.estabilidade_ipl,

    classificacao_ipl =
        t.classificacao_ipl,

    classificacao_integrada =
        t.classificacao_integrada,

    versao_ipl =
        t.versao_ipl,

    data_calculo =
        CURRENT_TIMESTAMP

FROM staging.ipl_celula_temp t

WHERE
    c.id_celula =
    t.id_celula;

"""


with engine.begin() as conn:

    conn.execute(
        text(
            sql_update
        )
    )

    conn.execute(

        text("""
        DROP TABLE IF EXISTS
        staging.ipl_celula_temp;
        """)

    )


print("\n" + "=" * 72)
print("IPL E PRIORIDADE INTEGRADA CALCULADOS COM SUCESSO")
print("=" * 72)