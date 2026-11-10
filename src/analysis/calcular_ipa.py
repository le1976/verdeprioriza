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

VERSAO_FEATURES = "v1.0"

VERSAO_MODELO = "ipa_v1.0_2024"


# ============================================================
# CONEXÃO
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
# EXTRAÇÃO DAS FEATURES
# ============================================================

sql = """
SELECT

    f.codigo_ibge,

    m.nome_municipio,

    f.score_baixa_cobertura,

    f.score_perda_vegetacao,

    f.score_pressao_agropecuaria,

    f.score_fogo_media_5a,

    f.score_fogo_carga_10a

FROM analytics.feature_municipio f

JOIN core.dim_municipio m
    ON m.codigo_ibge = f.codigo_ibge

WHERE
    f.ano_referencia = 2024
    AND f.versao_features = 'v1.0'

ORDER BY
    f.codigo_ibge;
"""


df = pd.read_sql(
    sql,
    engine,
)


print("=" * 72)
print("VERDEPRIORIZA - ÍNDICE DE PRIORIDADE AMBIENTAL")
print("ANO DE REFERÊNCIA: 2024")
print("=" * 72)

print(
    f"\nMunicípios carregados: {len(df)}"
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
        "Foram encontrados municípios duplicados."
    )


colunas_score = [

    "score_baixa_cobertura",

    "score_perda_vegetacao",

    "score_pressao_agropecuaria",

    "score_fogo_media_5a",

    "score_fogo_carga_10a",
]


if df[colunas_score].isna().any().any():

    print(
        "\nQuantidade de valores nulos:"
    )

    print(
        df[colunas_score]
        .isna()
        .sum()
    )

    raise ValueError(
        "Existem scores ambientais nulos."
    )


for coluna in colunas_score:

    if (
        (df[coluna] < 0).any()
        or
        (df[coluna] > 100).any()
    ):

        raise ValueError(
            f"O score {coluna} contém "
            "valores fora de 0-100."
        )


print(
    "Validações básicas concluídas."
)


# ============================================================
# CORRELAÇÃO ENTRE OS SCORES
# ============================================================

# Spearman sem depender diretamente do scipy:
# Pearson aplicado aos rankings.

correlacao = (
    df[colunas_score]
    .rank()
    .corr()
)


print("\n" + "=" * 72)
print("CORRELAÇÃO ENTRE SCORES - SPEARMAN")
print("=" * 72)

print(
    correlacao.round(3)
)


# Alerta de possível redundância entre
# cobertura e pressão agropecuária.

rho_cobertura_agro = correlacao.loc[
    "score_baixa_cobertura",
    "score_pressao_agropecuaria",
]


if abs(rho_cobertura_agro) >= 0.85:

    print(
        "\nATENÇÃO:"
        "\nExiste forte associação entre baixa cobertura "
        "e pressão agropecuária."
        f"\nSpearman = {rho_cobertura_agro:.3f}"
        "\nIsso deve ser considerado na interpretação "
        "dos pesos do IPA."
    )


# ============================================================
# DIMENSÃO FOGO
# ============================================================

df["score_fogo"] = (

    0.60
    *
    df["score_fogo_media_5a"]

    +

    0.40
    *
    df["score_fogo_carga_10a"]
)


# ============================================================
# CENÁRIO 1
# EQUILIBRADO - MODELO PRINCIPAL
# ============================================================

df["ipa"] = (

    0.35
    *
    df["score_baixa_cobertura"]

    +

    0.25
    *
    df["score_perda_vegetacao"]

    +

    0.20
    *
    df["score_pressao_agropecuaria"]

    +

    0.20
    *
    df["score_fogo"]
)


# ============================================================
# CENÁRIO 2
# CONSERVAÇÃO
# ============================================================

df["ipa_cenario_conservacao"] = (

    0.45
    *
    df["score_baixa_cobertura"]

    +

    0.30
    *
    df["score_perda_vegetacao"]

    +

    0.10
    *
    df["score_pressao_agropecuaria"]

    +

    0.15
    *
    df["score_fogo"]
)


# ============================================================
# CENÁRIO 3
# DISTÚRBIO RECENTE
# ============================================================

df["ipa_cenario_disturbio"] = (

    0.25
    *
    df["score_baixa_cobertura"]

    +

    0.35
    *
    df["score_perda_vegetacao"]

    +

    0.15
    *
    df["score_pressao_agropecuaria"]

    +

    0.25
    *
    df["score_fogo"]
)


# ============================================================
# ANÁLISE DE SENSIBILIDADE
# ============================================================

colunas_cenarios = [

    "ipa",

    "ipa_cenario_conservacao",

    "ipa_cenario_disturbio",
]


df["ipa_media_cenarios"] = (

    df[colunas_cenarios]
    .mean(
        axis=1
    )
)


df["amplitude_cenarios"] = (

    df[colunas_cenarios]
    .max(
        axis=1
    )

    -

    df[colunas_cenarios]
    .min(
        axis=1
    )
)


# ============================================================
# RANKINGS
# ============================================================

df["rank_ipa"] = (

    df["ipa"]

    .rank(
        method="min",
        ascending=False,
    )

    .astype(int)
)


df["rank_conservacao"] = (

    df["ipa_cenario_conservacao"]

    .rank(
        method="min",
        ascending=False,
    )

    .astype(int)
)


df["rank_disturbio"] = (

    df["ipa_cenario_disturbio"]

    .rank(
        method="min",
        ascending=False,
    )

    .astype(int)
)


colunas_rank = [

    "rank_ipa",

    "rank_conservacao",

    "rank_disturbio",
]


df["amplitude_rank"] = (

    df[colunas_rank]
    .max(
        axis=1
    )

    -

    df[colunas_rank]
    .min(
        axis=1
    )
)


# ============================================================
# ESTABILIDADE
# ============================================================

df["estabilidade"] = np.select(

    [

        df["amplitude_cenarios"] <= 5,

        df["amplitude_cenarios"] <= 10,

    ],

    [

        "Alta",

        "Media",

    ],

    default="Baixa",
)


# ============================================================
# CLASSIFICAÇÃO DO IPA
# ============================================================

def classificar_ipa(valor):

    if valor <= 20:
        return "Muito baixa"

    if valor <= 40:
        return "Baixa"

    if valor <= 60:
        return "Media"

    if valor <= 80:
        return "Alta"

    return "Muito alta"


df["classificacao"] = (

    df["ipa"]
    .apply(
        classificar_ipa
    )
)


# ============================================================
# METADADOS
# ============================================================

df["ano_referencia"] = (
    ANO_REFERENCIA
)


df["versao_modelo"] = (
    VERSAO_MODELO
)


# ============================================================
# ARREDONDAMENTO PARA RELATÓRIO
# ============================================================

colunas_numericas = [

    "score_fogo",

    "ipa",

    "ipa_cenario_conservacao",

    "ipa_cenario_disturbio",

    "ipa_media_cenarios",

    "amplitude_cenarios",
]


df[colunas_numericas] = (

    df[colunas_numericas]
    .round(2)
)


# ============================================================
# RESUMO
# ============================================================

print("\n" + "=" * 72)
print("RESUMO DO IPA")
print("=" * 72)


print(
    df["ipa"]
    .describe()
    .round(2)
)


print("\nClassificações:")

print(
    df["classificacao"]
    .value_counts()
)


print("\nEstabilidade:")

print(
    df["estabilidade"]
    .value_counts()
)


# ============================================================
# TOP 20
# ============================================================

top20 = (

    df

    .sort_values(
        "ipa",
        ascending=False,
    )

    .head(20)
)


print("\n" + "=" * 72)
print("TOP 20 - PRIORIDADE AMBIENTAL")
print("=" * 72)


print(

    top20[
        [
            "rank_ipa",
            "nome_municipio",
            "ipa",
            "classificacao",
            "ipa_cenario_conservacao",
            "ipa_cenario_disturbio",
            "amplitude_rank",
            "estabilidade",
        ]
    ]

    .to_string(
        index=False
    )

)


# ============================================================
# SALVAR RELATÓRIOS
# ============================================================

OUTPUT_DIR = (

    ROOT_DIR
    / "outputs"
    / "reports"
    / "module7"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


df.to_csv(

    OUTPUT_DIR
    / "ipa_municipios_sp_2024.csv",

    index=False,

    encoding="utf-8-sig",
)


top20.to_csv(

    OUTPUT_DIR
    / "top20_ipa_2024.csv",

    index=False,

    encoding="utf-8-sig",
)


df[
    [
        "codigo_ibge",
        "nome_municipio",
        "ipa",
        "ipa_cenario_conservacao",
        "ipa_cenario_disturbio",
        "ipa_media_cenarios",
        "amplitude_cenarios",
        "rank_ipa",
        "rank_conservacao",
        "rank_disturbio",
        "amplitude_rank",
        "estabilidade",
    ]
].to_csv(

    OUTPUT_DIR
    / "sensibilidade_ipa_2024.csv",

    index=False,

    encoding="utf-8-sig",
)


correlacao.to_csv(

    OUTPUT_DIR
    / "correlacao_scores_ipa_2024.csv",

    encoding="utf-8-sig",
)


# ============================================================
# PREPARAÇÃO PARA POSTGRESQL
# ============================================================

resultado = df[
    [

        "codigo_ibge",

        "ano_referencia",

        "score_baixa_cobertura",

        "score_perda_vegetacao",

        "score_pressao_agropecuaria",

        "score_fogo",

        "ipa",

        "classificacao",

        "versao_modelo",

        "ipa_cenario_conservacao",

        "ipa_cenario_disturbio",

        "ipa_media_cenarios",

        "amplitude_cenarios",

        "rank_ipa",

        "rank_conservacao",

        "rank_disturbio",

        "amplitude_rank",

        "estabilidade",
    ]
].copy()


resultado = resultado.rename(

    columns={

        "score_baixa_cobertura":
            "score_vegetacao",

    }
)


resultado.to_sql(

    name="ipa_municipio_temp",

    schema="staging",

    con=engine,

    if_exists="replace",

    index=False,
)


# ============================================================
# UPSERT
# ============================================================

sql_upsert = """
INSERT INTO analytics.ipa_municipio (

    codigo_ibge,

    ano_referencia,

    score_vegetacao,

    score_perda_vegetacao,

    score_pressao_agropecuaria,

    score_fogo,

    ipa,

    classificacao,

    versao_modelo,

    ipa_cenario_conservacao,

    ipa_cenario_disturbio,

    ipa_media_cenarios,

    amplitude_cenarios,

    rank_ipa,

    rank_conservacao,

    rank_disturbio,

    amplitude_rank,

    estabilidade

)

SELECT

    codigo_ibge,

    ano_referencia,

    score_vegetacao,

    score_perda_vegetacao,

    score_pressao_agropecuaria,

    score_fogo,

    ipa,

    classificacao,

    versao_modelo,

    ipa_cenario_conservacao,

    ipa_cenario_disturbio,

    ipa_media_cenarios,

    amplitude_cenarios,

    rank_ipa,

    rank_conservacao,

    rank_disturbio,

    amplitude_rank,

    estabilidade

FROM staging.ipa_municipio_temp

ON CONFLICT (

    codigo_ibge,

    ano_referencia,

    versao_modelo

)

DO UPDATE SET

    score_vegetacao =
        EXCLUDED.score_vegetacao,

    score_perda_vegetacao =
        EXCLUDED.score_perda_vegetacao,

    score_pressao_agropecuaria =
        EXCLUDED.score_pressao_agropecuaria,

    score_fogo =
        EXCLUDED.score_fogo,

    ipa =
        EXCLUDED.ipa,

    classificacao =
        EXCLUDED.classificacao,

    ipa_cenario_conservacao =
        EXCLUDED.ipa_cenario_conservacao,

    ipa_cenario_disturbio =
        EXCLUDED.ipa_cenario_disturbio,

    ipa_media_cenarios =
        EXCLUDED.ipa_media_cenarios,

    amplitude_cenarios =
        EXCLUDED.amplitude_cenarios,

    rank_ipa =
        EXCLUDED.rank_ipa,

    rank_conservacao =
        EXCLUDED.rank_conservacao,

    rank_disturbio =
        EXCLUDED.rank_disturbio,

    amplitude_rank =
        EXCLUDED.amplitude_rank,

    estabilidade =
        EXCLUDED.estabilidade,

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
            staging.ipa_municipio_temp;
        """)
    )


print("\n" + "=" * 72)
print("IPA 2024 CALCULADO COM SUCESSO")
print("=" * 72)