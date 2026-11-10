-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 10A
-- FICHA TÉCNICA AUTOMÁTICA DAS ÁREAS PRIORITÁRIAS
--
-- Referência: 2024
-- Versão territorial: areas_9h_v1.1_2024
-- ============================================================


BEGIN;


DROP VIEW IF EXISTS
analytics.vw_ficha_area_10a;


CREATE VIEW analytics.vw_ficha_area_10a AS


SELECT

    -- ========================================================
    -- IDENTIFICAÇÃO
    -- ========================================================

    a.id_area,

    a.codigo_area,

    a.codigo_ibge,

    m.nome_municipio,


    -- ========================================================
    -- RANKING
    -- ========================================================

    a.rank_area_municipio,

    a.rank_area_geral,

    a.percentil_prioridade,

    a.classe_relativa,

    a.robustez_area,


    -- ========================================================
    -- COMPOSIÇÃO
    -- ========================================================

    a.numero_celulas,

    a.numero_nucleos,

    a.numero_suportes,

    a.numero_excepcionais,


    -- ========================================================
    -- ÁREA
    -- ========================================================

    a.area_total_ha,

    a.area_nucleo_ha,

    a.area_suporte_ha,

    a.area_excepcional_ha,

    a.pct_area_nucleo,

    ROUND(

        (
            100
            -
            a.pct_area_nucleo
        )::NUMERIC,

        2

    ) AS pct_area_suporte,

    a.pct_area_excepcional,


    -- ========================================================
    -- USO / VEGETAÇÃO
    -- ========================================================

    a.area_uso_candidato_ha,

    a.vegetacao_interna_estimada_ha,

    a.uso_predominante,


    -- ========================================================
    -- ÍNDICES
    -- ========================================================

    a.ipa_municipal,

    a.ipl_medio,

    a.ipl_min,

    a.ipl_max,

    a.prioridade_integrada_media,

    a.prioridade_integrada_min,

    a.prioridade_integrada_max,


    -- ========================================================
    -- COMPONENTES DO IPL
    -- ========================================================

    a.score_hidrologia_medio,

    a.score_conectividade_medio,

    a.score_declividade_medio,

    a.score_elegibilidade_medio,


    -- ========================================================
    -- CARACTERIZAÇÃO AMBIENTAL
    -- ========================================================

    a.distancia_drenagem_media_m,

    a.vegetacao_entorno_media_pct,

    a.declividade_media_pct,


    -- ========================================================
    -- ROBUSTEZ
    -- ========================================================

    a.amplitude_ipl_media,

    a.pct_celulas_estabilidade_alta,


    -- ========================================================
    -- EXPANSÃO
    -- ========================================================

    a.distancia_suporte_nucleo_media_m,

    a.distancia_suporte_nucleo_max_m,


    -- ========================================================
    -- COORDENADA DE REFERÊNCIA
    --
    -- Não representa necessariamente o centro geométrico.
    -- É um ponto garantidamente interno à área.
    -- ========================================================

    ROUND(

        ST_X(

            ST_Transform(

                ST_PointOnSurface(
                    a.geom
                ),

                4674

            )

        )::NUMERIC,

        6

    ) AS longitude,


    ROUND(

        ST_Y(

            ST_Transform(

                ST_PointOnSurface(
                    a.geom
                ),

                4674

            )

        )::NUMERIC,

        6

    ) AS latitude,


    -- ========================================================
    -- CONTROLE
    -- ========================================================

    v.status_validacao,

    a.versao_areas


FROM spatial.area_prioritaria_9h a


JOIN core.dim_municipio m

    ON m.codigo_ibge =
       a.codigo_ibge


JOIN analytics.validacao_area_9i v

    ON v.id_area =
       a.id_area


WHERE

    a.versao_areas =
        'areas_9h_v1.1_2024'


    AND a.status_area =
        'Área prioritária final'


    AND v.status_validacao =
        'Aprovada';



COMMIT;



-- ============================================================
-- VALIDAÇÃO
-- ============================================================

SELECT

    COUNT(*) AS areas,

    COUNT(
        DISTINCT codigo_ibge
    ) AS municipios

FROM analytics.vw_ficha_area_10a;



SELECT *

FROM analytics.vw_ficha_area_10a

ORDER BY
    rank_area_geral

LIMIT 1;