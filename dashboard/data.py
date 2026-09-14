import os

from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL
from sqlalchemy import text


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]

ANO_REFERENCIA = 2024

VERSAO_FEATURES = "v1.0"

VERSAO_MODELO = "ipa_v1.0_2024"


load_dotenv(
    ROOT_DIR / ".env"
)


# ============================================================
# CONEXÃO
# ============================================================

@st.cache_resource
def get_engine():

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


# ============================================================
# BASE PRINCIPAL
# ============================================================

@st.cache_data(ttl=3600)
def carregar_base_ipa():

    engine = get_engine()

    sql = """
    SELECT

        m.codigo_ibge,

        m.nome_municipio,

        m.area_km2,


        -- IPA

        i.ipa,

        i.classificacao,

        i.rank_ipa,

        i.estabilidade,

        i.amplitude_rank,

        i.amplitude_cenarios,

        i.ipa_cenario_conservacao,

        i.ipa_cenario_disturbio,


        -- scores

        i.score_vegetacao,

        i.score_perda_vegetacao,

        i.score_pressao_agropecuaria,

        i.score_fogo,


        -- valores ambientais brutos

        f.cobertura_natural_pct,

        f.perda_liquida_vegetacao_10a_pct,

        f.agropecuaria_pct,

        f.fogo_media_5a_pct,

        f.fogo_carga_10a_pct,

        f.focos_inpe_100km2,


        -- geometria

        m.geom


    FROM core.dim_municipio m


    JOIN analytics.ipa_municipio i

        ON i.codigo_ibge = m.codigo_ibge


    JOIN analytics.feature_municipio f

        ON f.codigo_ibge = m.codigo_ibge


    WHERE

        m.uf = 'SP'

        AND i.ano_referencia = 2024

        AND i.versao_modelo = 'ipa_v1.0_2024'

        AND f.ano_referencia = 2024

        AND f.versao_features = 'v1.0'


    ORDER BY i.rank_ipa;
    """


    gdf = gpd.read_postgis(

        sql,

        engine,

        geom_col="geom",
    )


    return gdf


# ============================================================
# SÉRIE HISTÓRICA MAPBIOMAS
# ============================================================

@st.cache_data(ttl=3600)
def carregar_historico_cobertura(
    codigo_ibge
):

    engine = get_engine()

    sql = text("""
    SELECT

        ano,

        vegetacao_nativa_ha,

        agropecuaria_ha,

        area_mapeada_ha,

        CASE

            WHEN area_mapeada_ha > 0

            THEN
                vegetacao_nativa_ha
                /
                area_mapeada_ha
                *
                100

        END AS vegetacao_pct,


        CASE

            WHEN area_mapeada_ha > 0

            THEN
                agropecuaria_ha
                /
                area_mapeada_ha
                *
                100

        END AS agropecuaria_pct


    FROM staging.mapbiomas_municipio_ano

    WHERE

        codigo_ibge = :codigo_ibge

        AND ano <= 2024

    ORDER BY ano;
    """)


    return pd.read_sql(

        sql,

        engine,

        params={
            "codigo_ibge":
                codigo_ibge
        },
    )


# ============================================================
# SÉRIE HISTÓRICA DE FOGO
# ============================================================

@st.cache_data(ttl=3600)
def carregar_historico_fogo(
    codigo_ibge
):

    engine = get_engine()

    sql = text("""
    SELECT

        ano,

        area_queimada_ha,

        area_queimada_pct

    FROM staging.fogo_municipio_ano

    WHERE

        codigo_ibge = :codigo_ibge

        AND ano <= 2024

    ORDER BY ano;
    """)


    return pd.read_sql(

        sql,

        engine,

        params={
            "codigo_ibge":
                codigo_ibge
        },
    )


# ============================================================
# INPE
# ============================================================

@st.cache_data(ttl=3600)
def carregar_historico_inpe(
    codigo_ibge
):

    engine = get_engine()

    sql = text("""
    SELECT

        ano,

        focos_referencia,

        focos_por_100_km2,

        frp_medio

    FROM staging.inpe_fogo_municipio_ano

    WHERE

        codigo_ibge = :codigo_ibge

        AND ano <= 2024

    ORDER BY ano;
    """)


    return pd.read_sql(

        sql,

        engine,

        params={
            "codigo_ibge":
                codigo_ibge
        },
    )