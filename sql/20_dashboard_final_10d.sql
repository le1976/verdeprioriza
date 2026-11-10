-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 10D
-- DASHBOARD FINAL INTEGRADO
--
-- Integra:
-- 9H/9I - geometrias e áreas validadas
-- 10A   - ficha técnica
-- 10B   - resumo municipal
-- 10C   - explicabilidade
--
-- Referência: 2024
-- ============================================================

BEGIN;

DROP VIEW IF EXISTS analytics.vw_dashboard_area_10d;
DROP VIEW IF EXISTS analytics.vw_dashboard_municipio_10d;


-- ============================================================
-- 1. CAMADA INTEGRADA DE ÁREAS
-- ============================================================

CREATE VIEW analytics.vw_dashboard_area_10d AS

SELECT

    e.*,

    ST_X(
        ST_Transform(
            ST_PointOnSurface(a.geom),
            4326
        )
    ) AS longitude_mapa,

    ST_Y(
        ST_Transform(
            ST_PointOnSurface(a.geom),
            4326
        )
    ) AS latitude_mapa,

    ST_AsGeoJSON(
        ST_Transform(
            a.geom,
            4326
        ),
        6
    ) AS geojson_area

FROM analytics.vw_explicabilidade_area_10c e

JOIN spatial.area_prioritaria_9h a
    ON a.codigo_area = e.codigo_area

WHERE
    a.versao_areas = 'areas_9h_v1.1_2024'
    AND a.status_area = 'Área prioritária final';


-- ============================================================
-- 2. CAMADA INTEGRADA MUNICIPAL
-- ============================================================

CREATE VIEW analytics.vw_dashboard_municipio_10d AS

SELECT *
FROM analytics.vw_explicabilidade_municipio_10c;


COMMIT;


-- ============================================================
-- 3. VALIDAÇÃO
-- ============================================================

SELECT

    COUNT(*) AS areas_dashboard,

    COUNT(
        DISTINCT codigo_area
    ) AS codigos_unicos,

    COUNT(
        DISTINCT codigo_ibge
    ) AS municipios,

    COUNT(*) FILTER (
        WHERE geojson_area IS NULL
    ) AS areas_sem_geometria

FROM analytics.vw_dashboard_area_10d;


SELECT

    COUNT(*) AS municipios_dashboard,

    COUNT(
        DISTINCT codigo_ibge
    ) AS codigos_municipais_unicos

FROM analytics.vw_dashboard_municipio_10d;


SELECT

    rank_area_geral,
    codigo_area,
    nome_municipio,
    prioridade_integrada_media,
    robustez_area,
    componente_1_nome,
    posicao_ipa_municipio,
    longitude_mapa,
    latitude_mapa

FROM analytics.vw_dashboard_area_10d

ORDER BY rank_area_geral

LIMIT 10;
