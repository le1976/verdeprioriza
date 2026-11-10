import os
from pathlib import Path

import pandas as pd

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL


# ============================================================
# VERDEPRIORIZA
# MÓDULO 9G
# VALIDAÇÃO DOS LIMIARES DAS ÁREAS PRIORITÁRIAS
#
# Referência: 2024
#
# Limiares atualmente avaliados:
# 57,50
# 58,50
# 59,00
#
# O menor limiar encontrado no banco será utilizado
# automaticamente como cenário-base.
# ============================================================


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]


OUTPUT_DIR = (
    ROOT_DIR
    / "outputs"
    / "reports"
    / "module9g"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


LIMIARES_ESPERADOS = {
    55.84,
    58.44,
    61.46,
}


# ============================================================
# BANCO DE DADOS
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
# CONSULTA PRINCIPAL
# ============================================================

sql = """

SELECT

    limiar,


    COUNT(*) AS
        agrupamentos,


    COUNT(*)
    FILTER (

        WHERE
            status_area =
            'Área prioritária contínua'

    ) AS
        areas_continuas,


    COUNT(*)
    FILTER (

        WHERE
            status_area =
            'Núcleo isolado'

    ) AS
        nucleos_isolados,


    SUM(
        area_ha
    ) AS
        area_total_ha,


    AVG(
        area_ha
    ) AS
        area_media_ha,


    PERCENTILE_CONT(0.50)

    WITHIN GROUP (

        ORDER BY
            area_ha

    ) AS
        area_mediana_ha,


    PERCENTILE_CONT(0.90)

    WITHIN GROUP (

        ORDER BY
            area_ha

    ) AS
        area_p90_ha,


    MAX(
        area_ha
    ) AS
        maior_area_ha,


    SUM(

        prioridade_media
        *
        area_ha

    )

    /

    NULLIF(

        SUM(
            area_ha
        ),

        0

    ) AS
        prioridade_media_ponderada,


    COUNT(*)
    FILTER (

        WHERE
            robustez_area =
            'Alta'

    )

    *
    100.0

    /

    NULLIF(
        COUNT(*),
        0
    ) AS
        pct_areas_robustez_alta,


    COUNT(*)

    /

    NULLIF(

        SUM(
            area_ha
        ),

        0

    )

    *
    1000 AS
        fragmentacao_por_1000ha


FROM spatial.area_prioritaria_teste_9g


GROUP BY
    limiar


ORDER BY
    limiar;

"""


df = pd.read_sql(
    sql,
    engine,
)


# ============================================================
# VALIDAR RESULTADO
# ============================================================

if df.empty:

    raise ValueError(
        "\nA consulta não retornou nenhum resultado.\n"
        "Verifique se a tabela "
        "'spatial.area_prioritaria_teste_9g' "
        "foi preenchida pelo SQL da Etapa 9G."
    )


# Garantir tipo numérico

df["limiar"] = pd.to_numeric(
    df["limiar"],
    errors="coerce",
)


df = df.dropna(
    subset=[
        "limiar"
    ]
).copy()


if df.empty:

    raise ValueError(
        "A coluna 'limiar' não contém "
        "valores numéricos válidos."
    )


# ============================================================
# MOSTRAR LIMIARES ENCONTRADOS
# ============================================================

limiares_encontrados_lista = sorted(

    df[
        "limiar"
    ]

    .round(2)

    .tolist()
)


print("=" * 72)
print("VERDEPRIORIZA - VALIDAÇÃO DOS LIMIARES")
print("=" * 72)


print(
    "\nLimiares encontrados no banco:"
)


for valor in limiares_encontrados_lista:

    print(
        f"  - {valor:.2f}"
    )


# ============================================================
# VALIDAR CENÁRIOS ESPERADOS
# ============================================================

limiares_encontrados = {

    round(
        float(valor),
        2
    )

    for valor
    in df["limiar"]
}


faltantes = (

    LIMIARES_ESPERADOS
    -
    limiares_encontrados
)


if faltantes:

    print(
        "\nATENÇÃO:"
    )

    print(
        "Os seguintes limiares esperados "
        "não foram encontrados:"
    )


    for valor in sorted(
        faltantes
    ):

        print(
            f"  - {valor:.2f}"
        )


    print(
        "\nO relatório continuará utilizando "
        "os cenários efetivamente encontrados."
    )


# ============================================================
# MÉTRICAS DERIVADAS
# ============================================================

df["pct_nucleos_isolados"] = (

    df[
        "nucleos_isolados"
    ]

    /

    df[
        "agrupamentos"
    ]

    *

    100
)


# ============================================================
# CENÁRIO-BASE
#
# NÃO utilizamos mais 75 fixo.
#
# O menor limiar encontrado passa a ser automaticamente
# o cenário-base.
# ============================================================

limiar_base = (

    df[
        "limiar"
    ]

    .min()
)


registro_base = df.loc[

    df[
        "limiar"
    ]
    ==
    limiar_base,

    "area_total_ha"
]


if registro_base.empty:

    raise ValueError(
        "Não foi possível localizar "
        "a área total do cenário-base."
    )


area_base = registro_base.iloc[0]


if pd.isna(
    area_base
):

    raise ValueError(
        "A área total do cenário-base "
        "está nula."
    )


if area_base <= 0:

    raise ValueError(
        "A área total do cenário-base "
        "deve ser maior que zero."
    )


print(
    "\nCenário-base:"
    f" limiar {limiar_base:.2f}"
)


print(
    "Área do cenário-base:"
    f" {area_base:,.2f} ha"
    .replace(
        ",",
        "X"
    )
    .replace(
        ".",
        ","
    )
    .replace(
        "X",
        "."
    )
)


# ============================================================
# RETENÇÃO DE ÁREA
# ============================================================

df[
    "pct_area_retida_vs_base"
] = (

    df[
        "area_total_ha"
    ]

    /

    area_base

    *

    100
)


# ============================================================
# PERDA DE ÁREA EM RELAÇÃO AO CENÁRIO-BASE
# ============================================================

df[
    "pct_area_perdida_vs_base"
] = (

    100

    -

    df[
        "pct_area_retida_vs_base"
    ]
)


# ============================================================
# ÁREA MÉDIA POR ÁREA CONTÍNUA
# ============================================================

df[
    "area_media_por_area_continua"
] = (

    df[
        "area_total_ha"
    ]

    /

    df[
        "areas_continuas"
    ]

    .replace(
        0,
        pd.NA
    )
)


# ============================================================
# PERCENTUAL DE ÁREAS CONTÍNUAS
# ============================================================

df[
    "pct_areas_continuas"
] = (

    df[
        "areas_continuas"
    ]

    /

    df[
        "agrupamentos"
    ]

    *

    100
)


# ============================================================
# ARREDONDAMENTO
# ============================================================

colunas_numericas = [

    "area_total_ha",

    "area_media_ha",

    "area_mediana_ha",

    "area_p90_ha",

    "maior_area_ha",

    "prioridade_media_ponderada",

    "pct_areas_robustez_alta",

    "fragmentacao_por_1000ha",

    "pct_nucleos_isolados",

    "pct_area_retida_vs_base",

    "pct_area_perdida_vs_base",

    "area_media_por_area_continua",

    "pct_areas_continuas",
]


for coluna in colunas_numericas:

    df[coluna] = pd.to_numeric(
        df[coluna],
        errors="coerce",
    )


df[colunas_numericas] = (

    df[
        colunas_numericas
    ]

    .round(2)
)


# ============================================================
# ORDENAR
# ============================================================

df = (

    df

    .sort_values(
        "limiar"
    )

    .reset_index(
        drop=True
    )
)


# ============================================================
# SALVAR CSV PRINCIPAL
# ============================================================

saida = (

    OUTPUT_DIR

    /
    "comparacao_limiares_prioridade_integrada.csv"
)


df.to_csv(

    saida,

    index=False,

    encoding="utf-8-sig",
)


# ============================================================
# MOSTRAR RESULTADO
# ============================================================

print("\n" + "=" * 72)
print("COMPARAÇÃO DOS CENÁRIOS")
print("=" * 72)


colunas_exibicao = [

    "limiar",

    "agrupamentos",

    "areas_continuas",

    "nucleos_isolados",

    "area_total_ha",

    "area_mediana_ha",

    "maior_area_ha",

    "prioridade_media_ponderada",

    "pct_areas_robustez_alta",

    "fragmentacao_por_1000ha",

    "pct_nucleos_isolados",

    "pct_area_retida_vs_base",
]


print(

    df[
        colunas_exibicao
    ]

    .to_string(
        index=False
    )
)


# ============================================================
# VARIAÇÃO ENTRE CENÁRIOS CONSECUTIVOS
# ============================================================

comparacao = df[
    [

        "limiar",

        "area_total_ha",

        "prioridade_media_ponderada",

        "fragmentacao_por_1000ha",

        "pct_areas_robustez_alta",

        "pct_nucleos_isolados",

    ]
].copy()


comparacao[
    "delta_area_ha"
] = (

    comparacao[
        "area_total_ha"
    ]

    .diff()
)


comparacao[
    "delta_prioridade"
] = (

    comparacao[
        "prioridade_media_ponderada"
    ]

    .diff()
)


comparacao[
    "delta_fragmentacao"
] = (

    comparacao[
        "fragmentacao_por_1000ha"
    ]

    .diff()
)


comparacao[
    "delta_robustez"
] = (

    comparacao[
        "pct_areas_robustez_alta"
    ]

    .diff()
)


comparacao[
    "delta_pct_isolados"
] = (

    comparacao[
        "pct_nucleos_isolados"
    ]

    .diff()
)


colunas_delta = [

    "delta_area_ha",

    "delta_prioridade",

    "delta_fragmentacao",

    "delta_robustez",

    "delta_pct_isolados",
]


comparacao[
    colunas_delta
] = (

    comparacao[
        colunas_delta
    ]

    .round(2)
)


saida_delta = (

    OUTPUT_DIR

    /
    "variacao_entre_limiares.csv"
)


comparacao.to_csv(

    saida_delta,

    index=False,

    encoding="utf-8-sig",
)


print("\n" + "=" * 72)
print("VARIAÇÃO ENTRE CENÁRIOS")
print("=" * 72)


print(

    comparacao.to_string(
        index=False
    )
)


# ============================================================
# RESUMO AUTOMÁTICO
# ============================================================

print("\n" + "=" * 72)
print("RESUMO")
print("=" * 72)


for _, linha in df.iterrows():

    print(
        f"\nLimiar {linha['limiar']:.2f}"
    )

    print(
        f"  Agrupamentos: "
        f"{int(linha['agrupamentos'])}"
    )

    print(
        f"  Áreas contínuas: "
        f"{int(linha['areas_continuas'])}"
    )

    print(
        f"  Núcleos isolados: "
        f"{int(linha['nucleos_isolados'])}"
    )

    print(
        f"  Área total: "
        f"{linha['area_total_ha']:.2f} ha"
    )

    print(
        f"  Área retida vs. base: "
        f"{linha['pct_area_retida_vs_base']:.2f}%"
    )

    print(
        f"  Prioridade média ponderada: "
        f"{linha['prioridade_media_ponderada']:.2f}"
    )

    print(
        f"  Fragmentação / 1.000 ha: "
        f"{linha['fragmentacao_por_1000ha']:.2f}"
    )

    print(
        f"  Núcleos isolados: "
        f"{linha['pct_nucleos_isolados']:.2f}%"
    )

    print(
        f"  Robustez alta: "
        f"{linha['pct_areas_robustez_alta']:.2f}%"
    )


# ============================================================
# FINALIZAÇÃO
# ============================================================

print("\n" + "=" * 72)
print("VALIDAÇÃO DOS LIMIARES CONCLUÍDA")
print("=" * 72)


print(
    "\nRelatório principal:"
)

print(
    saida
)


print(
    "\nRelatório de variação:"
)

print(
    saida_delta
)