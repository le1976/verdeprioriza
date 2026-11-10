import os
import argparse
from pathlib import Path
from html import escape

import pandas as pd
import matplotlib.pyplot as plt

from dotenv import load_dotenv
from sqlalchemy import create_engine, URL


# ============================================================
# VERDEPRIORIZA
# MÓDULO 10C
# RELATÓRIOS DE EXPLICABILIDADE
# ============================================================


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    ROOT_DIR
    / "outputs"
    / "reports"
    / "module10c"
)

REPORTS_DIR = (
    OUTPUT_DIR
    / "areas"
)

CHARTS_DIR = (
    OUTPUT_DIR
    / "charts"
)

for pasta in (
    OUTPUT_DIR,
    REPORTS_DIR,
    CHARTS_DIR,
):
    pasta.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================
# ARGUMENTOS
# ============================================================

parser = argparse.ArgumentParser(
    description=(
        "Gera relatórios de explicabilidade "
        "das áreas prioritárias do VerdePrioriza."
    )
)

parser.add_argument(
    "--codigo-area",
    type=str,
    default=None,
    help=(
        "Gera somente uma área específica. "
        "Exemplo: 3525300-H001"
    ),
)

parser.add_argument(
    "--top",
    type=int,
    default=None,
    help=(
        "Gera somente as N primeiras áreas "
        "do ranking geral."
    ),
)

args = parser.parse_args()


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

df_areas = pd.read_sql(
    """
    SELECT *
    FROM analytics.vw_explicabilidade_area_10c
    ORDER BY rank_area_geral;
    """,
    engine,
)

df_municipios = pd.read_sql(
    """
    SELECT *
    FROM analytics.vw_explicabilidade_municipio_10c
    ORDER BY rank_municipio_10b;
    """,
    engine,
)


# ============================================================
# VALIDAÇÕES
# ============================================================

if df_areas.empty:
    raise ValueError(
        "vw_explicabilidade_area_10c "
        "não retornou registros."
    )

if df_municipios.empty:
    raise ValueError(
        "vw_explicabilidade_municipio_10c "
        "não retornou registros."
    )

if len(df_municipios) != 20:
    raise ValueError(
        f"Esperados 20 municípios; "
        f"encontrados {len(df_municipios)}."
    )


# ============================================================
# FILTROS
# ============================================================

if args.codigo_area:

    df_areas = df_areas.loc[
        df_areas["codigo_area"]
        == args.codigo_area
    ].copy()

    if df_areas.empty:
        raise ValueError(
            "Área não encontrada: "
            f"{args.codigo_area}"
        )

elif args.top:

    df_areas = (
        df_areas
        .head(args.top)
        .copy()
    )


# ============================================================
# FORMATAÇÃO
# ============================================================

def vazio(valor):
    return pd.isna(valor)


def fmt_num(
    valor,
    casas=2,
):

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

    return (
        f"{int(valor):,}"
        .replace(",", ".")
    )


def fmt_pct(
    valor,
    casas=1,
):

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


def fmt_delta(valor):

    if vazio(valor):
        return "-"

    sinal = (
        "+"
        if float(valor) > 0
        else ""
    )

    return (
        sinal
        +
        fmt_num(
            valor,
            1,
        )
    )


def normalizar_rotulo(valor):

    mapa = {
        "Media": "Média",
    }

    return mapa.get(
        str(valor),
        str(valor),
    )


# ============================================================
# GRÁFICO DOS COMPONENTES
# ============================================================

def gerar_grafico_componentes(linha):

    nomes = [
        "Hidrologia",
        "Conectividade",
        "Declividade",
        "Elegibilidade",
    ]

    area = [
        linha["score_hidrologia_medio"],
        linha["score_conectividade_medio"],
        linha["score_declividade_medio"],
        linha["score_elegibilidade_medio"],
    ]

    medias = [
        linha["media_hidrologia"],
        linha["media_conectividade"],
        linha["media_declividade"],
        linha["media_elegibilidade"],
    ]

    x = range(
        len(nomes)
    )

    largura = 0.36

    fig, ax = plt.subplots(
        figsize=(9, 5)
    )

    pos_area = [
        i - largura / 2
        for i in x
    ]

    pos_media = [
        i + largura / 2
        for i in x
    ]

    ax.bar(
        pos_area,
        area,
        width=largura,
        label="Área",
    )

    ax.bar(
        pos_media,
        medias,
        width=largura,
        label="Média das 1.045 áreas",
    )

    ax.set_xticks(
        list(x)
    )

    ax.set_xticklabels(
        nomes
    )

    ax.set_ylim(
        0,
        100,
    )

    ax.set_ylabel(
        "Score"
    )

    ax.set_title(
        (
            "Componentes ambientais — "
            f"{linha['codigo_area']}"
        )
    )

    ax.legend()

    fig.tight_layout()

    destino = (
        CHARTS_DIR
        /
        (
            "componentes_"
            +
            str(
                linha["codigo_area"]
            )
            +
            ".png"
        )
    )

    fig.savefig(
        destino,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)

    return destino


# ============================================================
# EXPLICAÇÃO DOS DELTAS
# ============================================================

def interpretar_delta(
    delta,
):

    if vazio(delta):
        return "-"

    delta = float(delta)

    if delta >= 10:
        return "Muito acima da média"

    if delta >= 3:
        return "Acima da média"

    if delta <= -10:
        return "Muito abaixo da média"

    if delta <= -3:
        return "Abaixo da média"

    return "Próximo da média"


# ============================================================
# GERAÇÃO DO HTML
# ============================================================

def gerar_html(
    linha,
    municipio,
    grafico_path,
):

    componentes = [
        (
            "Hidrologia",
            linha["score_hidrologia_medio"],
            linha["media_hidrologia"],
            linha["delta_hidrologia"],
        ),
        (
            "Conectividade",
            linha["score_conectividade_medio"],
            linha["media_conectividade"],
            linha["delta_conectividade"],
        ),
        (
            "Declividade",
            linha["score_declividade_medio"],
            linha["media_declividade"],
            linha["delta_declividade"],
        ),
        (
            "Elegibilidade",
            linha["score_elegibilidade_medio"],
            linha["media_elegibilidade"],
            linha["delta_elegibilidade"],
        ),
    ]

    linhas_componentes = ""

    for (
        nome,
        valor,
        media,
        delta,
    ) in componentes:

        linhas_componentes += f"""
        <tr>
            <td>{escape(nome)}</td>
            <td>{fmt_num(valor, 1)}</td>
            <td>{fmt_num(media, 1)}</td>
            <td>{fmt_delta(delta)}</td>
            <td>{escape(interpretar_delta(delta))}</td>
        </tr>
        """

    grafico_rel = (
        "../charts/"
        +
        grafico_path.name
    )

    return f"""<!DOCTYPE html>

<html lang="pt-BR">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0">

<title>
Explicabilidade — {escape(str(linha['codigo_area']))}
</title>

<style>

body {{
    font-family: Arial, Helvetica, sans-serif;
    margin: 0;
    background: #f4f5f6;
    color: #222;
}}

.container {{
    max-width: 1100px;
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
        repeat(
            auto-fit,
            minmax(180px, 1fr)
        );
    gap: 14px;
    margin-bottom: 30px;
}}

.card {{
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
}}

.card-label {{
    color: #666;
    font-size: 12px;
    margin-bottom: 5px;
}}

.card-value {{
    font-size: 22px;
    font-weight: bold;
}}

.section {{
    margin-top: 38px;
}}

.section h2 {{
    border-bottom: 2px solid #ddd;
    padding-bottom: 8px;
}}

.explain {{
    background: #f3f5f6;
    border-left: 5px solid #555;
    padding: 18px;
    line-height: 1.65;
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

.figure img {{
    width: 100%;
    max-width: 950px;
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
VerdePrioriza — Explicabilidade
</h1>

<div class="subtitle">
Área
<strong>{escape(str(linha['codigo_area']))}</strong>
|
{escape(str(linha['nome_municipio']))}
|
Referência 2024
</div>


<div class="cards">

<div class="card">
<div class="card-label">Ranking geral</div>
<div class="card-value">
{fmt_int(linha['rank_area_geral'])}º
</div>
</div>

<div class="card">
<div class="card-label">Percentil</div>
<div class="card-value">
{fmt_num(linha['percentil_prioridade'], 1)}
</div>
</div>

<div class="card">
<div class="card-label">Prioridade Integrada</div>
<div class="card-value">
{fmt_num(linha['prioridade_integrada_media'], 2)}
</div>
</div>

<div class="card">
<div class="card-label">Robustez</div>
<div class="card-value">
{escape(normalizar_rotulo(linha['robustez_area']))}
</div>
</div>

</div>


<div class="section">

<h2>
Por que esta área está nesta posição?
</h2>

<div class="explain">
{escape(str(linha['explicacao_automatica']))}
</div>

</div>


<div class="section">

<h2>
IPA + IPL + Prioridade Integrada
</h2>

<table>

<tr>
<td>IPA municipal</td>
<td>{fmt_num(linha['ipa_municipal'], 2)}</td>
<td>
Posição do IPA entre os 20 municípios:
{fmt_int(linha['posicao_ipa_municipio'])}º de 20
</td>
</tr>

<tr>
<td>IPL médio</td>
<td>{fmt_num(linha['ipl_medio'], 2)}</td>
<td>
Percentil entre as áreas:
{fmt_pct(linha['percentil_ipl_area'], 1)}
</td>
</tr>

<tr>
<td>Prioridade Integrada média</td>
<td>{fmt_num(linha['prioridade_integrada_media'], 2)}</td>
<td>
Delta para média das áreas:
{fmt_delta(linha['delta_pi'])}
</td>
</tr>

</table>

</div>


<div class="section">

<h2>
Componentes ambientais
</h2>

<table>

<thead>

<tr>
<th>Componente</th>
<th>Área</th>
<th>Média das áreas</th>
<th>Diferença</th>
<th>Leitura</th>
</tr>

</thead>

<tbody>
{linhas_componentes}
</tbody>

</table>

<div class="figure">

<img
src="{escape(grafico_rel)}"
alt="Comparação dos componentes">

</div>

</div>


<div class="section">

<h2>
Composição territorial
</h2>

<table>

<tr>
<td>Área total</td>
<td>{fmt_num(linha['area_total_ha'], 2)} ha</td>
</tr>

<tr>
<td>Núcleo prioritário</td>
<td>{fmt_pct(linha['pct_area_nucleo'], 1)}</td>
</tr>

<tr>
<td>Suporte espacial</td>
<td>{fmt_pct(linha['pct_area_suporte'], 1)}</td>
</tr>

<tr>
<td>Prioridade excepcional</td>
<td>{fmt_pct(linha['pct_area_excepcional'], 1)}</td>
</tr>

<tr>
<td>Percentil de tamanho</td>
<td>{fmt_pct(linha['percentil_tamanho_area'], 1)}</td>
</tr>

</table>

</div>


<div class="section">

<h2>
Contexto do município
</h2>

<div class="explain">
{escape(str(municipio['explicacao_automatica_municipio']))}
</div>

<table>

<tr>
<td>Ranking municipal 10B</td>
<td>{fmt_int(municipio['rank_municipio_10b'])}º</td>
</tr>

<tr>
<td>PI média ponderada municipal</td>
<td>{fmt_num(municipio['prioridade_media_ponderada'], 2)}</td>
</tr>

<tr>
<td>IPA municipal</td>
<td>{fmt_num(municipio['ipa'], 2)}</td>
</tr>

<tr>
<td>Área prioritária municipal</td>
<td>{fmt_num(municipio['area_total_ha'], 1)} ha</td>
</tr>

<tr>
<td>Faixa excepcional municipal</td>
<td>{fmt_pct(municipio['pct_area_excepcional'], 1)}</td>
</tr>

<tr>
<td>Área com robustez Alta</td>
<td>{fmt_pct(municipio['pct_area_robustez_alta'], 1)}</td>
</tr>

</table>

</div>


<div class="section">

<h2>
Como interpretar esta explicação
</h2>

<p class="note">

Esta página não apresenta uma decomposição causal do ranking.
Ela explica a posição observada usando os próprios indicadores
calculados pelo VerdePrioriza e compara a área com o universo das
1.045 áreas finais. Um score ambiental elevado indica que aquele
componente é forte na caracterização da área, mas não deve ser
interpretado isoladamente como a causa do ranking. A Prioridade
Integrada permanece sendo o indicador de ordenação operacional.

</p>

<p class="note">

O resultado é uma ferramenta de triagem e apoio à decisão e deve ser
complementado por análise técnica, fundiária, cadastral e vistoria de
campo antes de qualquer intervenção ambiental.

</p>

</div>


</div>

</body>

</html>
"""


# ============================================================
# GERAR RELATÓRIOS
# ============================================================

registros_indice = []


for _, linha in df_areas.iterrows():

    codigo_ibge = str(
        linha["codigo_ibge"]
    )

    municipio_df = df_municipios.loc[
        df_municipios["codigo_ibge"].astype(str)
        ==
        codigo_ibge
    ]

    if municipio_df.empty:

        raise ValueError(
            "Município não encontrado para a área "
            f"{linha['codigo_area']}."
        )

    municipio = (
        municipio_df
        .iloc[0]
    )

    grafico = gerar_grafico_componentes(
        linha
    )

    html = gerar_html(
        linha,
        municipio,
        grafico,
    )

    nome = (
        "explicabilidade_"
        +
        str(
            linha["codigo_area"]
        )
        +
        ".html"
    )

    destino = (
        REPORTS_DIR
        /
        nome
    )

    destino.write_text(
        html,
        encoding="utf-8",
    )

    registros_indice.append(
        {
            "rank":
                linha["rank_area_geral"],

            "codigo_area":
                linha["codigo_area"],

            "municipio":
                linha["nome_municipio"],

            "pi":
                linha[
                    "prioridade_integrada_media"
                ],

            "robustez":
                normalizar_rotulo(
                    linha["robustez_area"]
                ),

            "principal_componente":
                linha[
                    "componente_1_nome"
                ],

            "arquivo":
                nome,
        }
    )


# ============================================================
# CSV
# ============================================================

csv_path = (
    OUTPUT_DIR
    /
    "explicabilidade_areas_10c.csv"
)

df_areas.to_csv(
    csv_path,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# ÍNDICE HTML
# ============================================================

linhas_indice = ""

for item in registros_indice:

    linhas_indice += f"""
    <tr>
        <td>{fmt_int(item['rank'])}</td>
        <td>{escape(str(item['codigo_area']))}</td>
        <td>{escape(str(item['municipio']))}</td>
        <td>{fmt_num(item['pi'], 2)}</td>
        <td>{escape(str(item['robustez']))}</td>
        <td>{escape(str(item['principal_componente']))}</td>
        <td>
            <a href="areas/{escape(str(item['arquivo']))}">
                Abrir explicação
            </a>
        </td>
    </tr>
    """


indice = f"""<!DOCTYPE html>

<html lang="pt-BR">

<head>

<meta charset="UTF-8">

<title>
VerdePrioriza — Explicabilidade 10C
</title>

<style>

body {{
    font-family: Arial, Helvetica, sans-serif;
    margin: 35px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
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

a {{
    text-decoration: none;
    font-weight: bold;
}}

</style>

</head>

<body>

<h1>
VerdePrioriza — Explicabilidade do Modelo
</h1>

<p>
Áreas explicadas:
<strong>{len(df_areas)}</strong>
</p>

<table>

<thead>

<tr>
<th>Rank</th>
<th>Código</th>
<th>Município</th>
<th>PI</th>
<th>Robustez</th>
<th>Componente de maior score</th>
<th>Relatório</th>
</tr>

</thead>

<tbody>
{linhas_indice}
</tbody>

</table>

</body>

</html>
"""


indice_path = (
    OUTPUT_DIR
    /
    "index_explicabilidade_10c.html"
)

indice_path.write_text(
    indice,
    encoding="utf-8",
)


# ============================================================
# FINAL
# ============================================================

total_areas = len(
    pd.read_sql(
        """
        SELECT codigo_area
        FROM analytics.vw_explicabilidade_area_10c;
        """,
        engine,
    )
)

print("=" * 72)
print("VERDEPRIORIZA - EXPLICABILIDADE 10C")
print("=" * 72)

print(
    f"\nÁreas disponíveis no modelo: "
    f"{total_areas:,}"
)

print(
    f"Relatórios gerados nesta execução: "
    f"{len(df_areas):,}"
)

print(
    "\nÍndice:"
)

print(
    indice_path
)

print(
    "\nCSV:"
)

print(
    csv_path
)

print(
    "\nRelatórios:"
)

print(
    REPORTS_DIR
)
