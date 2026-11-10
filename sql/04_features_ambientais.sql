-- ============================================================
-- VERDEPRIORIZA
-- Módulo 6
-- Features e indicadores ambientais
-- Ano de referência: 2024
-- ============================================================


-- ============================================================
-- 1. CONSOLIDAÇÃO DO FOGO
-- ============================================================

WITH anos AS (

    SELECT
        generate_series(
            2016,
            2024
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
                WHEN ano = 2024
                THEN area_queimada_ha
            END
        ) AS area_queimada_ha_ano,

        MAX(
            CASE
                WHEN ano = 2024
                THEN area_queimada_pct
            END
        ) AS area_queimada_pct_ano,


        AVG(
            area_queimada_ha
        ) FILTER (
            WHERE ano BETWEEN 2021 AND 2024
        ) AS media_anual_queimada_5a_ha,


        AVG(
            area_queimada_pct
        ) FILTER (
            WHERE ano BETWEEN 2021 AND 2024
        ) AS media_anual_queimada_5a_pct,


        SUM(
            area_queimada_pct
        ) FILTER (
            WHERE ano BETWEEN 2016 AND 2024
        ) AS carga_fogo_10a_pct,


        COUNT(*)
        FILTER (
            WHERE
                ano BETWEEN 2016 AND 2024
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
                WHEN ano = 2024
                THEN focos_referencia
            END
        ) AS focos_inpe_ano,

        SUM(
            focos_referencia
        ) FILTER (
            WHERE ano BETWEEN 2021 AND 2024
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

    2024,

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


CREATE TABLE IF NOT EXISTS analytics.feature_municipio (

    id BIGSERIAL PRIMARY KEY,

    codigo_ibge VARCHAR(7) NOT NULL,

    ano_referencia SMALLINT NOT NULL,

    versao_features VARCHAR(20) NOT NULL,


    -- ----------------------------------------------
    -- Valores ambientais
    -- ----------------------------------------------

    cobertura_natural_pct NUMERIC(10,4),

    perda_liquida_vegetacao_10a_pct
        NUMERIC(10,4),

    agropecuaria_pct NUMERIC(10,4),

    fogo_media_5a_pct NUMERIC(12,6),

    fogo_carga_10a_pct NUMERIC(12,6),

    focos_inpe_100km2 NUMERIC(12,4),


    -- ----------------------------------------------
    -- Scores normalizados
    -- ----------------------------------------------

    score_baixa_cobertura NUMERIC(6,2),

    score_perda_vegetacao NUMERIC(6,2),

    score_pressao_agropecuaria NUMERIC(6,2),

    score_fogo_media_5a NUMERIC(6,2),

    score_fogo_carga_10a NUMERIC(6,2),

    score_focos_inpe NUMERIC(6,2),


    data_calculo
        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,


    CONSTRAINT fk_feature_municipio

        FOREIGN KEY (codigo_ibge)

        REFERENCES core.dim_municipio(codigo_ibge),


    CONSTRAINT uq_feature_municipio

        UNIQUE (
            codigo_ibge,
            ano_referencia,
            versao_features
        )

);

SELECT
    ano,
    COUNT(*) AS municipios
FROM analytics.indicador_municipio
GROUP BY ano
ORDER BY ano DESC;

SELECT
    COUNT(*) AS registros_2024,
    COUNT(vegetacao_nativa_pct) AS vegetacao_preenchida,
    COUNT(agropecuaria_pct) AS agropecuaria_preenchida,
    COUNT(variacao_liquida_vegetacao_ha_10a) AS variacao_preenchida
FROM analytics.indicador_municipio
WHERE ano = 2024;

SELECT
    ano_referencia,
    COUNT(*) AS municipios
FROM analytics.fogo_municipio
GROUP BY ano_referencia
ORDER BY ano_referencia DESC;

SELECT
    COUNT(*) AS total_registros,
    MIN(ano) AS primeiro_ano,
    MAX(ano) AS ultimo_ano,
    COUNT(DISTINCT ano) AS quantidade_anos
FROM analytics.indicador_municipio;

SELECT
    ano,
    COUNT(*) AS registros,
    COUNT(DISTINCT codigo_ibge) AS municipios
FROM analytics.indicador_municipio
GROUP BY ano
ORDER BY ano DESC;

SELECT
    codigo_ibge,
    ano,
    vegetacao_nativa_pct,
    agropecuaria_pct,
    variacao_liquida_vegetacao_ha_10a
FROM analytics.indicador_municipio
ORDER BY ano DESC, codigo_ibge
LIMIT 20;

SELECT
    COUNT(*) AS registros,
    MIN(ano) AS primeiro_ano,
    MAX(ano) AS ultimo_ano,
    COUNT(DISTINCT codigo_ibge) AS municipios,
    MIN(area_queimada_ha) AS minimo,
    MAX(area_queimada_ha) AS maximo
FROM staging.mapbiomas_fogo_municipio_ano;

SELECT
    ano,
    COUNT(*) AS registros,
    SUM(area_queimada_ha) AS area_queimada_total_ha
FROM staging.mapbiomas_fogo_municipio_ano
GROUP BY ano
ORDER BY ano DESC
LIMIT 10;

SELECT
    codigo_ibge,
    municipio,
    ano,
    area_queimada_ha
FROM staging.mapbiomas_fogo_municipio_ano
WHERE area_queimada_ha > 0
ORDER BY area_queimada_ha DESC
LIMIT 20;


SELECT
    ano_referencia,
    COUNT(*) AS municipios,
    MIN(media_anual_queimada_5a_pct) AS minimo_media_5a,
    MAX(media_anual_queimada_5a_pct) AS maximo_media_5a,
    MIN(carga_fogo_10a_pct) AS minimo_carga_10a,
    MAX(carga_fogo_10a_pct) AS maximo_carga_10a
FROM analytics.fogo_municipio
GROUP BY ano_referencia
ORDER BY ano_referencia DESC;

SELECT
    m.codigo_ibge,
    m.nome_municipio,

    ROUND(
        (
            SUM(f.area_queimada_ha)
            FILTER (WHERE f.ano BETWEEN 2020 AND 2024)
            / 5.0
        )
        /
        (m.area_km2 * 100)
        * 100,
        4
    ) AS media_anual_queimada_5a_pct,

    ROUND(
        (
            SUM(f.area_queimada_ha)
            FILTER (WHERE f.ano BETWEEN 2015 AND 2024)
        )
        /
        (m.area_km2 * 100)
        * 100,
        4
    ) AS carga_fogo_10a_pct

FROM core.dim_municipio m

JOIN staging.mapbiomas_fogo_municipio_ano f
    ON f.codigo_ibge = m.codigo_ibge

WHERE
    m.uf = 'SP'
    AND f.colecao = '5'

GROUP BY
    m.codigo_ibge,
    m.nome_municipio,
    m.area_km2

ORDER BY
    carga_fogo_10a_pct DESC

LIMIT 20;


WITH calculo AS (

    SELECT
        m.codigo_ibge,

        (
            SUM(f.area_queimada_ha)
            FILTER (
                WHERE f.ano BETWEEN 2020 AND 2024
            )
            / 5.0
        )
        /
        NULLIF(m.area_km2 * 100, 0)
        * 100
        AS media_anual_queimada_5a_pct,

        (
            SUM(f.area_queimada_ha)
            FILTER (
                WHERE f.ano BETWEEN 2015 AND 2024
            )
        )
        /
        NULLIF(m.area_km2 * 100, 0)
        * 100
        AS carga_fogo_10a_pct

    FROM core.dim_municipio m

    JOIN staging.mapbiomas_fogo_municipio_ano f
        ON f.codigo_ibge = m.codigo_ibge

    WHERE
        m.uf = 'SP'
        AND f.colecao = '5'

    GROUP BY
        m.codigo_ibge,
        m.area_km2
)

UPDATE analytics.fogo_municipio a

SET
    media_anual_queimada_5a_pct =
        c.media_anual_queimada_5a_pct,

    carga_fogo_10a_pct =
        c.carga_fogo_10a_pct

FROM calculo c

WHERE
    a.codigo_ibge = c.codigo_ibge
    AND a.ano_referencia = 2024;

SELECT
    ano_referencia,
    COUNT(*) AS municipios,

    MIN(media_anual_queimada_5a_pct) AS minimo_media_5a,
    MAX(media_anual_queimada_5a_pct) AS maximo_media_5a,

    MIN(carga_fogo_10a_pct) AS minimo_carga_10a,
    MAX(carga_fogo_10a_pct) AS maximo_carga_10a

FROM analytics.fogo_municipio

WHERE ano_referencia = 2024

GROUP BY ano_referencia;


SELECT
    ano_referencia,
    versao_features,
    COUNT(*) AS municipios
FROM analytics.feature_municipio
GROUP BY
    ano_referencia,
    versao_features
ORDER BY
    ano_referencia DESC;

SELECT
    MIN(score_baixa_cobertura) AS min_cobertura,
    MAX(score_baixa_cobertura) AS max_cobertura,

    MIN(score_perda_vegetacao) AS min_perda,
    MAX(score_perda_vegetacao) AS max_perda,

    MIN(score_pressao_agropecuaria) AS min_agro,
    MAX(score_pressao_agropecuaria) AS max_agro,

    MIN(score_fogo_media_5a) AS min_fogo5,
    MAX(score_fogo_media_5a) AS max_fogo5,

    MIN(score_fogo_carga_10a) AS min_fogo10,
    MAX(score_fogo_carga_10a) AS max_fogo10,

    MIN(score_focos_inpe) AS min_inpe,
    MAX(score_focos_inpe) AS max_inpe

FROM analytics.feature_municipio
WHERE
    ano_referencia = 2024
    AND versao_features = 'v1.0';

SELECT COUNT(*)

FROM analytics.feature_municipio

WHERE
    ano_referencia = 2024

    AND versao_features = 'v1.0';


SELECT

    m.nome_municipio,

    ROUND(
        f.cobertura_natural_pct,
        2
    ) AS cobertura_pct,

    ROUND(
        f.score_baixa_cobertura,
        2
    ) AS score

FROM analytics.feature_municipio f

JOIN core.dim_municipio m
    ON m.codigo_ibge = f.codigo_ibge

WHERE
    f.ano_referencia = 2024

    AND f.versao_features = 'v1.0'

ORDER BY
    f.score_baixa_cobertura DESC

LIMIT 20;


SELECT

    m.nome_municipio,

    ROUND(
        f.agropecuaria_pct,
        2
    ) AS agropecuaria_pct,

    ROUND(
        f.score_pressao_agropecuaria,
        2
    ) AS score

FROM analytics.feature_municipio f

JOIN core.dim_municipio m
    ON m.codigo_ibge = f.codigo_ibge

WHERE
    f.ano_referencia = 2024

ORDER BY
    f.score_pressao_agropecuaria DESC

LIMIT 20;


SELECT

    m.nome_municipio,

    ROUND(
        f.fogo_media_5a_pct,
        3
    ) AS fogo_medio_5a_pct,

    ROUND(
        f.fogo_carga_10a_pct,
        3
    ) AS carga_fogo_10a_pct,

    ROUND(
        f.score_fogo_media_5a,
        2
    ) AS score_fogo_recente,

    ROUND(
        f.score_fogo_carga_10a,
        2
    ) AS score_fogo_historico

FROM analytics.feature_municipio f

JOIN core.dim_municipio m
    ON m.codigo_ibge = f.codigo_ibge

WHERE
    f.ano_referencia = 2024

ORDER BY
    f.score_fogo_media_5a DESC

LIMIT 20;


SELECT

    m.nome_municipio,

    ROUND(
        f.score_baixa_cobertura,
        1
    ) AS cobertura,

    ROUND(
        f.score_perda_vegetacao,
        1
    ) AS perda,

    ROUND(
        f.score_pressao_agropecuaria,
        1
    ) AS agro,

    ROUND(
        f.score_fogo_media_5a,
        1
    ) AS fogo_recente,

    ROUND(
        f.score_fogo_carga_10a,
        1
    ) AS fogo_historico

FROM analytics.feature_municipio f

JOIN core.dim_municipio m
    ON m.codigo_ibge = f.codigo_ibge

WHERE
    f.ano_referencia = 2024

ORDER BY
    f.score_baixa_cobertura DESC;