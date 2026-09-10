from pathlib import Path
import re

import pandas as pd


# ============================================================
# VERDEPRIORIZA
# MAPBIOMAS FOGO - COLEÇÃO 5
#
# Converte o CSV exportado do Google Earth Engine:
#
# formato largo:
# CD_MUN | NM_MUN | burned_area_1985 | ... | burned_area_2025
#
# para formato longo:
# codigo_ibge | municipio | ano | area_queimada_ha
# ============================================================


BASE_DIR = Path(__file__).resolve().parent.parent.parent

RAW_DIR = (
    BASE_DIR
    / "data"
    / "raw"
    / "mapbiomas"
    / "fire_collection5"
)

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "mapbiomas"
    / "fire_collection5"
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# LOCALIZAR CSV
# ============================================================

arquivos = sorted(
    RAW_DIR.glob("*.csv")
)

if not arquivos:
    raise FileNotFoundError(
        f"Nenhum CSV encontrado em:\n{RAW_DIR}"
    )


# Preferência pelo nome que usamos no Earth Engine
preferidos = [
    arq
    for arq in arquivos
    if "mapbiomas_fogo_col5_sp_1985_2025" in arq.name.lower()
]

if preferidos:
    arquivo = preferidos[0]
else:
    arquivo = arquivos[0]


print("=" * 70)
print("VERDEPRIORIZA - MAPBIOMAS FOGO")
print("=" * 70)

print(f"\nArquivo: {arquivo.name}")


# ============================================================
# LEITURA
# ============================================================

df = pd.read_csv(
    arquivo,
    dtype=str,
)

df.columns = [
    str(coluna).strip()
    for coluna in df.columns
]


print(f"Linhas originais: {len(df):,}")
print(f"Colunas originais: {len(df.columns)}")


# ============================================================
# IDENTIFICAR MUNICÍPIO
# ============================================================

if "CD_MUN" not in df.columns:
    raise ValueError(
        "Coluna CD_MUN não encontrada no CSV."
    )

if "NM_MUN" not in df.columns:
    raise ValueError(
        "Coluna NM_MUN não encontrada no CSV."
    )


# ============================================================
# IDENTIFICAR COLUNAS DOS ANOS
# ============================================================

#
# O Earth Engine pode devolver:
#
# burned_area_1985
#
# ou, dependendo do redutor:
#
# burned_area_1985_sum
#
# O script aceita os dois formatos.
#

padrao = re.compile(
    r"^burned_area_(\d{4})(?:_sum)?$",
    re.IGNORECASE,
)

colunas_anos = {}
for coluna in df.columns:

    resultado = padrao.match(coluna)

    if resultado:

        ano = int(
            resultado.group(1)
        )

        colunas_anos[coluna] = ano


anos_encontrados = sorted(
    set(colunas_anos.values())
)


print("\nAnos encontrados:")
print(
    f"{min(anos_encontrados)} "
    f"a {max(anos_encontrados)}"
)

print(
    "Quantidade de anos:",
    len(anos_encontrados),
)


# ============================================================
# VALIDAR 1985-2025
# ============================================================

anos_esperados = list(
    range(1985, 2026)
)

faltando = sorted(
    set(anos_esperados)
    - set(anos_encontrados)
)

if faltando:

    raise ValueError(
        "Estão faltando anos no CSV: "
        + ", ".join(
            str(ano)
            for ano in faltando
        )
    )


# ============================================================
# PREPARAR CÓDIGO IBGE
# ============================================================

df["CD_MUN"] = (
    df["CD_MUN"]
    .astype(str)
    .str.strip()
    .str.replace(
        r"\.0$",
        "",
        regex=True,
    )
    .str.zfill(7)
)

df["NM_MUN"] = (
    df["NM_MUN"]
    .astype(str)
    .str.strip()
)


# ============================================================
# FORMATO LARGO -> LONGO
# ============================================================

df_long = df.melt(
    id_vars=[
        "CD_MUN",
        "NM_MUN",
    ],
    value_vars=list(
        colunas_anos.keys()
    ),
    var_name="coluna_ano",
    value_name="area_queimada_ha",
)


# Obter ano a partir do nome original da coluna
df_long["ano"] = (
    df_long["coluna_ano"]
    .map(colunas_anos)
    .astype(int)
)


# Converter área para número
df_long["area_queimada_ha"] = pd.to_numeric(
    df_long["area_queimada_ha"],
    errors="coerce",
).fillna(0)


# ============================================================
# RENOMEAR
# ============================================================

df_long = df_long.rename(
    columns={
        "CD_MUN": "codigo_ibge",
        "NM_MUN": "municipio",
    }
)


df_long = df_long[
    [
        "codigo_ibge",
        "municipio",
        "ano",
        "area_queimada_ha",
    ]
].copy()


# ============================================================
# ORDENAR
# ============================================================

df_long = df_long.sort_values(
    [
        "codigo_ibge",
        "ano",
    ]
).reset_index(
    drop=True
)


# ============================================================
# VALIDAÇÕES
# ============================================================

municipios = (
    df_long["codigo_ibge"]
    .nunique()
)

anos = (
    df_long["ano"]
    .nunique()
)

registros = len(
    df_long
)

esperado = (
    municipios
    * anos
)


print("\n" + "=" * 70)
print("VALIDAÇÃO")
print("=" * 70)

print(
    f"Municípios: {municipios:,}"
)

print(
    f"Primeiro ano: {df_long['ano'].min()}"
)

print(
    f"Último ano: {df_long['ano'].max()}"
)

print(
    f"Quantidade de anos: {anos}"
)

print(
    f"Registros: {registros:,}"
)

print(
    f"Registros esperados: {esperado:,}"
)


if municipios != 645:

    print(
        "\nATENÇÃO:"
        f" esperado 645 municípios, encontrados {municipios}."
    )


if anos != 41:

    raise ValueError(
        f"Esperados 41 anos; encontrados {anos}."
    )


if registros != esperado:

    raise ValueError(
        "Quantidade de registros inconsistente."
    )


if (
    municipios == 645
    and anos == 41
    and registros == 26445
):

    print(
        "\nVALIDAÇÃO PRINCIPAL: OK"
    )


# ============================================================
# SALVAR
# ============================================================

arquivo_saida = (
    PROCESSED_DIR
    / "mapbiomas_fogo_col5_sp_municipio_1985_2025_long.csv"
)

df_long.to_csv(
    arquivo_saida,
    index=False,
    encoding="utf-8-sig",
)


print("\nArquivo processado criado:")
print(arquivo_saida)


# ============================================================
# AMOSTRA
# ============================================================

print("\nPrimeiros 10 registros:")

print(
    df_long
    .head(10)
    .to_string(index=False)
)

print("\nProcessamento concluído.")