-- ============================================================
-- VERDEPRIORIZA
-- Módulo 6
-- Features e indicadores ambientais
-- Ano de referência: 2025
-- ============================================================


-- ============================================================
-- 1. CONSOLIDAÇÃO DO FOGO
-- ============================================================

WITH anos AS (

    SELECT
        generate_series(
            2016,
            2025
        )::SMALLINT AS ano

),

grade AS (

    SELECT

        m.codigo_ibge,

        a.ano

    FROM core.dim_municipio m

    CROSS JOIN anos a

    WHERE m.uf = 'SP'

),

fogo AS (

    SELECT

        g.codigo_ibge,

        g.ano,

        COALESCE(
            f.area_queimada_ha,
            0
        ) AS area_queimada_ha,

        COALESCE(
            f.area_queimada_pct,
            0
        ) AS area_queimada_pct

    FROM grade g

    LEFT JOIN staging.fogo_municipio_ano f

        ON f.codigo_ibge = g.codigo_ibge
        AND f.ano = g.ano
        AND f.colecao = '5'

),

fogo_resumo AS (

    SELECT

        codigo_ibge,

        MAX(
            CASE
                WHEN ano = 2025
                THEN area_queimada_ha
            END
        ) AS area_queimada_ha_ano,

        MAX(
            CASE
                WHEN ano = 2025
                THEN area_queimada_pct
            END
        ) AS area_queimada_pct_ano,


        AVG(
            area_queimada_ha
        ) FILTER (
            WHERE ano BETWEEN 2021 AND 2025
        ) AS media_anual_queimada_5a_ha,


        AVG(
            area_queimada_pct
        ) FILTER (
            WHERE ano BETWEEN 2021 AND 2025
        ) AS media_anual_queimada_5a_pct,


        SUM(
            area_queimada_pct
        ) FILTER (
            WHERE ano BETWEEN 2016 AND 2025
        ) AS carga_fogo_10a_pct,


        COUNT(*)
        FILTER (
            WHERE
                ano BETWEEN 2016 AND 2025
                AND area_queimada_ha > 0
        ) AS anos_com_fogo_10a

    FROM fogo

    GROUP BY codigo_ibge

),

inpe AS (

    SELECT

        codigo_ibge,

        MAX(
            CASE
                WHEN ano = 2025
                THEN focos_referencia
            END
        ) AS focos_inpe_ano,

        SUM(
            focos_referencia
        ) FILTER (
            WHERE ano BETWEEN 2021 AND 2025
        ) AS focos_inpe_5a

    FROM staging.inpe_fogo_municipio_ano

    GROUP BY codigo_ibge

)


INSERT INTO analytics.fogo_municipio (

    codigo_ibge,

    ano_referencia,

    area_queimada_ha_ano,

    area_queimada_pct_ano,

    media_anual_queimada_5a_ha,

    media_anual_queimada_5a_pct,

    carga_fogo_10a_pct,

    anos_com_fogo_10a,

    focos_inpe_ano,

    focos_inpe_5a

)

SELECT

    m.codigo_ibge,

    2025,

    COALESCE(
        f.area_queimada_ha_ano,
        0
    ),

    COALESCE(
        f.area_queimada_pct_ano,
        0
    ),

    COALESCE(
        f.media_anual_queimada_5a_ha,
        0
    ),

    COALESCE(
        f.media_anual_queimada_5a_pct,
        0
    ),

    COALESCE(
        f.carga_fogo_10a_pct,
        0
    ),

    COALESCE(
        f.anos_com_fogo_10a,
        0
    ),

    COALESCE(
        i.focos_inpe_ano,
        0
    ),

    COALESCE(
        i.focos_inpe_5a,
        0
    )

FROM core.dim_municipio m

LEFT JOIN fogo_resumo f
    ON f.codigo_ibge = m.codigo_ibge

LEFT JOIN inpe i
    ON i.codigo_ibge = m.codigo_ibge

WHERE m.uf = 'SP'

ON CONFLICT (codigo_ibge)

DO UPDATE SET

    ano_referencia =
        EXCLUDED.ano_referencia,

    area_queimada_ha_ano =
        EXCLUDED.area_queimada_ha_ano,

    area_queimada_pct_ano =
        EXCLUDED.area_queimada_pct_ano,

    media_anual_queimada_5a_ha =
        EXCLUDED.media_anual_queimada_5a_ha,

    media_anual_queimada_5a_pct =
        EXCLUDED.media_anual_queimada_5a_pct,

    carga_fogo_10a_pct =
        EXCLUDED.carga_fogo_10a_pct,

    anos_com_fogo_10a =
        EXCLUDED.anos_com_fogo_10a,

    focos_inpe_ano =
        EXCLUDED.focos_inpe_ano,

    focos_inpe_5a =
        EXCLUDED.focos_inpe_5a,

    data_calculo =
        CURRENT_TIMESTAMP;