-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 9I
-- VALIDAÇÃO ESPACIAL FINAL
--
-- Referência: 2024
-- Versão das áreas: areas_9h_v1.1_2024
-- ============================================================


BEGIN;


-- ============================================================
-- 0. LIMPEZA
-- ============================================================

DROP VIEW IF EXISTS
spatial.vw_areas_finais_9i;


DROP VIEW IF EXISTS
spatial.vw_nucleos_isolados_9i;


DROP VIEW IF EXISTS
spatial.vw_celulas_selecao_9i;


DROP TABLE IF EXISTS
analytics.validacao_area_9i;



-- ============================================================
-- 1. TABELA DE VALIDAÇÃO POR ÁREA
-- ============================================================

CREATE TABLE analytics.validacao_area_9i (

    id_area BIGINT PRIMARY KEY,

    codigo_area VARCHAR(40) NOT NULL,

    codigo_ibge VARCHAR(7) NOT NULL,

    status_area VARCHAR(40),

    area_total_ha NUMERIC(14,4),

    area_geometrica_ha NUMERIC(14,4),

    diferenca_area_ha NUMERIC(14,6),

    area_fora_municipio_m2 NUMERIC(18,4),

    geom_valida BOOLEAN,

    dentro_municipio BOOLEAN,

    possui_nucleo BOOLEAN,

    regra_area_status_ok BOOLEAN,

    area_componentes_ok BOOLEAN,

    percentuais_ok BOOLEAN,

    prioridade_ok BOOLEAN,

    ranking_ok BOOLEAN,

    suporte_distancia_ok BOOLEAN,

    sobreposicao_area_m2 NUMERIC(18,4),

    sem_sobreposicao BOOLEAN,

    status_validacao VARCHAR(20),

    data_validacao TIMESTAMP
        NOT NULL
        DEFAULT CURRENT_TIMESTAMP

);



-- ============================================================
-- 2. CALCULAR VALIDAÇÕES
-- ============================================================

WITH base AS (

    SELECT

        a.*,

        ST_Transform(
            m.geom,
            5880
        ) AS geom_municipio


    FROM spatial.area_prioritaria_9h a


    JOIN core.dim_municipio m

        ON m.codigo_ibge =
           a.codigo_ibge


    WHERE

        a.versao_areas =
            'areas_9h_v1.1_2024'

),


metricas AS (

    SELECT

        a.id_area,

        a.codigo_area,

        a.codigo_ibge,

        a.status_area,

        a.area_total_ha,

        a.area_geometrica_ha,


        ABS(

            a.area_total_ha

            -

            a.area_geometrica_ha

        ) AS diferenca_area_ha,


        -- ----------------------------------------------------
        -- Área da geometria que eventualmente ficou
        -- fora do município.
        -- ----------------------------------------------------

        ST_Area(

            ST_Difference(

                ST_MakeValid(
                    a.geom
                ),

                ST_MakeValid(
                    a.geom_municipio
                )

            )

        ) AS area_fora_municipio_m2,


        ST_IsValid(
            a.geom
        ) AS geom_valida,


        a.numero_nucleos > 0
            AS possui_nucleo,


        -- ----------------------------------------------------
        -- Status x área
        -- ----------------------------------------------------

        CASE

            WHEN
                a.status_area =
                    'Área prioritária final'

            THEN
                a.area_total_ha >= 10


            WHEN
                a.status_area =
                    'Núcleo isolado'

            THEN
                a.area_total_ha < 10


            ELSE
                FALSE

        END AS regra_area_status_ok,


        -- ----------------------------------------------------
        -- Área total deve ser núcleo + suporte
        -- ----------------------------------------------------

        ABS(

            a.area_total_ha

            -

            (
                a.area_nucleo_ha
                +
                a.area_suporte_ha
            )

        ) <= 0.01
            AS area_componentes_ok,


        -- ----------------------------------------------------
        -- Percentuais
        -- ----------------------------------------------------

        CASE

            WHEN
                a.pct_area_nucleo
                    BETWEEN 0 AND 100

                AND

                a.pct_area_excepcional
                    BETWEEN 0 AND 100

                AND

                a.pct_area_excepcional
                    <= a.pct_area_nucleo

            THEN TRUE

            ELSE FALSE

        END AS percentuais_ok,


        -- ----------------------------------------------------
        -- PI mínimo <= PI médio <= PI máximo
        -- ----------------------------------------------------

        CASE

            WHEN

                a.prioridade_integrada_min
                    <=
                a.prioridade_integrada_media

                AND

                a.prioridade_integrada_media
                    <=
                a.prioridade_integrada_max

                AND

                a.percentil_prioridade
                    BETWEEN 0 AND 100

            THEN TRUE

            ELSE FALSE

        END AS prioridade_ok,


        -- ----------------------------------------------------
        -- Ranking coerente com o status
        -- ----------------------------------------------------

        CASE

            WHEN
                a.status_area =
                    'Área prioritária final'

            THEN

                a.rank_area_municipio
                    IS NOT NULL

                AND

                a.rank_area_geral
                    IS NOT NULL

                AND

                a.rank_nucleo_isolado_municipio
                    IS NULL

                AND

                a.rank_nucleo_isolado_geral
                    IS NULL


            WHEN
                a.status_area =
                    'Núcleo isolado'

            THEN

                a.rank_area_municipio
                    IS NULL

                AND

                a.rank_area_geral
                    IS NULL

                AND

                a.rank_nucleo_isolado_municipio
                    IS NOT NULL

                AND

                a.rank_nucleo_isolado_geral
                    IS NOT NULL


            ELSE FALSE

        END AS ranking_ok,


        -- ----------------------------------------------------
        -- Se houver suporte, distância máxima <= 500 m.
        -- Sem suporte = automaticamente válido.
        -- ----------------------------------------------------

        CASE

            WHEN
                a.numero_suportes = 0

            THEN TRUE


            WHEN
                a.distancia_suporte_nucleo_max_m
                    <= 500

            THEN TRUE


            ELSE FALSE

        END AS suporte_distancia_ok,


        a.geom


    FROM base a

),


sobreposicoes AS (

    SELECT

        a.id_area,


        COALESCE(

            SUM(

                ST_Area(

                    ST_Intersection(
                        a.geom,
                        b.geom
                    )

                )

            ),

            0

        ) AS sobreposicao_area_m2


    FROM metricas a


    LEFT JOIN metricas b

        ON b.id_area >
           a.id_area


        AND ST_Intersects(
            a.geom,
            b.geom
        )


    GROUP BY
        a.id_area

)


INSERT INTO analytics.validacao_area_9i (

    id_area,

    codigo_area,

    codigo_ibge,

    status_area,

    area_total_ha,

    area_geometrica_ha,

    diferenca_area_ha,

    area_fora_municipio_m2,

    geom_valida,

    dentro_municipio,

    possui_nucleo,

    regra_area_status_ok,

    area_componentes_ok,

    percentuais_ok,

    prioridade_ok,

    ranking_ok,

    suporte_distancia_ok,

    sobreposicao_area_m2,

    sem_sobreposicao,

    status_validacao

)


SELECT

    m.id_area,

    m.codigo_area,

    m.codigo_ibge,

    m.status_area,

    m.area_total_ha,

    m.area_geometrica_ha,

    m.diferenca_area_ha,

    m.area_fora_municipio_m2,

    m.geom_valida,


    -- Até 1 m² fora do limite é tratado como
    -- tolerância numérica de geometria.
    m.area_fora_municipio_m2 <= 1
        AS dentro_municipio,


    m.possui_nucleo,

    m.regra_area_status_ok,

    m.area_componentes_ok,

    m.percentuais_ok,

    m.prioridade_ok,

    m.ranking_ok,

    m.suporte_distancia_ok,


    s.sobreposicao_area_m2,


    -- Até 1 m² é tratado como tolerância geométrica.
    s.sobreposicao_area_m2 <= 1
        AS sem_sobreposicao,


    CASE

        WHEN

            m.geom_valida

            AND m.area_fora_municipio_m2 <= 1

            AND m.possui_nucleo

            AND m.regra_area_status_ok

            AND m.area_componentes_ok

            AND m.percentuais_ok

            AND m.prioridade_ok

            AND m.ranking_ok

            AND m.suporte_distancia_ok

            AND s.sobreposicao_area_m2 <= 1

        THEN
            'Aprovada'


        ELSE
            'Revisar'

    END AS status_validacao


FROM metricas m


JOIN sobreposicoes s

    ON s.id_area =
       m.id_area;



-- ============================================================
-- 3. VIEW FINAL — ÁREAS OPERACIONAIS
-- ============================================================

CREATE OR REPLACE VIEW
spatial.vw_areas_finais_9i AS


SELECT

    a.id_area,

    a.codigo_area,

    a.codigo_ibge,

    m.nome_municipio,


    a.rank_area_municipio,

    a.rank_area_geral,


    a.area_total_ha,

    a.area_nucleo_ha,

    a.area_suporte_ha,

    a.area_excepcional_ha,


    a.pct_area_nucleo,

    a.pct_area_excepcional,


    a.prioridade_integrada_media,

    a.prioridade_integrada_min,

    a.prioridade_integrada_max,


    a.percentil_prioridade,

    a.classe_relativa,

    a.robustez_area,


    a.ipa_municipal,

    a.ipl_medio,


    a.score_hidrologia_medio,

    a.score_conectividade_medio,

    a.score_declividade_medio,

    a.score_elegibilidade_medio,


    a.distancia_drenagem_media_m,

    a.vegetacao_entorno_media_pct,

    a.declividade_media_pct,

    a.uso_predominante,


    a.amplitude_ipl_media,


    v.status_validacao,


    a.geom


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
        'Área prioritária final';



-- ============================================================
-- 4. VIEW DOS NÚCLEOS ISOLADOS
-- ============================================================

CREATE OR REPLACE VIEW
spatial.vw_nucleos_isolados_9i AS


SELECT

    a.id_area,

    a.codigo_area,

    a.codigo_ibge,

    m.nome_municipio,


    a.rank_nucleo_isolado_municipio,

    a.rank_nucleo_isolado_geral,


    a.area_total_ha,

    a.area_excepcional_ha,


    a.prioridade_integrada_media,

    a.percentil_prioridade,

    a.classe_relativa,

    a.robustez_area,


    v.status_validacao,


    a.geom


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
        'Núcleo isolado';



-- ============================================================
-- 5. VIEW DAS CÉLULAS NÚCLEO / SUPORTE / EXCEPCIONAL
-- ============================================================

CREATE OR REPLACE VIEW
spatial.vw_celulas_selecao_9i AS


SELECT

    s.id_celula,

    s.codigo_ibge,

    m.nome_municipio,

    s.tipo_selecao,

    s.nivel_prioridade,

    s.prioridade_integrada,

    s.distancia_nucleo_m,

    s.id_nucleo_proximo,

    s.geom


FROM spatial.celula_selecao_9h s


JOIN core.dim_municipio m

    ON m.codigo_ibge =
       s.codigo_ibge;



COMMIT;



-- ============================================================
-- 6. RESUMO DA VALIDAÇÃO
-- ============================================================

SELECT

    status_validacao,

    COUNT(*) AS areas,

    ROUND(
        SUM(area_total_ha),
        1
    ) AS area_ha

FROM analytics.validacao_area_9i

GROUP BY
    status_validacao

ORDER BY
    status_validacao;



-- ============================================================
-- 7. TESTES INDIVIDUAIS
-- ============================================================

SELECT

    COUNT(*) FILTER (
        WHERE NOT geom_valida
    ) AS geom_invalidas,

    COUNT(*) FILTER (
        WHERE NOT dentro_municipio
    ) AS fora_municipio,

    COUNT(*) FILTER (
        WHERE NOT possui_nucleo
    ) AS sem_nucleo,

    COUNT(*) FILTER (
        WHERE NOT regra_area_status_ok
    ) AS status_area_incorreto,

    COUNT(*) FILTER (
        WHERE NOT area_componentes_ok
    ) AS area_componentes_incorreta,

    COUNT(*) FILTER (
        WHERE NOT percentuais_ok
    ) AS percentuais_invalidos,

    COUNT(*) FILTER (
        WHERE NOT prioridade_ok
    ) AS prioridade_invalida,

    COUNT(*) FILTER (
        WHERE NOT ranking_ok
    ) AS ranking_invalido,

    COUNT(*) FILTER (
        WHERE NOT suporte_distancia_ok
    ) AS suporte_acima_500m,

    COUNT(*) FILTER (
        WHERE NOT sem_sobreposicao
    ) AS sobreposicoes

FROM analytics.validacao_area_9i;



-- ============================================================
-- 8. ÁREAS QUE PRECISAM DE REVISÃO
-- ============================================================

SELECT *

FROM analytics.validacao_area_9i

WHERE
    status_validacao =
        'Revisar'

ORDER BY
    codigo_ibge,
    codigo_area;



-- ============================================================
-- 9. RESUMO DAS ÁREAS FINAIS
-- ============================================================

SELECT

    COUNT(*) AS areas_finais,

    COUNT(
        DISTINCT codigo_ibge
    ) AS municipios,

    ROUND(
        SUM(area_total_ha),
        1
    ) AS area_total_ha,

    ROUND(
        SUM(area_nucleo_ha),
        1
    ) AS area_nucleo_ha,

    ROUND(
        SUM(area_suporte_ha),
        1
    ) AS area_suporte_ha,

    ROUND(
        SUM(area_excepcional_ha),
        1
    ) AS area_excepcional_ha,

    ROUND(
        AVG(prioridade_integrada_media),
        2
    ) AS prioridade_media

FROM spatial.area_prioritaria_9h

WHERE

    versao_areas =
        'areas_9h_v1.1_2024'

    AND status_area =
        'Área prioritária final';




SELECT

    COUNT(*) FILTER (
        WHERE NOT geom_valida
    ) AS geom_invalidas,

    COUNT(*) FILTER (
        WHERE NOT dentro_municipio
    ) AS fora_municipio,

    COUNT(*) FILTER (
        WHERE NOT possui_nucleo
    ) AS sem_nucleo,

    COUNT(*) FILTER (
        WHERE NOT regra_area_status_ok
    ) AS status_area_incorreto,

    COUNT(*) FILTER (
        WHERE NOT area_componentes_ok
    ) AS area_componentes_incorreta,

    COUNT(*) FILTER (
        WHERE NOT percentuais_ok
    ) AS percentuais_invalidos,

    COUNT(*) FILTER (
        WHERE NOT prioridade_ok
    ) AS prioridade_invalida,

    COUNT(*) FILTER (
        WHERE NOT ranking_ok
    ) AS ranking_invalido,

    COUNT(*) FILTER (
        WHERE NOT suporte_distancia_ok
    ) AS suporte_acima_500m,

    COUNT(*) FILTER (
        WHERE NOT sem_sobreposicao
    ) AS sobreposicoes

FROM analytics.validacao_area_9i;