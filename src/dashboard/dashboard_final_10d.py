import os
import re
import json
import base64
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components

from dotenv import load_dotenv
from sqlalchemy import create_engine, URL


# ============================================================
# VERDEPRIORIZA
# MÓDULO 10D
# DASHBOARD FINAL INTEGRADO
# ============================================================


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="VerdePrioriza — Dashboard Final",
    page_icon="🌱",
    layout="wide",
)

ROOT_DIR = Path(__file__).resolve().parents[2]

REPORT_10A_DIR = (
    ROOT_DIR
    / "outputs"
    / "reports"
    / "module10a"
    / "fichas"
)

REPORT_10C_DIR = (
    ROOT_DIR
    / "outputs"
    / "reports"
    / "module10c"
    / "areas"
)

CHARTS_10C_DIR = (
    ROOT_DIR
    / "outputs"
    / "reports"
    / "module10c"
    / "charts"
)

MAPS_9I_DIR = (
    ROOT_DIR
    / "outputs"
    / "maps"
    / "module9i"
)


# ============================================================
# BANCO
# ============================================================

@st.cache_resource
def get_engine():

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

    return create_engine(
        url,
        pool_pre_ping=True,
    )


@st.cache_data(
    ttl=600
)
def carregar_areas():

    return pd.read_sql(
        """
        SELECT *
        FROM analytics.vw_dashboard_area_10d
        ORDER BY rank_area_geral;
        """,
        get_engine(),
    )


@st.cache_data(
    ttl=600
)
def carregar_municipios():

    return pd.read_sql(
        """
        SELECT *
        FROM analytics.vw_dashboard_municipio_10d
        ORDER BY rank_municipio_10b;
        """,
        get_engine(),
    )


# ============================================================
# FUNÇÕES
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


def rotulo_robustez(valor):

    if valor == "Media":
        return "Média"

    return str(valor)


def weighted_mean(
    df,
    value_col,
    weight_col,
):

    temp = df[
        [
            value_col,
            weight_col,
        ]
    ].dropna()

    if temp.empty:
        return None

    peso = temp[
        weight_col
    ].sum()

    if peso == 0:
        return None

    return (
        (
            temp[value_col]
            *
            temp[weight_col]
        ).sum()
        /
        peso
    )


def color_robustez(valor):

    if valor == "Alta":
        return [
            40,
            120,
            70,
            160,
        ]

    if valor == "Media":
        return [
            190,
            150,
            50,
            160,
        ]

    return [
        150,
        80,
        70,
        160,
    ]


def criar_feature_collection(df):

    features = []

    for _, r in df.iterrows():

        geojson_text = (
            r.get(
                "geojson_area"
            )
        )

        if (
            geojson_text is None
            or pd.isna(
                geojson_text
            )
        ):
            continue

        try:
            geometry = json.loads(
                geojson_text
            )
        except Exception:
            continue

        features.append(
            {
                "type":
                    "Feature",

                "geometry":
                    geometry,

                "properties":
                    {
                        "codigo_area":
                            str(
                                r[
                                    "codigo_area"
                                ]
                            ),

                        "municipio":
                            str(
                                r[
                                    "nome_municipio"
                                ]
                            ),

                        "rank":
                            int(
                                r[
                                    "rank_area_geral"
                                ]
                            ),

                        "pi":
                            round(
                                float(
                                    r[
                                        "prioridade_integrada_media"
                                    ]
                                ),
                                2,
                            ),

                        "robustez":
                            rotulo_robustez(
                                r[
                                    "robustez_area"
                                ]
                            ),

                        "area_ha":
                            round(
                                float(
                                    r[
                                        "area_total_ha"
                                    ]
                                ),
                                1,
                            ),

                        "fill_color":
                            color_robustez(
                                r[
                                    "robustez_area"
                                ]
                            ),
                    },
            }
        )

    return {
        "type":
            "FeatureCollection",

        "features":
            features,
    }


def imagem_para_data_uri(
    caminho,
):

    caminho = Path(
        caminho
    )

    if not caminho.exists():
        return None

    suffix = (
        caminho
        .suffix
        .lower()
    )

    mime = (
        "image/png"
        if suffix == ".png"
        else "image/jpeg"
    )

    encoded = (
        base64
        .b64encode(
            caminho.read_bytes()
        )
        .decode("ascii")
    )

    return (
        f"data:{mime};base64,{encoded}"
    )


def incorporar_imagens_locais(
    html_text,
    base_dir,
):

    pattern = re.compile(
        r'src=["\']([^"\']+)["\']',
        flags=re.IGNORECASE,
    )

    def substituir(match):

        src = match.group(1)

        if (
            src.startswith(
                "data:"
            )
            or src.startswith(
                "http://"
            )
            or src.startswith(
                "https://"
            )
        ):
            return match.group(0)

        caminho = (
            base_dir
            /
            src
        ).resolve()

        if not caminho.exists():
            return match.group(0)

        uri = imagem_para_data_uri(
            caminho
        )

        if uri is None:
            return match.group(0)

        return (
            'src="'
            +
            uri
            +
            '"'
        )

    return pattern.sub(
        substituir,
        html_text,
    )


def carregar_html_local(
    caminho,
):

    caminho = Path(
        caminho
    )

    if not caminho.exists():
        return None

    texto = caminho.read_text(
        encoding="utf-8"
    )

    return incorporar_imagens_locais(
        texto,
        caminho.parent,
    )


def exibir_html_e_download(
    caminho,
    altura=1100,
):

    caminho = Path(
        caminho
    )

    if not caminho.exists():

        st.info(
            "Arquivo ainda não encontrado: "
            +
            str(
                caminho
            )
        )

        return

    html_text = carregar_html_local(
        caminho
    )

    components.html(
        html_text,
        height=altura,
        scrolling=True,
    )

    st.download_button(
        label=(
            "Baixar HTML"
        ),
        data=caminho.read_bytes(),
        file_name=caminho.name,
        mime="text/html",
        use_container_width=True,
    )


# ============================================================
# CARREGAMENTO
# ============================================================

try:

    areas = carregar_areas()

    municipios = (
        carregar_municipios()
    )

except Exception as exc:

    st.error(
        "Não foi possível carregar "
        "as views do Módulo 10D."
    )

    st.exception(
        exc
    )

    st.stop()


if areas.empty:

    st.error(
        "Nenhuma área disponível "
        "em analytics.vw_dashboard_area_10d."
    )

    st.stop()


# ============================================================
# CABEÇALHO
# ============================================================

st.title(
    "🌱 VerdePrioriza — Dashboard Final Integrado"
)

st.caption(
    "Priorização ambiental territorial | "
    "20 municípios | referência 2024 | "
    "areas_9h_v1.1_2024"
)


# ============================================================
# FILTROS
# ============================================================

st.sidebar.header(
    "Filtros"
)

lista_municipios = sorted(
    areas[
        "nome_municipio"
    ]
    .dropna()
    .unique()
    .tolist()
)

municipios_sel = (
    st.sidebar
    .multiselect(
        "Municípios",
        options=lista_municipios,
        default=[],
        placeholder=(
            "Todos os municípios"
        ),
    )
)

robustez_opcoes = [
    "Alta",
    "Media",
    "Baixa",
]

robustez_sel = (
    st.sidebar
    .multiselect(
        "Robustez",
        options=robustez_opcoes,
        format_func=rotulo_robustez,
        default=[],
        placeholder=(
            "Todas as classes"
        ),
    )
)

pi_min = float(
    areas[
        "prioridade_integrada_media"
    ].min()
)

pi_max = float(
    areas[
        "prioridade_integrada_media"
    ].max()
)

pi_sel = (
    st.sidebar
    .slider(
        "Prioridade Integrada",
        min_value=round(
            pi_min,
            2,
        ),
        max_value=round(
            pi_max,
            2,
        ),
        value=(
            round(
                pi_min,
                2,
            ),
            round(
                pi_max,
                2,
            ),
        ),
        step=0.10,
    )
)

somente_excepcional = (
    st.sidebar
    .checkbox(
        "Somente áreas com faixa excepcional",
        value=False,
    )
)

top_n = (
    st.sidebar
    .selectbox(
        "Ranking exibido",
        options=[
            20,
            50,
            100,
            250,
            1045,
        ],
        index=1,
    )
)


# ============================================================
# APLICAR FILTROS
# ============================================================

filtrado = areas.copy()

if municipios_sel:

    filtrado = filtrado[
        filtrado[
            "nome_municipio"
        ].isin(
            municipios_sel
        )
    ]

if robustez_sel:

    filtrado = filtrado[
        filtrado[
            "robustez_area"
        ].isin(
            robustez_sel
        )
    ]

filtrado = filtrado[
    filtrado[
        "prioridade_integrada_media"
    ].between(
        pi_sel[0],
        pi_sel[1],
    )
]

if somente_excepcional:

    filtrado = filtrado[
        filtrado[
            "area_excepcional_ha"
        ] > 0
    ]


# ============================================================
# KPIs
# ============================================================

area_total = (
    filtrado[
        "area_total_ha"
    ].sum()
)

area_excepcional = (
    filtrado[
        "area_excepcional_ha"
    ].sum()
)

pi_ponderada = weighted_mean(
    filtrado,
    "prioridade_integrada_media",
    "area_total_ha",
)

municipios_filtrados = (
    filtrado[
        "codigo_ibge"
    ].nunique()
)

k1, k2, k3, k4, k5 = st.columns(
    5
)

k1.metric(
    "Áreas",
    fmt_int(
        len(
            filtrado
        )
    ),
)

k2.metric(
    "Municípios",
    fmt_int(
        municipios_filtrados
    ),
)

k3.metric(
    "Área priorizada",
    (
        fmt_num(
            area_total,
            1,
        )
        +
        " ha"
    ),
)

k4.metric(
    "PI média ponderada",
    fmt_num(
        pi_ponderada,
        2,
    ),
)

pct_excepcional = (
    (
        area_excepcional
        /
        area_total
        *
        100
    )
    if area_total > 0
    else 0
)

k5.metric(
    "Área excepcional",
    fmt_pct(
        pct_excepcional,
        1,
    ),
)


# ============================================================
# ABAS
# ============================================================

(
    tab_visao,
    tab_mapa,
    tab_areas,
    tab_municipios,
    tab_detalhe,
    tab_mapas_tecnicos,
) = st.tabs(
    [
        "Visão geral",
        "Mapa interativo",
        "Ranking de áreas",
        "Municípios",
        "Detalhe da área",
        "Mapas técnicos",
    ]
)


# ============================================================
# VISÃO GERAL
# ============================================================

with tab_visao:

    st.subheader(
        "Distribuição territorial"
    )

    resumo_mun = (
        filtrado
        .groupby(
            "nome_municipio",
            as_index=False,
        )
        .agg(
            area_total_ha=(
                "area_total_ha",
                "sum",
            ),
            numero_areas=(
                "codigo_area",
                "count",
            ),
        )
        .sort_values(
            "area_total_ha",
            ascending=False,
        )
    )

    c1, c2 = st.columns(
        2
    )

    with c1:

        st.markdown(
            "**Área prioritária por município**"
        )

        st.bar_chart(
            resumo_mun.set_index(
                "nome_municipio"
            )[
                "area_total_ha"
            ]
        )

    with c2:

        st.markdown(
            "**Número de áreas por município**"
        )

        st.bar_chart(
            resumo_mun.set_index(
                "nome_municipio"
            )[
                "numero_areas"
            ]
        )

    st.subheader(
        "Robustez"
    )

    robustez_resumo = (
        filtrado
        .assign(
            robustez_exibicao=(
                filtrado[
                    "robustez_area"
                ]
                .map(
                    rotulo_robustez
                )
            )
        )
        .groupby(
            "robustez_exibicao",
            as_index=False,
        )
        .agg(
            area_total_ha=(
                "area_total_ha",
                "sum",
            ),
            numero_areas=(
                "codigo_area",
                "count",
            ),
        )
    )

    st.dataframe(
        robustez_resumo,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader(
        "Top componentes ambientais"
    )

    componentes_resumo = (
        filtrado[
            "componente_1_nome"
        ]
        .value_counts()
        .rename_axis(
            "componente"
        )
        .reset_index(
            name="numero_areas"
        )
    )

    st.bar_chart(
        componentes_resumo.set_index(
            "componente"
        )[
            "numero_areas"
        ]
    )


# ============================================================
# MAPA
# ============================================================

with tab_mapa:

    st.subheader(
        "Áreas prioritárias filtradas"
    )

    if filtrado.empty:

        st.warning(
            "Nenhuma área corresponde "
            "aos filtros selecionados."
        )

    else:

        geojson = criar_feature_collection(
            filtrado
        )

        lat = (
            filtrado[
                "latitude_mapa"
            ]
            .dropna()
            .mean()
        )

        lon = (
            filtrado[
                "longitude_mapa"
            ]
            .dropna()
            .mean()
        )

        if pd.isna(
            lat
        ):
            lat = -21.2

        if pd.isna(
            lon
        ):
            lon = -48.5

        layer = pdk.Layer(
            "GeoJsonLayer",
            geojson,
            pickable=True,
            stroked=True,
            filled=True,
            get_fill_color=(
                "properties.fill_color"
            ),
            get_line_color=[
                60,
                60,
                60,
                180,
            ],
            line_width_min_pixels=1,
        )

        deck = pdk.Deck(
            layers=[
                layer
            ],
            initial_view_state=(
                pdk.ViewState(
                    latitude=float(
                        lat
                    ),
                    longitude=float(
                        lon
                    ),
                    zoom=7.2,
                    pitch=0,
                )
            ),
            tooltip={
                "html":
                    (
                        "<b>{municipio}</b><br/>"
                        "{codigo_area}<br/>"
                        "Rank: {rank}<br/>"
                        "PI: {pi}<br/>"
                        "Robustez: {robustez}<br/>"
                        "Área: {area_ha} ha"
                    ),
                "style":
                    {
                        "backgroundColor":
                            "rgba(30,30,30,0.85)",
                        "color":
                            "white",
                    },
            },
        )

        st.pydeck_chart(
            deck,
            use_container_width=True,
        )

        st.caption(
            "Cores representam a classe de robustez. "
            "O mapa é ferramenta de triagem; "
            "não substitui validação cadastral e de campo."
        )


# ============================================================
# RANKING DE ÁREAS
# ============================================================

with tab_areas:

    st.subheader(
        "Ranking das áreas"
    )

    tabela = (
        filtrado
        .sort_values(
            "rank_area_geral"
        )
        .head(
            int(
                top_n
            )
        )
        [
            [
                "rank_area_geral",
                "codigo_area",
                "nome_municipio",
                "area_total_ha",
                "prioridade_integrada_media",
                "percentil_prioridade",
                "robustez_area",
                "componente_1_nome",
                "posicao_ipa_municipio",
            ]
        ]
        .copy()
    )

    tabela[
        "robustez_area"
    ] = tabela[
        "robustez_area"
    ].map(
        rotulo_robustez
    )

    tabela.columns = [
        "Rank",
        "Código",
        "Município",
        "Área (ha)",
        "PI",
        "Percentil",
        "Robustez",
        "Componente destaque",
        "Posição IPA municipal",
    ]

    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True,
    )

    csv = tabela.to_csv(
        index=False
    ).encode(
        "utf-8-sig"
    )

    st.download_button(
        "Baixar ranking filtrado em CSV",
        data=csv,
        file_name=(
            "ranking_areas_10d_filtrado.csv"
        ),
        mime="text/csv",
    )


# ============================================================
# MUNICÍPIOS
# ============================================================

with tab_municipios:

    st.subheader(
        "Comparação dos 20 municípios"
    )

    mun = municipios.copy()

    if municipios_sel:

        mun = mun[
            mun[
                "nome_municipio"
            ].isin(
                municipios_sel
            )
        ]

    tabela_mun = mun[
        [
            "rank_municipio_10b",
            "nome_municipio",
            "numero_areas",
            "area_total_ha",
            "prioridade_media_ponderada",
            "ipa",
            "pct_area_excepcional",
            "pct_area_robustez_alta",
            "uso_predominante_areas",
        ]
    ].copy()

    tabela_mun.columns = [
        "Rank",
        "Município",
        "Áreas",
        "Área (ha)",
        "PI média",
        "IPA",
        "% excepcional",
        "% robustez Alta",
        "Uso predominante nas áreas",
    ]

    st.dataframe(
        tabela_mun,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        "**Prioridade Integrada média ponderada por município**"
    )

    st.bar_chart(
        mun.set_index(
            "nome_municipio"
        )[
            "prioridade_media_ponderada"
        ]
    )

    municipio_detalhe = (
        st.selectbox(
            "Explicação municipal",
            options=(
                mun[
                    "nome_municipio"
                ]
                .tolist()
            ),
        )
        if not mun.empty
        else None
    )

    if municipio_detalhe:

        linha_mun = (
            mun.loc[
                mun[
                    "nome_municipio"
                ]
                ==
                municipio_detalhe
            ]
            .iloc[0]
        )

        st.info(
            str(
                linha_mun[
                    "explicacao_automatica_municipio"
                ]
            )
        )


# ============================================================
# DETALHE DA ÁREA
# ============================================================

with tab_detalhe:

    st.subheader(
        "Área individual"
    )

    if filtrado.empty:

        st.warning(
            "Não há área disponível "
            "com os filtros atuais."
        )

    else:

        opcoes = (
            filtrado
            .sort_values(
                "rank_area_geral"
            )
            [
                "codigo_area"
            ]
            .tolist()
        )

        codigo = st.selectbox(
            "Selecione a área",
            options=opcoes,
        )

        linha = (
            filtrado.loc[
                filtrado[
                    "codigo_area"
                ]
                ==
                codigo
            ]
            .iloc[0]
        )

        d1, d2, d3, d4 = st.columns(
            4
        )

        d1.metric(
            "Ranking",
            (
                fmt_int(
                    linha[
                        "rank_area_geral"
                    ]
                )
                +
                "º"
            ),
        )

        d2.metric(
            "PI",
            fmt_num(
                linha[
                    "prioridade_integrada_media"
                ],
                2,
            ),
        )

        d3.metric(
            "Área",
            (
                fmt_num(
                    linha[
                        "area_total_ha"
                    ],
                    2,
                )
                +
                " ha"
            ),
        )

        d4.metric(
            "Robustez",
            rotulo_robustez(
                linha[
                    "robustez_area"
                ]
            ),
        )

        st.info(
            str(
                linha[
                    "explicacao_automatica"
                ]
            )
        )

        ficha_tab, expl_tab = st.tabs(
            [
                "Ficha técnica 10A",
                "Explicabilidade 10C",
            ]
        )

        with ficha_tab:

            caminho_10a = (
                REPORT_10A_DIR
                /
                (
                    "ficha_"
                    +
                    codigo
                    +
                    ".html"
                )
            )

            exibir_html_e_download(
                caminho_10a,
                altura=1200,
            )

        with expl_tab:

            caminho_10c = (
                REPORT_10C_DIR
                /
                (
                    "explicabilidade_"
                    +
                    codigo
                    +
                    ".html"
                )
            )

            exibir_html_e_download(
                caminho_10c,
                altura=1300,
            )


# ============================================================
# MAPAS TÉCNICOS
# ============================================================

with tab_mapas_tecnicos:

    st.subheader(
        "Mapas consolidados do Módulo 9I"
    )

    mapas = [
        (
            "Percentil de prioridade",
            (
                MAPS_9I_DIR
                /
                "areas_prioritarias_percentil_2024.png"
            ),
        ),
        (
            "Robustez",
            (
                MAPS_9I_DIR
                /
                "areas_prioritarias_robustez_2024.png"
            ),
        ),
        (
            "Top 30 áreas",
            (
                MAPS_9I_DIR
                /
                "top30_areas_prioritarias_2024.png"
            ),
        ),
    ]

    encontrou = False

    for titulo, caminho in mapas:

        if caminho.exists():

            encontrou = True

            st.markdown(
                "**"
                +
                titulo
                +
                "**"
            )

            st.image(
                str(
                    caminho
                ),
                use_container_width=True,
            )

    if not encontrou:

        st.info(
            "Os mapas da Etapa 9I não foram "
            "encontrados no diretório esperado."
        )


# ============================================================
# RODAPÉ
# ============================================================

st.divider()

st.caption(
    "VerdePrioriza — ferramenta de triagem territorial "
    "e apoio à decisão. Os resultados não representam "
    "isoladamente obrigação legal de restauração, "
    "déficit de APP ou Reserva Legal, disponibilidade "
    "fundiária ou autorização automática de intervenção."
)
