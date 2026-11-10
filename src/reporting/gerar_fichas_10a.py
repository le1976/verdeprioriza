import os
import argparse
from pathlib import Path
from html import escape

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL


# ============================================================
# VERDEPRIORIZA
# MÓDULO 10A
# FICHAS TÉCNICAS AUTOMÁTICAS
#
# Referência: 2024
# Versão: areas_9h_v1.1_2024
# ============================================================


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    ROOT_DIR
    / "outputs"
    / "reports"
    / "module10a"
)

FICHAS_DIR = (
    OUTPUT_DIR
    / "fichas"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

FICHAS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# ARGUMENTOS
# ============================================================

parser = argparse.ArgumentParser(
    description=(
        "Gera fichas técnicas automáticas "
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
# CONSULTA
# ============================================================

sql = """
SELECT *
FROM analytics.vw_ficha_area_10a
ORDER BY rank_area_geral;
"""

df = pd.read_sql(
    sql,
    engine,
)


# ============================================================
# VALIDAÇÃO
# ============================================================

if df.empty:
    raise ValueError(
        "analytics.vw_ficha_area_10a "
        "não retornou nenhuma área."
    )

print("=" * 72)
print("VERDEPRIORIZA - FICHAS TÉCNICAS 10A")
print("=" * 72)

print(
    f"\nÁreas disponíveis: "
    f"{len(df):,}"
)

print(
    f"Municípios: "
    f"{df['codigo_ibge'].nunique()}"
)


# ============================================================
# FILTROS OPCIONAIS
# ============================================================

if args.codigo_area:

    df = df.loc[
        df["codigo_area"]
        == args.codigo_area
    ].copy()

    if df.empty:
        raise ValueError(
            "Área não encontrada: "
            f"{args.codigo_area}"
        )

elif args.top:

    df = (
        df
        .head(
            args.top
        )
        .copy()
    )


# ============================================================
# FUNÇÕES DE FORMATAÇÃO
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

    return str(int(valor))


def fmt_pct(valor):

    if vazio(valor):
        return "-"

    return (
        fmt_num(
            valor,
            1
        )
        +
        "%"
    )


def fmt_texto(valor):

    if vazio(valor):
        return "-"

    return escape(
        str(valor)
    )


# ============================================================
# COMPONENTES
# ============================================================

COMPONENTES = {
    "score_hidrologia_medio":
        "Hidrologia",

    "score_conectividade_medio":
        "Conectividade",

    "score_declividade_medio":
        "Declividade",

    "score_elegibilidade_medio":
        "Elegibilidade",
}


def obter_componentes(linha):

    dados = []

    for coluna, nome in COMPONENTES.items():

        valor = linha[coluna]

        if not vazio(valor):

            dados.append(
                (
                    nome,
                    float(valor)
                )
            )

    dados.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    return dados


# ============================================================
# SÍNTESE AUTOMÁTICA
# ============================================================

def gerar_sintese(linha):

    componentes = obter_componentes(
        linha
    )

    if componentes:

        destaque_nome = (
            componentes[0][0]
        )

        destaque_valor = (
            componentes[0][1]
        )

    else:

        destaque_nome = (
            "não disponível"
        )

        destaque_valor = None

    partes = []

    partes.append(
        (
            f"A área {linha['codigo_area']} "
            f"ocupa a posição "
            f"{fmt_int(linha['rank_area_geral'])} "
            f"no ranking geral das áreas "
            f"prioritárias finais."
        )
    )

    partes.append(
        (
            f"Seu percentil de prioridade é "
            f"{fmt_num(linha['percentil_prioridade'], 1)}, "
            f"com classificação relativa "
            f"{linha['classe_relativa']}."
        )
    )

    partes.append(
        (
            f"A área total é de "
            f"{fmt_num(linha['area_total_ha'], 1)} ha, "
            f"dos quais "
            f"{fmt_pct(linha['pct_area_nucleo'])} "
            f"correspondem ao núcleo prioritário."
        )
    )

    if (
        not vazio(
            linha[
                "area_excepcional_ha"
            ]
        )
        and
        linha[
            "area_excepcional_ha"
        ] > 0
    ):

        partes.append(
            (
                f"A faixa de prioridade excepcional "
                f"representa "
                f"{fmt_num(linha['area_excepcional_ha'], 1)} ha "
                f"({fmt_pct(linha['pct_area_excepcional'])})."
            )
        )

    if destaque_valor is not None:

        partes.append(
            (
                f"Entre os quatro componentes ambientais, "
                f"o maior score observado é "
                f"{destaque_nome} "
                f"({fmt_num(destaque_valor, 1)})."
            )
        )

    partes.append(
        (
            f"A robustez da priorização foi "
            f"classificada como "
            f"{linha['robustez_area']}."
        )
    )

    return " ".join(
        partes
    )


# ============================================================
# BARRA DE SCORE
# ============================================================

def barra_score(
    nome,
    valor,
):

    if vazio(valor):

        largura = 0
        valor_txt = "-"

    else:

        largura = max(
            0,
            min(
                100,
                float(valor)
            )
        )

        valor_txt = fmt_num(
            valor,
            1
        )

    return f"""
    <div class="score-row">

        <div class="score-label">
            {escape(nome)}
        </div>

        <div class="score-bar-bg">

            <div
                class="score-bar"
                style="width:{largura}%">
            </div>

        </div>

        <div class="score-value">
            {valor_txt}
        </div>

    </div>
    """


# ============================================================
# TEMPLATE HTML
# ============================================================

def gerar_html(linha):

    componentes_html = ""

    for coluna, nome in COMPONENTES.items():

        componentes_html += (
            barra_score(
                nome,
                linha[coluna],
            )
        )

    sintese = gerar_sintese(
        linha
    )

    titulo = (
        f"Ficha Técnica — "
        f"{linha['codigo_area']}"
    )

    return f"""<!DOCTYPE html>

<html lang="pt-BR">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0">

<title>
{escape(titulo)}
</title>


<style>

body {{
    font-family: Arial, Helvetica, sans-serif;
    background: #f5f6f7;
    color: #222;
    margin: 0;
    padding: 30px;
}}

.container {{
    max-width: 1050px;
    margin: auto;
    background: white;
    padding: 35px;
    border-radius: 12px;
    box-shadow: 0 3px 15px rgba(0,0,0,0.10);
}}

h1 {{
    margin-bottom: 5px;
}}

.subtitle {{
    color: #666;
    margin-bottom: 30px;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(200px, 1fr)
        );
    gap: 15px;
    margin-bottom: 30px;
}}

.card {{
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
}}

.card-label {{
    font-size: 12px;
    color: #666;
    margin-bottom: 5px;
}}

.card-value {{
    font-size: 21px;
    font-weight: bold;
}}

.section {{
    margin-top: 35px;
}}

.section h2 {{
    border-bottom: 2px solid #ddd;
    padding-bottom: 8px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

td {{
    padding: 9px;
    border-bottom: 1px solid #eee;
}}

td:first-child {{
    font-weight: bold;
    width: 45%;
}}

.score-row {{
    display: grid;
    grid-template-columns:
        160px 1fr 60px;
    gap: 10px;
    align-items: center;
    margin-bottom: 12px;
}}

.score-bar-bg {{
    height: 16px;
    background: #ececec;
    border-radius: 8px;
    overflow: hidden;
}}

.score-bar {{
    height: 100%;
    background: #555;
}}

.score-value {{
    text-align: right;
    font-weight: bold;
}}

.summary {{
    padding: 18px;
    background: #f3f5f6;
    border-left: 5px solid #555;
    line-height: 1.6;
}}

.warning {{
    font-size: 13px;
    color: #666;
    margin-top: 35px;
    line-height: 1.5;
}}

.approved {{
    font-weight: bold;
}}

@media print {{

    body {{
        background: white;
        padding: 0;
    }}

    .container {{
        box-shadow: none;
        max-width: none;
    }}

}}

</style>

</head>


<body>

<div class="container">


<h1>
VerdePrioriza — Ficha Técnica
</h1>


<div class="subtitle">

Área
<strong>
{fmt_texto(linha['codigo_area'])}
</strong>

&nbsp;|&nbsp;

{fmt_texto(linha['nome_municipio'])}

&nbsp;|&nbsp;

Referência 2024

</div>



<div class="grid">


<div class="card">

<div class="card-label">
Ranking geral
</div>

<div class="card-value">
{fmt_int(linha['rank_area_geral'])}º
</div>

</div>



<div class="card">

<div class="card-label">
Percentil de prioridade
</div>

<div class="card-value">
{fmt_num(linha['percentil_prioridade'], 1)}
</div>

</div>



<div class="card">

<div class="card-label">
Prioridade Integrada
</div>

<div class="card-value">
{fmt_num(linha['prioridade_integrada_media'], 2)}
</div>

</div>



<div class="card">

<div class="card-label">
Robustez
</div>

<div class="card-value">
{fmt_texto(linha['robustez_area'])}
</div>

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
<td>Área núcleo</td>
<td>
{fmt_num(linha['area_nucleo_ha'], 2)} ha
({fmt_pct(linha['pct_area_nucleo'])})
</td>
</tr>

<tr>
<td>Área suporte</td>
<td>
{fmt_num(linha['area_suporte_ha'], 2)} ha
({fmt_pct(linha['pct_area_suporte'])})
</td>
</tr>

<tr>
<td>Prioridade excepcional</td>
<td>
{fmt_num(linha['area_excepcional_ha'], 2)} ha
({fmt_pct(linha['pct_area_excepcional'])})
</td>
</tr>

<tr>
<td>Número de células</td>
<td>{fmt_int(linha['numero_celulas'])}</td>
</tr>

</table>

</div>



<div class="section">

<h2>
Índices
</h2>

<table>

<tr>
<td>IPA municipal</td>
<td>{fmt_num(linha['ipa_municipal'], 2)}</td>
</tr>

<tr>
<td>IPL médio</td>
<td>{fmt_num(linha['ipl_medio'], 2)}</td>
</tr>

<tr>
<td>Prioridade Integrada média</td>
<td>{fmt_num(linha['prioridade_integrada_media'], 2)}</td>
</tr>

<tr>
<td>Prioridade Integrada mínima</td>
<td>{fmt_num(linha['prioridade_integrada_min'], 2)}</td>
</tr>

<tr>
<td>Prioridade Integrada máxima</td>
<td>{fmt_num(linha['prioridade_integrada_max'], 2)}</td>
</tr>

<tr>
<td>Classe relativa</td>
<td>{fmt_texto(linha['classe_relativa'])}</td>
</tr>

</table>

</div>



<div class="section">

<h2>
Componentes ambientais
</h2>

{componentes_html}

</div>



<div class="section">

<h2>
Caracterização ambiental
</h2>

<table>

<tr>
<td>Uso predominante</td>
<td>{fmt_texto(linha['uso_predominante'])}</td>
</tr>

<tr>
<td>Distância média à drenagem</td>
<td>
{fmt_num(linha['distancia_drenagem_media_m'], 1)} m
</td>
</tr>

<tr>
<td>Vegetação no entorno</td>
<td>
{fmt_pct(linha['vegetacao_entorno_media_pct'])}
</td>
</tr>

<tr>
<td>Declividade média</td>
<td>
{fmt_pct(linha['declividade_media_pct'])}
</td>
</tr>

<tr>
<td>Amplitude IPL média</td>
<td>
{fmt_num(linha['amplitude_ipl_media'], 2)}
</td>
</tr>

<tr>
<td>Coordenada de referência</td>
<td>
{fmt_num(linha['latitude'], 6)},
{fmt_num(linha['longitude'], 6)}
</td>
</tr>

</table>

</div>



<div class="section">

<h2>
Síntese automática
</h2>

<div class="summary">

{escape(sintese)}

</div>

</div>



<div class="section">

<h2>
Controle de qualidade
</h2>

<table>

<tr>
<td>Status da validação</td>
<td class="approved">
{fmt_texto(linha['status_validacao'])}
</td>
</tr>

<tr>
<td>Versão territorial</td>
<td>
{fmt_texto(linha['versao_areas'])}
</td>
</tr>

</table>

</div>



<div class="warning">

<strong>Importante:</strong>
o VerdePrioriza é uma ferramenta de triagem e apoio à decisão.
A classificação não representa, isoladamente, obrigação legal de
restauração, déficit de APP ou Reserva Legal, disponibilidade
fundiária ou recomendação automática de intervenção.
As áreas selecionadas devem ser confirmadas por análise técnica,
fundiária e vistoria de campo.

</div>


</div>

</body>

</html>
"""


# ============================================================
# GERAR FICHAS
# ============================================================

arquivos = []


for _, linha in df.iterrows():

    codigo = str(
        linha[
            "codigo_area"
        ]
    )

    nome_arquivo = (
        f"ficha_{codigo}.html"
    )

    destino = (
        FICHAS_DIR
        /
        nome_arquivo
    )

    html = gerar_html(
        linha
    )

    destino.write_text(
        html,
        encoding="utf-8",
    )

    arquivos.append(
        {
            "rank_area_geral":
                linha[
                    "rank_area_geral"
                ],

            "codigo_area":
                codigo,

            "municipio":
                linha[
                    "nome_municipio"
                ],

            "area_total_ha":
                linha[
                    "area_total_ha"
                ],

            "prioridade":
                linha[
                    "prioridade_integrada_media"
                ],

            "robustez":
                linha[
                    "robustez_area"
                ],

            "arquivo":
                nome_arquivo,
        }
    )


# ============================================================
# CSV
# ============================================================

csv_path = (
    OUTPUT_DIR
    /
    "fichas_areas_10a.csv"
)

df.to_csv(
    csv_path,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# ÍNDICE HTML
# ============================================================

linhas_indice = ""


for item in arquivos:

    linhas_indice += f"""

    <tr>

        <td>
        {fmt_int(item['rank_area_geral'])}
        </td>

        <td>
        {escape(item['codigo_area'])}
        </td>

        <td>
        {escape(str(item['municipio']))}
        </td>

        <td>
        {fmt_num(item['area_total_ha'], 1)}
        </td>

        <td>
        {fmt_num(item['prioridade'], 2)}
        </td>

        <td>
        {escape(str(item['robustez']))}
        </td>

        <td>

            <a href="fichas/{escape(item['arquivo'])}">
                Abrir ficha
            </a>

        </td>

    </tr>

    """


indice_html = f"""<!DOCTYPE html>

<html lang="pt-BR">

<head>

<meta charset="UTF-8">

<title>
VerdePrioriza — Fichas Técnicas
</title>

<style>

body {{
    font-family: Arial, sans-serif;
    margin: 35px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th,
td {{
    padding: 8px;
    border-bottom: 1px solid #ddd;
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
VerdePrioriza — Fichas Técnicas
</h1>


<p>
Áreas geradas: {len(df)}
</p>


<table>

<thead>

<tr>
<th>Rank</th>
<th>Código</th>
<th>Município</th>
<th>Área (ha)</th>
<th>PI</th>
<th>Robustez</th>
<th>Ficha</th>
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
    "index_fichas_10a.html"
)

indice_path.write_text(
    indice_html,
    encoding="utf-8",
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 72)
print(
    "FICHAS GERADAS COM SUCESSO"
)
print("=" * 72)

print(
    f"\nFichas criadas: "
    f"{len(df):,}"
)

print(
    "\nDiretório:"
)

print(
    FICHAS_DIR
)

print(
    "\nÍndice:"
)

print(
    indice_path
)

print(
    "\nCSV consolidado:"
)

print(
    csv_path
)

if len(df) > 0:

    primeira = (
        FICHAS_DIR
        /
        (
            "ficha_"
            +
            str(
                df.iloc[0][
                    "codigo_area"
                ]
            )
            +
            ".html"
        )
    )

    print(
        "\nPrimeira ficha:"
    )

    print(
        primeira
    )
