import json

import pandas as pd
import plotly.express as px
import streamlit as st

from data import (
    carregar_base_ipa,
    carregar_historico_cobertura,
    carregar_historico_fogo,
    carregar_historico_inpe,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="VerdePrioriza",
    page_icon="🌱",
    layout="wide",
)

ANO_REFERENCIA = 2024

st.title("🌱 VerdePrioriza")

st.caption(
    "Plataforma de Inteligência para Priorização Ambiental "
    "— Estado de São Paulo — Referência 2024"
)


# ============================================================
# DADOS
# ============================================================

gdf = carregar_base_ipa()

if len(gdf) != 645:
    st.warning(
        f"Foram encontrados {len(gdf)} municípios. "
        "O esperado é 645."
    )


# ============================================================
# FILTROS
# ============================================================

st.sidebar.header("Filtros")

classes_disponiveis = [
    "Muito alta",
    "Alta",
    "Media",
    "Baixa",
    "Muito baixa",
]

classes_selecionadas = st.sidebar.multiselect(
    "Classificação IPA",
    options=classes_disponiveis,
    default=classes_disponiveis,
)

estabilidades = sorted(
    gdf["estabilidade"]
    .dropna()
    .unique()
)

estabilidades_selecionadas = st.sidebar.multiselect(
    "Estabilidade",
    options=estabilidades,
    default=estabilidades,
)

ipa_minimo = st.sidebar.slider(
    "IPA mínimo",
    min_value=0,
    max_value=100,
    value=0,
)

dados = gdf[
    gdf["classificacao"].isin(classes_selecionadas)
    & gdf["estabilidade"].isin(estabilidades_selecionadas)
    & (gdf["ipa"] >= ipa_minimo)
].copy()


# ============================================================
# KPIs
# ============================================================

st.subheader("Visão geral")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Municípios",
    f"{len(dados):,}".replace(",", "."),
)

if not dados.empty:
    col2.metric(
        "IPA médio",
        f"{dados['ipa'].mean():.1f}",
    )

    alta_prioridade = (
        dados["classificacao"]
        .isin(["Alta", "Muito alta"])
        .sum()
    )

    col3.metric(
        "Alta / Muito alta",
        int(alta_prioridade),
    )

    lider = (
        dados
        .sort_values("ipa", ascending=False)
        .iloc[0]
    )

    col4.metric(
        "Maior IPA",
        f"{lider['ipa']:.1f}",
        lider["nome_municipio"],
    )
else:
    col2.metric("IPA médio", "—")
    col3.metric("Alta / Muito alta", 0)
    col4.metric("Maior IPA", "—")


# ============================================================
# ABAS
# ============================================================

tab_mapa, tab_ranking, tab_municipio, tab_metodologia = st.tabs(
    [
        "🗺️ Mapa",
        "🏆 Ranking",
        "🔎 Município",
        "📘 Metodologia",
    ]
)


# ============================================================
# ABA 1 — MAPA
# ============================================================

with tab_mapa:
    st.subheader("Mapa de Prioridade Ambiental")

    if dados.empty:
        st.info("Nenhum município atende aos filtros selecionados.")
    else:
        geojson = json.loads(gdf.to_json())

        mapa_df = pd.DataFrame(
            dados.drop(
                columns="geom",
                errors="ignore",
            )
        )

        fig_mapa = px.choropleth_map(
            mapa_df,
            geojson=geojson,
            locations="codigo_ibge",
            featureidkey="properties.codigo_ibge",
            color="ipa",
            color_continuous_scale="YlOrRd",
            range_color=(0, 100),
            map_style="carto-positron",
            center={
                "lat": -22.3,
                "lon": -48.5,
            },
            zoom=5.2,
            opacity=0.75,
            hover_name="nome_municipio",
            hover_data={
                "codigo_ibge": False,
                "ipa": ":.1f",
                "classificacao": True,
                "rank_ipa": True,
                "estabilidade": True,
            },
            labels={
                "ipa": "IPA",
                "classificacao": "Classificação",
                "rank_ipa": "Posição",
                "estabilidade": "Estabilidade",
            },
        )

        fig_mapa.update_layout(
            margin=dict(
                l=0,
                r=0,
                t=0,
                b=0,
            ),
            height=650,
        )

        st.plotly_chart(
            fig_mapa,
            width="stretch",
        )

        distribuicao = (
            dados["classificacao"]
            .value_counts()
            .reindex(
                [
                    "Muito baixa",
                    "Baixa",
                    "Media",
                    "Alta",
                    "Muito alta",
                ],
                fill_value=0,
            )
            .reset_index()
        )

        distribuicao.columns = [
            "Classificação",
            "Municípios",
        ]

        fig_dist = px.bar(
            distribuicao,
            x="Classificação",
            y="Municípios",
            text="Municípios",
            title=(
                "Distribuição dos municípios "
                "por classe de prioridade"
            ),
        )

        st.plotly_chart(
            fig_dist,
            width="stretch",
        )

        st.subheader(
            "Prioridade × Sensibilidade Metodológica"
        )

        fig_sensibilidade = px.scatter(
            dados,
            x="ipa",
            y="amplitude_cenarios",
            hover_name="nome_municipio",
            hover_data={
                "rank_ipa": True,
                "classificacao": True,
                "estabilidade": True,
            },
            labels={
                "ipa": "IPA",
                "amplitude_cenarios": "Amplitude entre cenários",
            },
            title=(
                "IPA elevado e baixa amplitude "
                "indicam prioridade mais robusta"
            ),
        )

        st.plotly_chart(
            fig_sensibilidade,
            width="stretch",
        )


# ============================================================
# ABA 2 — RANKING
# ============================================================

with tab_ranking:
    st.subheader("Ranking de Prioridade Ambiental")

    if dados.empty:
        st.info("Nenhum município atende aos filtros selecionados.")
    else:
        ranking = (
            dados[
                [
                    "rank_ipa",
                    "nome_municipio",
                    "ipa",
                    "classificacao",
                    "estabilidade",
                    "score_vegetacao",
                    "score_perda_vegetacao",
                    "score_pressao_agropecuaria",
                    "score_fogo",
                ]
            ]
            .sort_values("rank_ipa")
            .copy()
        )

        ranking.columns = [
            "Posição",
            "Município",
            "IPA",
            "Classificação",
            "Estabilidade",
            "Baixa cobertura",
            "Perda vegetação",
            "Pressão agropecuária",
            "Fogo",
        ]

        st.dataframe(
            ranking,
            width="stretch",
            hide_index=True,
            column_config={
                "IPA": st.column_config.ProgressColumn(
                    "IPA",
                    min_value=0,
                    max_value=100,
                    format="%.1f",
                ),
            },
        )

        csv = ranking.to_csv(
            index=False,
            encoding="utf-8-sig",
        )

        st.download_button(
            label="Baixar ranking filtrado em CSV",
            data=csv,
            file_name="verdeprioriza_ranking_2024.csv",
            mime="text/csv",
        )


# ============================================================
# ABA 3 — MUNICÍPIO
# ============================================================

with tab_municipio:
    st.subheader("Diagnóstico Municipal")

    municipios = (
        gdf["nome_municipio"]
        .sort_values()
        .tolist()
    )

    municipio_selecionado = st.selectbox(
        "Selecione o município",
        municipios,
    )

    municipio = (
        gdf[
            gdf["nome_municipio"]
            == municipio_selecionado
        ]
        .iloc[0]
    )

    codigo = municipio["codigo_ibge"]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "IPA",
        f"{municipio['ipa']:.1f}",
    )

    c2.metric(
        "Ranking estadual",
        f"{int(municipio['rank_ipa'])}º",
    )

    c3.metric(
        "Classificação",
        municipio["classificacao"],
    )

    c4.metric(
        "Estabilidade",
        municipio["estabilidade"],
    )

    st.subheader("Indicadores ambientais")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Cobertura natural",
        f"{municipio['cobertura_natural_pct']:.1f}%",
    )

    c2.metric(
        "Agropecuária",
        f"{municipio['agropecuaria_pct']:.1f}%",
    )

    c3.metric(
        "Perda líquida em 10 anos",
        f"{municipio['perda_liquida_vegetacao_10a_pct']:.2f}%",
    )

    c4, c5, c6 = st.columns(3)

    c4.metric(
        "Fogo médio — 5 anos",
        f"{municipio['fogo_media_5a_pct']:.2f}%",
    )

    c5.metric(
        "Carga de fogo — 10 anos",
        f"{municipio['fogo_carga_10a_pct']:.2f}%",
    )

    c6.metric(
        "Focos INPE / 100 km²",
        f"{municipio['focos_inpe_100km2']:.2f}",
    )

    st.subheader("Decomposição da prioridade")

    componentes = pd.DataFrame(
        {
            "Dimensão": [
                "Baixa cobertura",
                "Perda de vegetação",
                "Pressão agropecuária",
                "Fogo",
            ],
            "Score": [
                municipio["score_vegetacao"],
                municipio["score_perda_vegetacao"],
                municipio["score_pressao_agropecuaria"],
                municipio["score_fogo"],
            ],
        }
    )

    fig_componentes = px.bar(
        componentes,
        x="Score",
        y="Dimensão",
        orientation="h",
        range_x=[0, 100],
        text_auto=".1f",
        title="Scores relativos que compõem o IPA",
    )

    st.plotly_chart(
        fig_componentes,
        width="stretch",
    )

    cenarios = pd.DataFrame(
        {
            "Cenário": [
                "Principal",
                "Conservação",
                "Distúrbio recente",
            ],
            "IPA": [
                municipio["ipa"],
                municipio["ipa_cenario_conservacao"],
                municipio["ipa_cenario_disturbio"],
            ],
        }
    )

    fig_cenarios = px.bar(
        cenarios,
        x="Cenário",
        y="IPA",
        range_y=[0, 100],
        text_auto=".1f",
        title="Sensibilidade aos diferentes pesos",
    )

    st.plotly_chart(
        fig_cenarios,
        width="stretch",
    )

    historico = carregar_historico_cobertura(
        codigo
    )

    st.subheader(
        "Evolução da cobertura e uso da terra"
    )

    if not historico.empty:
        fig_cobertura = px.line(
            historico,
            x="ano",
            y=[
                "vegetacao_pct",
                "agropecuaria_pct",
            ],
            labels={
                "ano": "Ano",
                "value": "% da área mapeada",
                "variable": "Indicador",
            },
            title=(
                f"Evolução territorial — "
                f"{municipio_selecionado}"
            ),
        )

        st.plotly_chart(
            fig_cobertura,
            width="stretch",
        )
    else:
        st.info(
            "Não há histórico de cobertura disponível "
            "para este município."
        )

    historico_fogo = carregar_historico_fogo(
        codigo
    )

    if not historico_fogo.empty:
        fig_fogo = px.bar(
            historico_fogo,
            x="ano",
            y="area_queimada_pct",
            labels={
                "ano": "Ano",
                "area_queimada_pct": "Área queimada (%)",
            },
            title="Histórico anual de área queimada",
        )

        st.plotly_chart(
            fig_fogo,
            width="stretch",
        )
    else:
        st.info(
            "Não há histórico de fogo disponível "
            "para este município."
        )

    historico_inpe = carregar_historico_inpe(
        codigo
    )

    if not historico_inpe.empty:
        fig_inpe = px.line(
            historico_inpe,
            x="ano",
            y="focos_por_100_km2",
            markers=True,
            labels={
                "ano": "Ano",
                "focos_por_100_km2": "Focos / 100 km²",
            },
            title=(
                "Focos detectados pelo satélite "
                "de referência do INPE"
            ),
        )

        st.plotly_chart(
            fig_inpe,
            width="stretch",
        )
    else:
        st.info(
            "Não há histórico de focos INPE disponível "
            "para este município."
        )


# ============================================================
# ABA 4 — METODOLOGIA
# ============================================================

with tab_metodologia:
    st.header("Metodologia do VerdePrioriza")

    st.markdown(
        """
### Objetivo

O Índice de Prioridade Ambiental — IPA é um indicador
relativo utilizado para apoiar a triagem territorial dos
municípios do Estado de São Paulo.

Ele não representa déficit legal de vegetação, irregularidade
ambiental, déficit de Reserva Legal ou de APP.

---

### Ano de referência

**2024**

---

### Dimensões do IPA

**V — Baixa cobertura natural**

Representa a posição relativa do município em relação à
cobertura natural observada.

**D — Dinâmica recente**

Representa a redução líquida da cobertura natural no período
de dez anos.

**P — Pressão agropecuária**

Utilizada como proxy da intensidade de ocupação agropecuária
do território.

**F — Fogo**

Combina pressão recente e recorrência histórica do fogo.

---

### Fórmula principal

IPA = 0,35V + 0,25D + 0,20P + 0,20F

A dimensão fogo é calculada por:

F = 0,60 F_recente + 0,40 F_histórico

---

### Interpretação dos scores

Os scores variam de 0 a 100 e representam posição relativa
entre os municípios paulistas.

Um score 90 não significa 90% de déficit ambiental.

Significa que o município apresenta pressão relativa elevada
naquela dimensão em comparação ao conjunto analisado.

---

### Sensibilidade

São calculados cenários alternativos de ponderação para avaliar
quanto o resultado depende da escolha dos pesos.

Municípios que permanecem altamente prioritários nos diferentes
cenários possuem maior robustez metodológica.
        """
    )