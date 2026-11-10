-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 10B
-- RELATÓRIO EXECUTIVO AUTOMÁTICO DOS 20 MUNICÍPIOS
--
-- Referência: 2024
-- Versão territorial: areas_9h_v1.1_2024
-- ============================================================

BEGIN;

DROP VIEW IF EXISTS analytics.vw_resumo_geral_10b;
DROP VIEW IF EXISTS analytics.vw_resumo_municipio_10b;


-- ============================================================
-- 1. RESUMO MUNICIPAL
-- ============================================================

CREATE VIEW analytics.vw_resumo_municipio_10b AS

WITH areas AS (

    SELECT
        a.*,
        m.nome_municipio

    FROM spatial.area_prioritaria_9h a

    JOIN core.dim_municipio m
        ON m.codigo_ibge = a.codigo_ibge

    JOIN analytics.validacao_area_9i v
        ON v.id_area = a.id_area

    WHERE
        a.versao_areas = 'areas_9h_v1.1_2024'
        AND a.status_area = 'Área prioritária final'
        AND v.status_validacao = 'Aprovada'
),

agregado AS (

    SELECT

        codigo_ibge,

        COUNT(*)::INTEGER AS numero_areas,

        SUM(area_total_ha) AS area_total_ha,

        SUM(area_nucleo_ha) AS area_nucleo_ha,

        SUM(area_suporte_ha) AS area_suporte_ha,

        SUM(area_excepcional_ha) AS area_excepcional_ha,

        CASE
            WHEN SUM(area_total_ha) > 0
            THEN
                SUM(area_excepcional_ha)
                / SUM(area_total_ha)
                * 100
            ELSE 0
        END AS pct_area_excepcional,

        AVG(area_total_ha) AS area_media_ha,

        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY area_total_ha
        ) AS area_mediana_ha,

        MAX(area_total_ha) AS maior_area_ha,

        SUM(
            prioridade_integrada_media
            * area_total_ha
        )
        /
        NULLIF(
            SUM(area_total_ha),
            0
        ) AS prioridade_media_ponderada,

        MAX(
            prioridade_integrada_media
        ) AS prioridade_maxima,

        MIN(
            rank_area_geral
        ) AS melhor_rank_area,

        COUNT(*) FILTER (
            WHERE robustez_area = 'Alta'
        )::INTEGER AS areas_robustez_alta,

        COUNT(*) FILTER (
            WHERE robustez_area = 'Media'
        )::INTEGER AS areas_robustez_media,

        COUNT(*) FILTER (
            WHERE robustez_area = 'Baixa'
        )::INTEGER AS areas_robustez_baixa,

        SUM(area_total_ha) FILTER (
            WHERE robustez_area = 'Alta'
        ) AS area_robustez_alta_ha,

        SUM(area_total_ha) FILTER (
            WHERE robustez_area = 'Media'
        ) AS area_robustez_media_ha,

        SUM(area_total_ha) FILTER (
            WHERE robustez_area = 'Baixa'
        ) AS area_robustez_baixa_ha,

        COUNT(*) FILTER (
            WHERE percentil_prioridade >= 90
        )::INTEGER AS areas_percentil_90_mais,

        COUNT(*) FILTER (
            WHERE area_excepcional_ha > 0
        )::INTEGER AS areas_com_faixa_excepcional,

        SUM(
            score_hidrologia_medio
            * area_total_ha
        )
        /
        NULLIF(
            SUM(area_total_ha),
            0
        ) AS score_hidrologia_ponderado,

        SUM(
            score_conectividade_medio
            * area_total_ha
        )
        /
        NULLIF(
            SUM(area_total_ha),
            0
        ) AS score_conectividade_ponderado,

        SUM(
            score_declividade_medio
            * area_total_ha
        )
        /
        NULLIF(
            SUM(area_total_ha),
            0
        ) AS score_declividade_ponderado,

        SUM(
            score_elegibilidade_medio
            * area_total_ha
        )
        /
        NULLIF(
            SUM(area_total_ha),
            0
        ) AS score_elegibilidade_ponderado

    FROM areas

    GROUP BY
        codigo_ibge
),

uso_principal AS (

    SELECT DISTINCT ON (
        codigo_ibge
    )

        codigo_ibge,

        uso_predominante AS uso_predominante_areas

    FROM (

        SELECT

            codigo_ibge,

            uso_predominante,

            SUM(
                area_total_ha
            ) AS area_uso_ha

        FROM areas

        WHERE
            uso_predominante IS NOT NULL

        GROUP BY
            codigo_ibge,
            uso_predominante

    ) x

    ORDER BY
        codigo_ibge,
        area_uso_ha DESC,
        uso_predominante
),

ipa AS (

    SELECT

        codigo_ibge,

        ipa

    FROM analytics.ipa_municipio

    WHERE
        ano_referencia = 2024
        AND versao_modelo = 'ipa_v1.0_2024'
),

base AS (

    SELECT

        a.codigo_ibge,

        m.nome_municipio,

        i.ipa,

        COALESCE(
            g.numero_areas,
            0
        ) AS numero_areas,

        COALESCE(
            g.area_total_ha,
            0
        ) AS area_total_ha,

        COALESCE(
            g.area_nucleo_ha,
            0
        ) AS area_nucleo_ha,

        COALESCE(
            g.area_suporte_ha,
            0
        ) AS area_suporte_ha,

        COALESCE(
            g.area_excepcional_ha,
            0
        ) AS area_excepcional_ha,

        COALESCE(
            g.pct_area_excepcional,
            0
        ) AS pct_area_excepcional,

        g.area_media_ha,

        g.area_mediana_ha,

        g.maior_area_ha,

        g.prioridade_media_ponderada,

        g.prioridade_maxima,

        g.melhor_rank_area,

        COALESCE(
            g.areas_robustez_alta,
            0
        ) AS areas_robustez_alta,

        COALESCE(
            g.areas_robustez_media,
            0
        ) AS areas_robustez_media,

        COALESCE(
            g.areas_robustez_baixa,
            0
        ) AS areas_robustez_baixa,

        COALESCE(
            g.area_robustez_alta_ha,
            0
        ) AS area_robustez_alta_ha,

        COALESCE(
            g.area_robustez_media_ha,
            0
        ) AS area_robustez_media_ha,

        COALESCE(
            g.area_robustez_baixa_ha,
            0
        ) AS area_robustez_baixa_ha,

        COALESCE(
            g.areas_percentil_90_mais,
            0
        ) AS areas_percentil_90_mais,

        COALESCE(
            g.areas_com_faixa_excepcional,
            0
        ) AS areas_com_faixa_excepcional,

        g.score_hidrologia_ponderado,

        g.score_conectividade_ponderado,

        g.score_declividade_ponderado,

        g.score_elegibilidade_ponderado,

        u.uso_predominante_areas

    FROM spatial.municipio_alvo a

    JOIN core.dim_municipio m
        ON m.codigo_ibge = a.codigo_ibge

    LEFT JOIN agregado g
        ON g.codigo_ibge = a.codigo_ibge

    LEFT JOIN uso_principal u
        ON u.codigo_ibge = a.codigo_ibge

    LEFT JOIN ipa i
        ON i.codigo_ibge = a.codigo_ibge
)

SELECT

    ROW_NUMBER() OVER (

        ORDER BY

            prioridade_media_ponderada DESC NULLS LAST,

            area_total_ha DESC,

            nome_municipio

    )::INTEGER AS rank_municipio_10b,

    *,

    CASE
        WHEN area_total_ha > 0
        THEN
            area_nucleo_ha
            / area_total_ha
            * 100
        ELSE 0
    END AS pct_area_nucleo,

    CASE
        WHEN area_total_ha > 0
        THEN
            area_suporte_ha
            / area_total_ha
            * 100
        ELSE 0
    END AS pct_area_suporte,

    CASE
        WHEN area_total_ha > 0
        THEN
            area_robustez_alta_ha
            / area_total_ha
            * 100
        ELSE 0
    END AS pct_area_robustez_alta

FROM base;


-- ============================================================
-- 2. RESUMO GERAL
-- ============================================================

CREATE VIEW analytics.vw_resumo_geral_10b AS

WITH areas AS (

    SELECT
        a.*

    FROM spatial.area_prioritaria_9h a

    JOIN analytics.validacao_area_9i v
        ON v.id_area = a.id_area

    WHERE
        a.versao_areas = 'areas_9h_v1.1_2024'
        AND a.status_area = 'Área prioritária final'
        AND v.status_validacao = 'Aprovada'
),

ipa AS (

    SELECT
        AVG(ipa) AS ipa_medio_municipios

    FROM analytics.ipa_municipio

    WHERE
        ano_referencia = 2024
        AND versao_modelo = 'ipa_v1.0_2024'
        AND codigo_ibge IN (
            SELECT codigo_ibge
            FROM spatial.municipio_alvo
        )
)

SELECT

    COUNT(
        DISTINCT codigo_ibge
    )::INTEGER AS municipios,

    COUNT(*)::INTEGER AS areas_finais,

    SUM(
        area_total_ha
    ) AS area_total_ha,

    SUM(
        area_nucleo_ha
    ) AS area_nucleo_ha,

    SUM(
        area_suporte_ha
    ) AS area_suporte_ha,

    SUM(
        area_excepcional_ha
    ) AS area_excepcional_ha,

    SUM(
        prioridade_integrada_media
        * area_total_ha
    )
    /
    NULLIF(
        SUM(area_total_ha),
        0
    ) AS prioridade_media_ponderada,

    MAX(
        prioridade_integrada_media
    ) AS prioridade_maxima,

    COUNT(*) FILTER (
        WHERE robustez_area = 'Alta'
    )::INTEGER AS areas_robustez_alta,

    COUNT(*) FILTER (
        WHERE robustez_area = 'Media'
    )::INTEGER AS areas_robustez_media,

    COUNT(*) FILTER (
        WHERE robustez_area = 'Baixa'
    )::INTEGER AS areas_robustez_baixa,

    SUM(area_total_ha) FILTER (
        WHERE robustez_area = 'Alta'
    ) AS area_robustez_alta_ha,

    SUM(area_total_ha) FILTER (
        WHERE robustez_area = 'Media'
    ) AS area_robustez_media_ha,

    SUM(area_total_ha) FILTER (
        WHERE robustez_area = 'Baixa'
    ) AS area_robustez_baixa_ha,

    COUNT(*) FILTER (
        WHERE percentil_prioridade >= 90
    )::INTEGER AS areas_percentil_90_mais,

    COUNT(*) FILTER (
        WHERE area_excepcional_ha > 0
    )::INTEGER AS areas_com_faixa_excepcional,

    (
        SELECT ipa_medio_municipios
        FROM ipa
    ) AS ipa_medio_municipios

FROM areas;


COMMIT;


-- ============================================================
-- 3. VALIDAÇÃO
-- ============================================================

SELECT
    COUNT(*) AS municipios
FROM analytics.vw_resumo_municipio_10b;


SELECT *
FROM analytics.vw_resumo_geral_10b;


SELECT
    rank_municipio_10b,
    nome_municipio,
    numero_areas,
    ROUND(area_total_ha, 1) AS area_total_ha,
    ROUND(area_excepcional_ha, 1) AS area_excepcional_ha,
    ROUND(prioridade_media_ponderada, 2) AS prioridade_media,
    ROUND(ipa, 2) AS ipa,
    ROUND(pct_area_robustez_alta, 1) AS pct_area_robustez_alta,
    uso_predominante_areas
FROM analytics.vw_resumo_municipio_10b
ORDER BY rank_municipio_10b;
