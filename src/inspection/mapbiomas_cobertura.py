import os
import re
import unicodedata

from pathlib import Path

import pandas as pd

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
    / "mapbiomas"
    / "collection11"
)


COLECAO = "11"

ANO_INICIAL = 1985
ANO_FINAL = 2025


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
    port=int(os.getenv("DB_PORT", 5432)),
    database=os.getenv("DB_NAME"),
)


engine = create_engine(url)


# ============================================================
# FUNÇÕES
# ============================================================

def normalizar_texto(valor):

    if pd.isna(valor):
        return ""

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

    texto = texto.lower().strip()

    texto = re.sub(
        r"[^a-z0-9]+",
        "_",
        texto,
    )

    return texto.strip("_")


def normalizar_coluna(valor):

    if isinstance(valor, (int, float)):

        if not pd.isna(valor):

            numero = float(valor)

            if numero.is_integer():
                return str(int(numero))

    texto = str(valor)

    if re.fullmatch(r"\d{4}\.0", texto):
        return texto[:4]

    return normalizar_texto(texto)


def localizar_coluna(colunas, candidatos):

    for candidato in candidatos:

        if candidato in colunas:
            return candidato

    return None


def localizar_header(arquivo, sheet):

    preview = pd.read_excel(
        arquivo,
        sheet_name=sheet,
        header=None,
        nrows=20,
    )

    for indice, row in preview.iterrows():

        valores = set()

        for valor in row:

            if pd.isna(valor):
                continue

            try:
                numero = int(float(valor))

                if 1900 <= numero <= 2100:
                    valores.add(numero)

            except (ValueError, TypeError):
                pass

        if (
            ANO_INICIAL in valores
            and ANO_FINAL in valores
        ):
            return indice

    return None


# ============================================================
# LOCALIZAR ARQUIVO
# ============================================================

arquivos = list(
    DATA_DIR.glob("*.xlsx")
)


if not arquivos:
    raise FileNotFoundError(
        f"Nenhum .xlsx encontrado em:\n{DATA_DIR}"
    )


arquivo = arquivos[0]


print("=" * 70)
print("VERDEPRIORIZA - ETL MAPBIOMAS")
print("=" * 70)

print(f"\nArquivo: {arquivo.name}")


# ============================================================
# LOCALIZAR PLANILHA PRINCIPAL
# ============================================================

excel = pd.ExcelFile(
    arquivo
)


melhor_df = None
melhor_sheet = None
maior_numero_anos = 0


for sheet in excel.sheet_names:

    header = localizar_header(
        arquivo,
        sheet,
    )

    if header is None:
        continue

    df_temp = pd.read_excel(
        arquivo,
        sheet_name=sheet,
        header=header,
    )

    df_temp.columns = [
        normalizar_coluna(c)
        for c in df_temp.columns
    ]

    anos = [
        c
        for c in df_temp.columns
        if c.isdigit()
        and ANO_INICIAL <= int(c) <= ANO_FINAL
    ]

    if len(anos) > maior_numero_anos:

        maior_numero_anos = len(anos)

        melhor_df = df_temp

        melhor_sheet = sheet


if melhor_df is None:

    raise ValueError(
        "Não encontrei uma planilha contendo "
        "a série histórica 1985-2025."
    )


df = melhor_df


print(
    f"\nPlanilha selecionada: {melhor_sheet}"
)

print(
    f"Anos encontrados: {maior_numero_anos}"
)


# ============================================================
# IDENTIFICAR COLUNAS
# ============================================================

colunas = list(
    df.columns
)


print("\nColunas identificadas:")

for c in colunas:
    print(f" - {c}")


col_uf = localizar_coluna(
    colunas,
    [
        "state",
        "estado",
        "uf",
        "state_name",
    ],
)


col_bioma = localizar_coluna(
    colunas,
    [
        "biome",
        "bioma",
    ],
)


col_codigo = localizar_coluna(
    colunas,
    [
        "municipality_code",
        "municipio_codigo",
        "codigo_municipio",
        "codigo_ibge",
        "cd_mun",
        "geocode",
    ],
)


col_municipio = localizar_coluna(
    colunas,
    [
        "municipality",
        "municipio",
        "municipality_name",
        "nome_municipio",
    ],
)


col_classe_id = localizar_coluna(
    colunas,
    [
        "class_id",
        "classe_id",
        "id_classe",
        "class_code",
        "codigo_classe",
    ],
)


col_classe = localizar_coluna(
    colunas,
    [
        "class",
        "classe",
        "class_name",
        "classe_nome",
    ],
)


col_nivel = localizar_coluna(
    colunas,
    [
        "level",
        "nivel",
    ],
)


# ============================================================
# ANOS
# ============================================================

colunas_ano = [
    c
    for c in df.columns
    if c.isdigit()
    and ANO_INICIAL <= int(c) <= ANO_FINAL
]


if len(colunas_ano) != 41:

    raise ValueError(
        f"Esperávamos 41 anos entre 1985 e 2025, "
        f"mas encontramos {len(colunas_ano)}."
    )


# ============================================================
# DIMENSÃO MUNICÍPIO DO NOSSO BANCO
# ============================================================

municipios_core = pd.read_sql(
    """
    SELECT
        codigo_ibge,
        nome_municipio
    FROM core.dim_municipio
    WHERE uf = 'SP'
    """,
    engine,
)


municipios_core["codigo6"] = (
    municipios_core["codigo_ibge"]
    .str[:6]
)


municipios_core["nome_normalizado"] = (
    municipios_core["nome_municipio"]
    .map(normalizar_texto)
)


# ============================================================
# FILTRAR SÃO PAULO
# ============================================================

if col_uf is not None:

    uf_normalizada = (
        df[col_uf]
        .map(normalizar_texto)
    )

    df = df[
        uf_normalizada.isin(
            [
                "sp",
                "sao_paulo",
            ]
        )
    ].copy()


# ============================================================
# CÓDIGO IBGE
# ============================================================

if col_codigo is not None:

    df["codigo_original"] = (
        df[col_codigo]
        .astype(str)
        .str.extract(r"(\d+)", expand=False)
    )

    mapa_7 = dict(
        zip(
            municipios_core["codigo_ibge"],
            municipios_core["codigo_ibge"],
        )
    )

    mapa_6 = dict(
        zip(
            municipios_core["codigo6"],
            municipios_core["codigo_ibge"],
        )
    )

    def converter_codigo(valor):

        if pd.isna(valor):
            return None

        valor = str(valor)

        if len(valor) >= 7:

            codigo7 = valor[:7]

            if codigo7 in mapa_7:
                return codigo7

        codigo6 = valor[:6]

        return mapa_6.get(
            codigo6
        )

    df["codigo_ibge"] = (
        df["codigo_original"]
        .apply(converter_codigo)
    )

else:

    if col_municipio is None:

        raise ValueError(
            "Não encontrei código nem nome de município."
        )

    mapa_nome = dict(
        zip(
            municipios_core["nome_normalizado"],
            municipios_core["codigo_ibge"],
        )
    )

    df["codigo_ibge"] = (
        df[col_municipio]
        .map(normalizar_texto)
        .map(mapa_nome)
    )


# Caso não existisse coluna UF,
# o código IBGE agora permite filtrar SP.

df = df[
    df["codigo_ibge"].notna()
].copy()


# ============================================================
# IDENTIFICAR AS CINCO CLASSES DE NÍVEL 1
# ============================================================

mapa_id = {
    1: "formacao_florestal",
    10: "vegetacao_herbacea_arbustiva",
    14: "agropecuaria",
    22: "area_nao_vegetada",
    26: "corpo_agua",
}


df["categoria"] = None


# ------------------------------------------------------------
# Preferência 1: ID oficial da classe
# ------------------------------------------------------------

if col_classe_id is not None:

    ids = pd.to_numeric(
        df[col_classe_id],
        errors="coerce",
    )

    ids_disponiveis = set(
        ids.dropna().astype(int)
    )

    # Verificamos se parecem realmente os códigos
    # oficiais do MapBiomas.

    if any(
        codigo in ids_disponiveis
        for codigo in [10, 14, 22, 26]
    ):

        df["classe_id_padrao"] = ids

        df["categoria"] = (
            df["classe_id_padrao"]
            .map(mapa_id)
        )

# ------------------------------------------------------------
# Preferência 2: estrutura oficial COVERAGE_11
# Usa class_level_1 para identificar os grandes grupos
# ------------------------------------------------------------

if (
    df["categoria"].notna().sum() == 0
    and "class_level_1" in df.columns
):

    classe_nivel_1 = (
        df["class_level_1"]
        .fillna("")
        .map(normalizar_texto)
    )

    def identificar_categoria_level_1(texto):

        # 1. Forest
        if (
            "forest" in texto
            or "floresta" in texto
        ):
            return "formacao_florestal"

        # 2. Herbaceous and Shrubby Vegetation
        if (
            "herbaceous" in texto
            or "shrubby" in texto
            or "vegetacao_herbacea" in texto
            or "vegetacao_herbacea_e_arbustiva" in texto
        ):
            return "vegetacao_herbacea"

        # 3. Farming
        if (
            "farming" in texto
            or "agropecuaria" in texto
        ):
            return "agropecuaria"

        # 4. Non vegetated area
        if (
            "non_vegetated" in texto
            or "nao_vegetada" in texto
            or "area_nao_vegetada" in texto
        ):
            return "area_nao_vegetada"

        # 5. Water
        if (
            "water" in texto
            or "agua" in texto
            or "corpo_agua" in texto
        ):
            return "corpo_agua"

        return None

    df["categoria"] = classe_nivel_1.map(
        identificar_categoria_level_1
    )

    print("\nCategorias identificadas por class_level_1:")
    print(
        df["categoria"]
        .value_counts(dropna=False)
        .to_string()
    )

# ------------------------------------------------------------
# Preferência 3: nível + nome da classe
# ------------------------------------------------------------

if df["categoria"].notna().sum() == 0:

    if (
        col_classe is None
        or col_nivel is None
    ):

        raise ValueError(
            "Não consegui identificar de forma segura "
            "as classes MapBiomas. Execute o script "
            "inspect_mapbiomas.py e verifique os nomes "
            "das colunas."
        )

    nivel = pd.to_numeric(
        df[col_nivel],
        errors="coerce",
    )

    df = df[
        nivel == 1
    ].copy()

    classe_normalizada = (
        df[col_classe]
        .map(normalizar_texto)
    )

    def identificar_categoria(texto):

        if "formacao_florestal" in texto:
            return "formacao_florestal"

        if (
            "vegetacao_herbacea" in texto
            or "vegetacao_herbacea_e_arbustiva" in texto
        ):
            return "vegetacao_herbacea_arbustiva"

        if "agropecuaria" in texto:
            return "agropecuaria"

        if "area_nao_vegetada" in texto:
            return "area_nao_vegetada"

        if (
            "corpo_d_agua" in texto
            or "corpo_dagua" in texto
        ):
            return "corpo_agua"

        return None

    df["categoria"] = (
        classe_normalizada
        .apply(identificar_categoria)
    )


df = df[
    df["categoria"].notna()
].copy()


# ============================================================
# GARANTIR NÍVEL 1
# ============================================================

if col_nivel is not None:

    nivel = pd.to_numeric(
        df[col_nivel],
        errors="coerce",
    )

    # Quando o arquivo realmente possuir hierarquia,
    # evitamos somar classe pai + classe filha.

    if (nivel == 1).any():

        df = df[
            nivel == 1
        ].copy()


# ============================================================
# WIDE → LONG
# ============================================================

colunas_identificacao = [
    "codigo_ibge",
    "categoria",
]


if col_bioma is not None:
    colunas_identificacao.append(
        col_bioma
    )


long_df = df.melt(

    id_vars=colunas_identificacao,

    value_vars=colunas_ano,

    var_name="ano",

    value_name="area_ha",
)


long_df["ano"] = (
    long_df["ano"]
    .astype(int)
)


long_df["area_ha"] = pd.to_numeric(
    long_df["area_ha"],
    errors="coerce",
)


long_df = long_df[
    long_df["area_ha"].notna()
].copy()


# ============================================================
# PREPARAR RAW
# ============================================================

codigo_por_categoria = {
    "formacao_florestal": 1,
    "vegetacao_herbacea_arbustiva": 10,
    "agropecuaria": 14,
    "area_nao_vegetada": 22,
    "corpo_agua": 26,
}


nome_por_categoria = {
    "formacao_florestal":
        "Formação Florestal",

    "vegetacao_herbacea_arbustiva":
        "Vegetação Herbácea e Arbustiva",

    "agropecuaria":
        "Agropecuária",

    "area_nao_vegetada":
        "Área não vegetada",

    "corpo_agua":
        "Corpo d'Água",
}


mapa_nome_oficial = dict(
    zip(
        municipios_core["codigo_ibge"],
        municipios_core["nome_municipio"],
    )
)


raw_df = pd.DataFrame()


raw_df["codigo_ibge"] = (
    long_df["codigo_ibge"]
)


raw_df["municipio"] = (
    raw_df["codigo_ibge"]
    .map(mapa_nome_oficial)
)


raw_df["uf"] = "SP"


if col_bioma is not None:

    raw_df["bioma"] = (
        long_df[col_bioma]
        .astype(str)
    )

else:

    raw_df["bioma"] = None


raw_df["ano"] = (
    long_df["ano"]
)


raw_df["classe_id"] = (
    long_df["categoria"]
    .map(codigo_por_categoria)
)


raw_df["classe"] = (
    long_df["categoria"]
    .map(nome_por_categoria)
)


raw_df["nivel"] = 1

raw_df["area_ha"] = (
    long_df["area_ha"]
)

raw_df["colecao"] = COLECAO

raw_df["arquivo_origem"] = (
    arquivo.name
)


# ============================================================
# VALIDAÇÕES RAW
# ============================================================

municipios_encontrados = (
    raw_df["codigo_ibge"]
    .nunique()
)


anos_encontrados = (
    raw_df["ano"]
    .nunique()
)


print(
    f"\nMunicípios encontrados: {municipios_encontrados}"
)

print(
    f"Anos encontrados: {anos_encontrados}"
)


if municipios_encontrados != 645:

    raise ValueError(
        f"Esperávamos 645 municípios de SP, "
        f"mas encontramos {municipios_encontrados}."
    )


if anos_encontrados != 41:

    raise ValueError(
        f"Esperávamos 41 anos, "
        f"mas encontramos {anos_encontrados}."
    )


# ============================================================
# CARREGAR RAW
# ============================================================

print(
    "\nCarregando raw.mapbiomas_municipio..."
)


with engine.begin() as conn:

    conn.execute(
        text("""
            DELETE FROM raw.mapbiomas_municipio
            WHERE colecao = '11'
              AND uf = 'SP';
        """)
    )

    raw_df.to_sql(
        name="mapbiomas_municipio",
        schema="raw",
        con=conn,
        if_exists="append",
        index=False,
        chunksize=5000,
        method="multi",
    )


# ============================================================
# CONSOLIDAR MUNICÍPIO × ANO
# ============================================================

consolidado = (

    raw_df

    .groupby(
        [
            "codigo_ibge",
            "ano",
            "classe_id",
        ],
        as_index=False,
    )

    ["area_ha"]
    .sum()
)


pivot = consolidado.pivot_table(

    index=[
        "codigo_ibge",
        "ano",
    ],

    columns="classe_id",

    values="area_ha",

    aggfunc="sum",

    fill_value=0,
).reset_index()


for codigo in [
    1,
    10,
    14,
    22,
    26,
]:

    if codigo not in pivot.columns:
        pivot[codigo] = 0


staging_df = pd.DataFrame()


staging_df["codigo_ibge"] = (
    pivot["codigo_ibge"]
)

staging_df["ano"] = (
    pivot["ano"]
)

staging_df["colecao"] = COLECAO


staging_df["formacao_florestal_ha"] = (
    pivot[1]
)


staging_df[
    "vegetacao_herbacea_arbustiva_ha"
] = pivot[10]


staging_df["vegetacao_nativa_ha"] = (
    pivot[1]
    +
    pivot[10]
)


staging_df["agropecuaria_ha"] = (
    pivot[14]
)


staging_df["area_nao_vegetada_ha"] = (
    pivot[22]
)


staging_df["corpo_agua_ha"] = (
    pivot[26]
)


staging_df["area_mapeada_ha"] = (

    staging_df["vegetacao_nativa_ha"]
    +
    staging_df["agropecuaria_ha"]
    +
    staging_df["area_nao_vegetada_ha"]
    +
    staging_df["corpo_agua_ha"]
)


# ============================================================
# VALIDAÇÃO DO PAINEL
# ============================================================

esperado = (
    645
    *
    41
)


if len(staging_df) != esperado:

    raise ValueError(
        f"Esperávamos {esperado} registros "
        f"município×ano, mas encontramos "
        f"{len(staging_df)}."
    )


print(
    f"\nPainel município×ano: {len(staging_df)} registros."
)


# ============================================================
# CARREGAR STAGING
# ============================================================

print(
    "Carregando staging.mapbiomas_municipio_ano..."
)


with engine.begin() as conn:

    conn.execute(
        text("""
            DELETE
            FROM staging.mapbiomas_municipio_ano
            WHERE colecao = '11';
        """)
    )

    staging_df.to_sql(
        name="mapbiomas_municipio_ano",
        schema="staging",
        con=conn,
        if_exists="append",
        index=False,
        chunksize=5000,
        method="multi",
    )


# ============================================================
# ANALYTICS - ANO 2025
# ============================================================

sql_analytics = """
INSERT INTO analytics.indicador_municipio (

    codigo_ibge,
    ano,

    vegetacao_nativa_ha,
    vegetacao_nativa_pct,

    agropecuaria_ha,
    agropecuaria_pct,

    colecao_mapbiomas,

    variacao_liquida_vegetacao_ha_5a,
    variacao_liquida_vegetacao_ha_10a,
    variacao_liquida_vegetacao_ha_40a
)

SELECT

    atual.codigo_ibge,

    atual.ano,

    atual.vegetacao_nativa_ha,

    100.0
    *
    atual.vegetacao_nativa_ha
    /
    NULLIF(
        atual.area_mapeada_ha,
        0
    ),

    atual.agropecuaria_ha,

    100.0
    *
    atual.agropecuaria_ha
    /
    NULLIF(
        atual.area_mapeada_ha,
        0
    ),

    '11',

    atual.vegetacao_nativa_ha
        - cinco.vegetacao_nativa_ha,

    atual.vegetacao_nativa_ha
        - dez.vegetacao_nativa_ha,

    atual.vegetacao_nativa_ha
        - quarenta.vegetacao_nativa_ha

FROM staging.mapbiomas_municipio_ano atual

LEFT JOIN staging.mapbiomas_municipio_ano cinco
    ON atual.codigo_ibge = cinco.codigo_ibge
    AND cinco.ano = 2020
    AND cinco.colecao = '11'

LEFT JOIN staging.mapbiomas_municipio_ano dez
    ON atual.codigo_ibge = dez.codigo_ibge
    AND dez.ano = 2015
    AND dez.colecao = '11'

LEFT JOIN staging.mapbiomas_municipio_ano quarenta
    ON atual.codigo_ibge = quarenta.codigo_ibge
    AND quarenta.ano = 1985
    AND quarenta.colecao = '11'

WHERE
    atual.ano = 2025
    AND atual.colecao = '11'

ON CONFLICT (
    codigo_ibge,
    ano
)

DO UPDATE SET

    vegetacao_nativa_ha =
        EXCLUDED.vegetacao_nativa_ha,

    vegetacao_nativa_pct =
        EXCLUDED.vegetacao_nativa_pct,

    agropecuaria_ha =
        EXCLUDED.agropecuaria_ha,

    agropecuaria_pct =
        EXCLUDED.agropecuaria_pct,

    colecao_mapbiomas =
        EXCLUDED.colecao_mapbiomas,

    variacao_liquida_vegetacao_ha_5a =
        EXCLUDED.variacao_liquida_vegetacao_ha_5a,

    variacao_liquida_vegetacao_ha_10a =
        EXCLUDED.variacao_liquida_vegetacao_ha_10a,

    variacao_liquida_vegetacao_ha_40a =
        EXCLUDED.variacao_liquida_vegetacao_ha_40a,

    data_calculo =
        CURRENT_TIMESTAMP;
"""


with engine.begin() as conn:

    conn.execute(
        text(sql_analytics)
    )


print("\n" + "=" * 70)
print("ETL MAPBIOMAS FINALIZADO COM SUCESSO")
print("=" * 70)