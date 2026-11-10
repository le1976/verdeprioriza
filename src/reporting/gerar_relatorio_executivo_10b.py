import os
import base64
from pathlib import Path
from html import escape

import pandas as pd
import matplotlib.pyplot as plt

from dotenv import load_dotenv
from sqlalchemy import create_engine, URL


# ============================================================
# VERDEPRIORIZA
# MÓDULO 10B
# RELATÓRIO EXECUTIVO AUTOMÁTICO DOS 20 MUNICÍPIOS
#
# Referência: 2024
# Versão territorial: areas_9h_v1.1_2024
# ============================================================


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    ROOT_DIR
    / "outputs"
    / "reports"
    / "module10b"
)

CHARTS_DIR = (
    OUTPUT_DIR
    / "charts"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

CHARTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


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
# CONSULTAS
# ============================================================

df_mun = pd.read_sql(
    """
    SELECT *
    FROM analytics.vw_resumo_municipio_10b
    ORDER BY rank_municipio_10b;
    """,
    engine,
)

df_geral = pd.read_sql(
    """
    SELECT *
    FROM analytics.vw_resumo_geral_10b;
    """,
    engine,
)

df_top = pd.read_sql(
    """
    SELECT

        a.rank_area_geral,
        a.codigo_area,
        m.nome_municipio,
        a.area_total_ha,
        a.area_excepcional_ha,
        a.prioridade_integrada_media,
        a.percentil_prioridade,
        a.robustez_area,
        a.uso_predominante

    FROM spatial.area_prioritaria_9h a

    JOIN core.dim_municipio m
        ON m.codigo_ibge = a.codigo_ibge

    JOIN analytics.validacao_area_9i v
        ON v.id_area = a.id_area

    WHERE
        a.versao_areas = 'areas_9h_v1.1_2024'
        AND a.status_area = 'Área prioritária final'
        AND v.status_validacao = 'Aprovada'

    ORDER BY
        a.rank_area_geral

    LIMIT 20;
    """,
    engine,
)


# ============================================================
# VALIDAÇÕES
# ============================================================

if df_mun.empty:
    raise ValueError(
        "analytics.vw_resumo_municipio_10b não retornou registros."
    )

if df_geral.empty:
    raise ValueError(
        "analytics.vw_resumo_geral_10b não retornou registros."
    )

if len(df_mun) != 20:
    raise ValueError(
        f"Esperados 20 municípios; encontrados {len(df_mun)}."
    )


# ============================================================
# FORMATAÇÃO
# ============================================================

def vazio(valor):
    return pd.isna(valor)


def fmt_num(valor, casas=2):

    if vazio(valor):
        return "-"

    return (
        f"{float(valor):,.{casas}f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def fmt_int(valor):

    if vazio(valor):
        return "-"

    return f"{int(valor):,}".replace(",", ".")


def fmt_pct(valor, casas=1):

    if vazio(valor):
        return "-"

    return (
        fmt_num(
            valor,
            casas,
        )
        +
        "%"
    )


def normalizar_rotulo(valor):

    mapa = {
        "Media": "Média",
        "Muito alta": "Muito alta",
        "Muito baixa": "Muito baixa",
    }

    return mapa.get(
        str(valor),
        str(valor),
    )


# ============================================================
# GRÁFICOS
# ============================================================

# ------------------------------------------------------------
# 1. ÁREA PRIORITÁRIA TOTAL POR MUNICÍPIO
# ------------------------------------------------------------

graf_area = (
    CHARTS_DIR
    / "area_prioritaria_por_municipio.png"
)

plot_df = (
    df_mun
    .sort_values(
        "area_total_ha",
        ascending=True,
    )
)

fig, ax = plt.subplots(
    figsize=(11, 8)
)

ax.barh(
    plot_df["nome_municipio"],
    plot_df["area_total_ha"],
)

ax.set_title(
    "Área prioritária final por município"
)

ax.set_xlabel(
    "Área (ha)"
)

fig.tight_layout()

fig.savefig(
    graf_area,
    dpi=220,
    bbox_inches="tight",
)

plt.close(fig)


# ------------------------------------------------------------
# 2. PRIORIDADE MÉDIA PONDERADA POR MUNICÍPIO
# ------------------------------------------------------------

graf_pi = (
    CHARTS_DIR
    / "prioridade_media_por_municipio.png"
)

plot_df = (
    df_mun
    .sort_values(
        "prioridade_media_ponderada",
        ascending=True,
    )
)

fig, ax = plt.subplots(
    figsize=(11, 8)
)

ax.barh(
    plot_df["nome_municipio"],
    plot_df["prioridade_media_ponderada"],
)

ax.set_title(
    "Prioridade Integrada média ponderada por município"
)

ax.set_xlabel(
    "Prioridade Integrada"
)

fig.tight_layout()

fig.savefig(
    graf_pi,
    dpi=220,
    bbox_inches="tight",
)

plt.close(fig)


# ------------------------------------------------------------
# 3. COMPOSIÇÃO NÚCLEO X SUPORTE
# ------------------------------------------------------------

graf_composicao = (
    CHARTS_DIR
    / "composicao_nucleo_suporte.png"
)

plot_df = (
    df_mun
    .sort_values(
        "area_total_ha",
        ascending=False,
    )
    .head(12)
    .copy()
)

fig, ax = plt.subplots(
    figsize=(12, 7)
)

ax.bar(
    plot_df["nome_municipio"],
    plot_df["area_nucleo_ha"],
    label="Núcleo",
)

ax.bar(
    plot_df["nome_municipio"],
    plot_df["area_suporte_ha"],
    bottom=plot_df["area_nucleo_ha"],
    label="Suporte",
)

ax.set_title(
    "Composição territorial — 12 maiores municípios por área"
)

ax.set_ylabel(
    "Área (ha)"
)

ax.tick_params(
    axis="x",
    rotation=60,
)

ax.legend()

fig.tight_layout()

fig.savefig(
    graf_composicao,
    dpi=220,
    bbox_inches="tight",
)

plt.close(fig)


# ------------------------------------------------------------
# 4. ROBUSTEZ — ÁREA TOTAL
# ------------------------------------------------------------

graf_robustez = (
    CHARTS_DIR
    / "robustez_area_total.png"
)

geral = df_geral.iloc[0]

robustez = pd.Series(
    {
        "Alta":
            geral["area_robustez_alta_ha"],

        "Média":
            geral["area_robustez_media_ha"],

        "Baixa":
            geral["area_robustez_baixa_ha"],
    }
)

fig, ax = plt.subplots(
    figsize=(8, 5)
)

ax.bar(
    robustez.index,
    robustez.values,
)

ax.set_title(
    "Área prioritária por classe de robustez"
)

ax.set_ylabel(
    "Área (ha)"
)

fig.tight_layout()

fig.savefig(
    graf_robustez,
    dpi=220,
    bbox_inches="tight",
)

plt.close(fig)


# ============================================================
# MAPAS DO MÓDULO 9I
# ============================================================

MAPAS_9I = [
    (
        ROOT_DIR
        / "outputs"
        / "maps"
        / "module9i"
        / "areas_prioritarias_percentil_2024.png"
    ),
    (
        ROOT_DIR
        / "outputs"
        / "maps"
        / "module9i"
        / "areas_prioritarias_robustez_2024.png"
    ),
    (
        ROOT_DIR
        / "outputs"
        / "maps"
        / "module9i"
        / "top30_areas_prioritarias_2024.png"
    ),
]


# ============================================================
# BASE64
# ============================================================

def img_base64(caminho):

    caminho = Path(caminho)

    if not caminho.exists():
        return None

    mime = (
        "image/png"
        if caminho.suffix.lower() == ".png"
        else "image/jpeg"
    )

    dados = base64.b64encode(
        caminho.read_bytes()
    ).decode("ascii")

    return (
        f"data:{mime};base64,{dados}"
    )


# ============================================================
# CSVs
# ============================================================

csv_mun = (
    OUTPUT_DIR
    / "resumo_municipios_10b.csv"
)

csv_top = (
    OUTPUT_DIR
    / "top20_areas_10b.csv"
)

df_mun.to_csv(
    csv_mun,
    index=False,
    encoding="utf-8-sig",
)

df_top.to_csv(
    csv_top,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# LEITURA EXECUTIVA AUTOMÁTICA
# ============================================================

top_pi = (
    df_mun
    .sort_values(
        "prioridade_media_ponderada",
        ascending=False,
    )
    .iloc[0]
)

top_area = (
    df_mun
    .sort_values(
        "area_total_ha",
        ascending=False,
    )
    .iloc[0]
)

top_exc = (
    df_mun
    .sort_values(
        "pct_area_excepcional",
        ascending=False,
    )
    .iloc[0]
)

top_rob = (
    df_mun
    .sort_values(
        "pct_area_robustez_alta",
        ascending=False,
    )
    .iloc[0]
)

melhor_area = df_top.iloc[0]

pct_nucleo_geral = (
    geral["area_nucleo_ha"]
    /
    geral["area_total_ha"]
    *
    100
)

pct_suporte_geral = (
    geral["area_suporte_ha"]
    /
    geral["area_total_ha"]
    *
    100
)

pct_excepcional_geral = (
    geral["area_excepcional_ha"]
    /
    geral["area_total_ha"]
    *
    100
)

pct_rob_alta_geral = (
    geral["area_robustez_alta_ha"]
    /
    geral["area_total_ha"]
    *
    100
)


# ============================================================
# TABELA MUNICIPAL HTML
# ============================================================

linhas_municipios = ""

for _, r in df_mun.iterrows():

    linhas_municipios += f"""
    <tr>
        <td>{fmt_int(r['rank_municipio_10b'])}</td>
        <td>{escape(str(r['nome_municipio']))}</td>
        <td>{fmt_int(r['numero_areas'])}</td>
        <td>{fmt_num(r['area_total_ha'], 1)}</td>
        <td>{fmt_num(r['area_excepcional_ha'], 1)}</td>
        <td>{fmt_num(r['prioridade_media_ponderada'], 2)}</td>
        <td>{fmt_num(r['ipa'], 2)}</td>
        <td>{fmt_pct(r['pct_area_robustez_alta'], 1)}</td>
        <td>{escape(str(r['uso_predominante_areas'] or '-'))}</td>
    </tr>
    """


# ============================================================
# TOP 20 HTML
# ============================================================

linhas_top = ""

for _, r in df_top.iterrows():

    linhas_top += f"""
    <tr>
        <td>{fmt_int(r['rank_area_geral'])}</td>
        <td>{escape(str(r['codigo_area']))}</td>
        <td>{escape(str(r['nome_municipio']))}</td>
        <td>{fmt_num(r['area_total_ha'], 1)}</td>
        <td>{fmt_num(r['prioridade_integrada_media'], 2)}</td>
        <td>{fmt_num(r['percentil_prioridade'], 1)}</td>
        <td>{escape(normalizar_rotulo(r['robustez_area']))}</td>
        <td>{escape(str(r['uso_predominante'] or '-'))}</td>
    </tr>
    """


# ============================================================
# IMAGENS HTML
# ============================================================

def bloco_imagem(
    titulo,
    caminho,
):

    src = img_base64(caminho)

    if src is None:
        return ""

    return f"""
    <div class="figure">
        <h3>{escape(titulo)}</h3>
        <img src="{src}">
    </div>
    """


graficos_html = "".join(
    [
        bloco_imagem(
            "Área prioritária por município",
            graf_area,
        ),
        bloco_imagem(
            "Prioridade Integrada média ponderada",
            graf_pi,
        ),
        bloco_imagem(
            "Composição núcleo x suporte",
            graf_composicao,
        ),
        bloco_imagem(
            "Área por classe de robustez",
            graf_robustez,
        ),
    ]
)

mapas_html = "".join(
    [
        bloco_imagem(
            "Mapa — Percentil de prioridade",
            MAPAS_9I[0],
        ),
        bloco_imagem(
            "Mapa — Robustez",
            MAPAS_9I[1],
        ),
        bloco_imagem(
            "Mapa — Top 30 áreas",
            MAPAS_9I[2],
        ),
    ]
)


# ============================================================
# HTML
# ============================================================

html = f"""<!DOCTYPE html>

<html lang="pt-BR">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0">

<title>
VerdePrioriza — Relatório Executivo 2024
</title>

<style>

body {{
    font-family: Arial, Helvetica, sans-serif;
    margin: 0;
    background: #f4f5f6;
    color: #222;
}}

.container {{
    max-width: 1250px;
    margin: 25px auto;
    background: white;
    padding: 35px;
}}

h1 {{
    margin-bottom: 5px;
}}

.subtitle {{
    color: #666;
    margin-bottom: 30px;
}}

.cards {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
    margin: 25px 0 35px 0;
}}

.card {{
    border: 1px solid #ddd;
    padding: 16px;
    border-radius: 8px;
}}

.card-label {{
    font-size: 12px;
    color: #666;
    margin-bottom: 6px;
}}

.card-value {{
    font-size: 23px;
    font-weight: bold;
}}

.section {{
    margin-top: 42px;
}}

.section h2 {{
    border-bottom: 2px solid #ddd;
    padding-bottom: 8px;
}}

.executive {{
    background: #f3f5f6;
    border-left: 5px solid #555;
    padding: 18px 22px;
    line-height: 1.65;
}}

.figure {{
    margin: 30px 0;
    page-break-inside: avoid;
}}

.figure img {{
    width: 100%;
    max-width: 1100px;
    height: auto;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}

th,
td {{
    border-bottom: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}}

th {{
    background: #f1f1f1;
}}

.note {{
    color: #666;
    font-size: 13px;
    line-height: 1.55;
}}

@media print {{

    body {{
        background: white;
    }}

    .container {{
        margin: 0;
        max-width: none;
        padding: 15px;
    }}

}}

</style>

</head>

<body>

<div class="container">


<h1>
VerdePrioriza — Relatório Executivo
</h1>

<div class="subtitle">
20 municípios-alvo | Referência ambiental 2024 |
Versão territorial areas_9h_v1.1_2024
</div>


<div class="cards">

<div class="card">
<div class="card-label">Municípios</div>
<div class="card-value">
{fmt_int(geral['municipios'])}
</div>
</div>

<div class="card">
<div class="card-label">Áreas prioritárias finais</div>
<div class="card-value">
{fmt_int(geral['areas_finais'])}
</div>
</div>

<div class="card">
<div class="card-label">Área total priorizada</div>
<div class="card-value">
{fmt_num(geral['area_total_ha'], 1)} ha
</div>
</div>

<div class="card">
<div class="card-label">Área núcleo</div>
<div class="card-value">
{fmt_pct(pct_nucleo_geral, 1)}
</div>
</div>

<div class="card">
<div class="card-label">Faixa excepcional</div>
<div class="card-value">
{fmt_pct(pct_excepcional_geral, 1)}
</div>
</div>

<div class="card">
<div class="card-label">PI média ponderada</div>
<div class="card-value">
{fmt_num(geral['prioridade_media_ponderada'], 2)}
</div>
</div>

</div>


<div class="section">

<h2>Leitura executiva</h2>

<div class="executive">

<p>
O VerdePrioriza identificou
<strong>{fmt_int(geral['areas_finais'])}</strong>
áreas prioritárias finais distribuídas nos
<strong>{fmt_int(geral['municipios'])}</strong>
municípios-alvo, totalizando
<strong>{fmt_num(geral['area_total_ha'], 1)} ha</strong>.
Do total territorial selecionado,
<strong>{fmt_pct(pct_nucleo_geral, 1)}</strong>
corresponde a núcleo prioritário,
<strong>{fmt_pct(pct_suporte_geral, 1)}</strong>
a suporte espacial e
<strong>{fmt_pct(pct_excepcional_geral, 1)}</strong>
à faixa de prioridade excepcional.
</p>

<p>
O município com maior Prioridade Integrada média ponderada é
<strong>{escape(str(top_pi['nome_municipio']))}</strong>,
com PI médio de
<strong>{fmt_num(top_pi['prioridade_media_ponderada'], 2)}</strong>.
O maior volume territorial priorizado ocorre em
<strong>{escape(str(top_area['nome_municipio']))}</strong>,
com
<strong>{fmt_num(top_area['area_total_ha'], 1)} ha</strong>.
</p>

<p>
A maior participação relativa de área excepcional ocorre em
<strong>{escape(str(top_exc['nome_municipio']))}</strong>,
onde essa faixa representa
<strong>{fmt_pct(top_exc['pct_area_excepcional'], 1)}</strong>
da área prioritária municipal.
A maior participação de área classificada com robustez Alta ocorre em
<strong>{escape(str(top_rob['nome_municipio']))}</strong>,
com
<strong>{fmt_pct(top_rob['pct_area_robustez_alta'], 1)}</strong>.
No conjunto dos 20 municípios,
<strong>{fmt_pct(pct_rob_alta_geral, 1)}</strong>
da área prioritária está na classe de robustez Alta.
</p>

<p>
A área mais bem posicionada no ranking operacional é
<strong>{escape(str(melhor_area['codigo_area']))}</strong>,
em
<strong>{escape(str(melhor_area['nome_municipio']))}</strong>,
com
<strong>{fmt_num(melhor_area['area_total_ha'], 1)} ha</strong>
e Prioridade Integrada média de
<strong>{fmt_num(melhor_area['prioridade_integrada_media'], 2)}</strong>.
</p>

</div>

</div>


<div class="section">

<h2>Indicadores gerais</h2>

<table>

<tr>
<td>Área total</td>
<td>{fmt_num(geral['area_total_ha'], 1)} ha</td>
</tr>

<tr>
<td>Área núcleo</td>
<td>
{fmt_num(geral['area_nucleo_ha'], 1)} ha
({fmt_pct(pct_nucleo_geral, 1)})
</td>
</tr>

<tr>
<td>Área suporte</td>
<td>
{fmt_num(geral['area_suporte_ha'], 1)} ha
({fmt_pct(pct_suporte_geral, 1)})
</td>
</tr>

<tr>
<td>Área excepcional</td>
<td>
{fmt_num(geral['area_excepcional_ha'], 1)} ha
({fmt_pct(pct_excepcional_geral, 1)})
</td>
</tr>

<tr>
<td>Áreas robustez Alta</td>
<td>{fmt_int(geral['areas_robustez_alta'])}</td>
</tr>

<tr>
<td>Áreas robustez Média</td>
<td>{fmt_int(geral['areas_robustez_media'])}</td>
</tr>

<tr>
<td>Áreas robustez Baixa</td>
<td>{fmt_int(geral['areas_robustez_baixa'])}</td>
</tr>

<tr>
<td>Áreas no percentil 90+</td>
<td>{fmt_int(geral['areas_percentil_90_mais'])}</td>
</tr>

<tr>
<td>IPA médio dos municípios</td>
<td>{fmt_num(geral['ipa_medio_municipios'], 2)}</td>
</tr>

</table>

</div>


<div class="section">

<h2>Gráficos executivos</h2>

{graficos_html}

</div>


<div class="section">

<h2>Resumo por município</h2>

<table>

<thead>
<tr>
<th>Rank</th>
<th>Município</th>
<th>Áreas</th>
<th>Área (ha)</th>
<th>Excepcional (ha)</th>
<th>PI média</th>
<th>IPA</th>
<th>Robustez Alta</th>
<th>Uso predominante</th>
</tr>
</thead>

<tbody>
{linhas_municipios}
</tbody>

</table>

</div>


<div class="section">

<h2>Top 20 áreas prioritárias</h2>

<table>

<thead>
<tr>
<th>Rank</th>
<th>Código</th>
<th>Município</th>
<th>Área (ha)</th>
<th>PI</th>
<th>Percentil</th>
<th>Robustez</th>
<th>Uso predominante</th>
</tr>
</thead>

<tbody>
{linhas_top}
</tbody>

</table>

</div>


<div class="section">

<h2>Mapas técnicos</h2>

{mapas_html}

</div>


<div class="section">

<h2>Nota metodológica</h2>

<p class="note">
O VerdePrioriza é uma ferramenta de triagem territorial e apoio à
decisão. A versão apresentada utiliza referência ambiental 2024 e a
camada territorial <strong>areas_9h_v1.1_2024</strong>. O relatório
executivo sintetiza as áreas previamente validadas na Etapa 9I.
A priorização não representa, isoladamente, obrigação legal de
restauração, déficit de APP ou Reserva Legal, disponibilidade fundiária
ou autorização automática de intervenção. A decisão de campo deve ser
complementada por análise técnica, fundiária, cadastral e vistoria local.
</p>

</div>


</div>

</body>

</html>
"""


# ============================================================
# SALVAR RELATÓRIO
# ============================================================

report_path = (
    OUTPUT_DIR
    / "relatorio_executivo_20_municipios_2024.html"
)

report_path.write_text(
    html,
    encoding="utf-8",
)


# ============================================================
# FINAL
# ============================================================

print("=" * 72)
print("VERDEPRIORIZA - RELATÓRIO EXECUTIVO 10B")
print("=" * 72)

print(
    f"\nMunicípios: {len(df_mun)}"
)

print(
    f"Áreas finais: "
    f"{fmt_int(geral['areas_finais'])}"
)

print(
    f"Área total: "
    f"{fmt_num(geral['area_total_ha'], 1)} ha"
)

print(
    "\nRelatório:"
)

print(
    report_path
)

print(
    "\nCSVs:"
)

print(
    csv_mun
)

print(
    csv_top
)

print(
    "\nGráficos:"
)

print(
    CHARTS_DIR
)
