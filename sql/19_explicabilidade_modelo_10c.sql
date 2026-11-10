-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 10C
-- EXPLICABILIDADE DO MODELO
--
-- Objetivo:
-- 1) Explicar por que uma área aparece bem posicionada;
-- 2) Mostrar quais componentes ambientais se destacam;
-- 3) Comparar a área com o universo das 1.045 áreas finais;
-- 4) Contextualizar o município frente aos 20 municípios-alvo.
--
-- Referência: 2024
-- ============================================================

BEGIN;

DROP VIEW IF EXISTS analytics.vw_explicabilidade_area_10c;
DROP VIEW IF EXISTS analytics.vw_explicabilidade_municipio_10c;


-- ============================================================
-- 1. EXPLICABILIDADE DAS ÁREAS
-- ============================================================

CREATE VIEW analytics.vw_explicabilidade_area_10c AS

WITH base AS (

    SELECT *
    FROM analytics.vw_ficha_area_10a

),

ipa_municipios AS (

    SELECT

        codigo_ibge,

        ipa,

        RANK() OVER (
            ORDER BY ipa DESC
        )::INTEGER
            AS posicao_ipa_municipio

    FROM analytics.vw_resumo_municipio_10b

),

estatisticas AS (

    SELECT

        AVG(score_hidrologia_medio)
            AS media_hidrologia,

        AVG(score_conectividade_medio)
            AS media_conectividade,

        AVG(score_declividade_medio)
            AS media_declividade,

        AVG(score_elegibilidade_medio)
            AS media_elegibilidade,

        (
            SELECT AVG(ipa)
            FROM ipa_municipios
        ) AS media_ipa,

        AVG(ipl_medio)
            AS media_ipl,

        AVG(prioridade_integrada_media)
            AS media_pi,

        AVG(area_total_ha)
            AS media_area_ha

    FROM base

),

comparacao AS (

    SELECT

        b.*,

        e.media_hidrologia,
        e.media_conectividade,
        e.media_declividade,
        e.media_elegibilidade,
        e.media_ipa,
        e.media_ipl,
        e.media_pi,
        e.media_area_ha,

        b.score_hidrologia_medio
            - e.media_hidrologia
            AS delta_hidrologia,

        b.score_conectividade_medio
            - e.media_conectividade
            AS delta_conectividade,

        b.score_declividade_medio
            - e.media_declividade
            AS delta_declividade,

        b.score_elegibilidade_medio
            - e.media_elegibilidade
            AS delta_elegibilidade,

        b.ipa_municipal
            - e.media_ipa
            AS delta_ipa,

        b.ipl_medio
            - e.media_ipl
            AS delta_ipl,

        b.prioridade_integrada_media
            - e.media_pi
            AS delta_pi,

        b.area_total_ha
            - e.media_area_ha
            AS delta_area_ha,

        im.posicao_ipa_municipio,

        PERCENT_RANK() OVER (
            ORDER BY b.ipl_medio
        ) * 100
            AS percentil_ipl_area,

        PERCENT_RANK() OVER (
            ORDER BY b.area_total_ha
        ) * 100
            AS percentil_tamanho_area

    FROM base b

    CROSS JOIN estatisticas e

    JOIN ipa_municipios im
        ON im.codigo_ibge = b.codigo_ibge

),

ordenado AS (

    SELECT

        c.*,

        d1.nome
            AS componente_1_nome,

        d1.valor
            AS componente_1_score,

        d1.media
            AS componente_1_media,

        d1.delta
            AS componente_1_delta,

        d2.nome
            AS componente_2_nome,

        d2.valor
            AS componente_2_score,

        d2.media
            AS componente_2_media,

        d2.delta
            AS componente_2_delta,

        d3.nome
            AS componente_3_nome,

        d3.valor
            AS componente_3_score,

        d3.media
            AS componente_3_media,

        d3.delta
            AS componente_3_delta,

        d4.nome
            AS componente_4_nome,

        d4.valor
            AS componente_4_score,

        d4.media
            AS componente_4_media,

        d4.delta
            AS componente_4_delta

    FROM comparacao c

    CROSS JOIN LATERAL (

        SELECT
            x.nome,
            x.valor,
            x.media,
            x.delta

        FROM (
            VALUES

                (
                    'Hidrologia'::TEXT,
                    c.score_hidrologia_medio::NUMERIC,
                    c.media_hidrologia::NUMERIC,
                    c.delta_hidrologia::NUMERIC
                ),

                (
                    'Conectividade'::TEXT,
                    c.score_conectividade_medio::NUMERIC,
                    c.media_conectividade::NUMERIC,
                    c.delta_conectividade::NUMERIC
                ),

                (
                    'Declividade'::TEXT,
                    c.score_declividade_medio::NUMERIC,
                    c.media_declividade::NUMERIC,
                    c.delta_declividade::NUMERIC
                ),

                (
                    'Elegibilidade'::TEXT,
                    c.score_elegibilidade_medio::NUMERIC,
                    c.media_elegibilidade::NUMERIC,
                    c.delta_elegibilidade::NUMERIC
                )

        ) AS x(
            nome,
            valor,
            media,
            delta
        )

        WHERE
            x.valor IS NOT NULL

        ORDER BY
            x.valor DESC,
            x.nome

        LIMIT 1
        OFFSET 0

    ) d1

    CROSS JOIN LATERAL (

        SELECT
            x.nome,
            x.valor,
            x.media,
            x.delta

        FROM (
            VALUES

                (
                    'Hidrologia'::TEXT,
                    c.score_hidrologia_medio::NUMERIC,
                    c.media_hidrologia::NUMERIC,
                    c.delta_hidrologia::NUMERIC
                ),

                (
                    'Conectividade'::TEXT,
                    c.score_conectividade_medio::NUMERIC,
                    c.media_conectividade::NUMERIC,
                    c.delta_conectividade::NUMERIC
                ),

                (
                    'Declividade'::TEXT,
                    c.score_declividade_medio::NUMERIC,
                    c.media_declividade::NUMERIC,
                    c.delta_declividade::NUMERIC
                ),

                (
                    'Elegibilidade'::TEXT,
                    c.score_elegibilidade_medio::NUMERIC,
                    c.media_elegibilidade::NUMERIC,
                    c.delta_elegibilidade::NUMERIC
                )

        ) AS x(
            nome,
            valor,
            media,
            delta
        )

        WHERE
            x.valor IS NOT NULL

        ORDER BY
            x.valor DESC,
            x.nome

        LIMIT 1
        OFFSET 1

    ) d2

    CROSS JOIN LATERAL (

        SELECT
            x.nome,
            x.valor,
            x.media,
            x.delta

        FROM (
            VALUES

                (
                    'Hidrologia'::TEXT,
                    c.score_hidrologia_medio::NUMERIC,
                    c.media_hidrologia::NUMERIC,
                    c.delta_hidrologia::NUMERIC
                ),

                (
                    'Conectividade'::TEXT,
                    c.score_conectividade_medio::NUMERIC,
                    c.media_conectividade::NUMERIC,
                    c.delta_conectividade::NUMERIC
                ),

                (
                    'Declividade'::TEXT,
                    c.score_declividade_medio::NUMERIC,
                    c.media_declividade::NUMERIC,
                    c.delta_declividade::NUMERIC
                ),

                (
                    'Elegibilidade'::TEXT,
                    c.score_elegibilidade_medio::NUMERIC,
                    c.media_elegibilidade::NUMERIC,
                    c.delta_elegibilidade::NUMERIC
                )

        ) AS x(
            nome,
            valor,
            media,
            delta
        )

        WHERE
            x.valor IS NOT NULL

        ORDER BY
            x.valor DESC,
            x.nome

        LIMIT 1
        OFFSET 2

    ) d3

    CROSS JOIN LATERAL (

        SELECT
            x.nome,
            x.valor,
            x.media,
            x.delta

        FROM (
            VALUES

                (
                    'Hidrologia'::TEXT,
                    c.score_hidrologia_medio::NUMERIC,
                    c.media_hidrologia::NUMERIC,
                    c.delta_hidrologia::NUMERIC
                ),

                (
                    'Conectividade'::TEXT,
                    c.score_conectividade_medio::NUMERIC,
                    c.media_conectividade::NUMERIC,
                    c.delta_conectividade::NUMERIC
                ),

                (
                    'Declividade'::TEXT,
                    c.score_declividade_medio::NUMERIC,
                    c.media_declividade::NUMERIC,
                    c.delta_declividade::NUMERIC
                ),

                (
                    'Elegibilidade'::TEXT,
                    c.score_elegibilidade_medio::NUMERIC,
                    c.media_elegibilidade::NUMERIC,
                    c.delta_elegibilidade::NUMERIC
                )

        ) AS x(
            nome,
            valor,
            media,
            delta
        )

        WHERE
            x.valor IS NOT NULL

        ORDER BY
            x.valor DESC,
            x.nome

        LIMIT 1
        OFFSET 3

    ) d4

)

SELECT

    *,

    CONCAT(

        'A área ',
        codigo_area,
        ', em ',
        nome_municipio,
        ', ocupa a posição ',
        rank_area_geral,
        ' no ranking geral e está no percentil ',
        ROUND(
            percentil_prioridade::NUMERIC,
            1
        ),
        '. ',

        'Sua Prioridade Integrada média é ',
        ROUND(
            prioridade_integrada_media::NUMERIC,
            2
        ),
        ', com IPA municipal de ',
        ROUND(
            ipa_municipal::NUMERIC,
            2
        ),
        ' e IPL médio de ',
        ROUND(
            ipl_medio::NUMERIC,
            2
        ),
        '. ',

        'O componente com maior score é ',
        componente_1_nome,
        ' (',
        ROUND(
            componente_1_score::NUMERIC,
            1
        ),
        '), seguido de ',
        componente_2_nome,
        ' (',
        ROUND(
            componente_2_score::NUMERIC,
            1
        ),
        '). ',

        CASE

            WHEN componente_1_delta >= 10
                THEN CONCAT(
                    componente_1_nome,
                    ' está ',
                    ROUND(
                        componente_1_delta::NUMERIC,
                        1
                    ),
                    ' pontos acima da média das áreas finais. '
                )

            WHEN componente_1_delta <= -10
                THEN CONCAT(
                    componente_1_nome,
                    ' está ',
                    ABS(
                        ROUND(
                            componente_1_delta::NUMERIC,
                            1
                        )
                    ),
                    ' pontos abaixo da média das áreas finais. '
                )

            ELSE CONCAT(
                componente_1_nome,
                ' está próximo da média das áreas finais. '
            )

        END,

        'A robustez da área é ',
        CASE
            WHEN robustez_area = 'Media'
                THEN 'Média'
            ELSE robustez_area
        END,
        '. ',

        CASE

            WHEN pct_area_excepcional >= 75
                THEN
                    'A maior parte da área está na faixa de prioridade excepcional. '

            WHEN pct_area_excepcional > 0
                THEN CONCAT(
                    ROUND(
                        pct_area_excepcional::NUMERIC,
                        1
                    ),
                    '% da área está na faixa excepcional. '
                )

            ELSE
                'A área não possui parcela classificada como prioridade excepcional. '

        END,

        CASE

            WHEN pct_area_nucleo >= 90
                THEN
                    'Sua composição territorial é fortemente dominada pelo núcleo prioritário.'

            WHEN pct_area_nucleo >= 50
                THEN
                    'O núcleo prioritário representa a maior parcela da área.'

            ELSE
                    'A área apresenta participação relevante de suporte espacial.'

        END

    ) AS explicacao_automatica

FROM ordenado;


-- ============================================================
-- 2. EXPLICABILIDADE DOS MUNICÍPIOS
-- ============================================================

CREATE VIEW analytics.vw_explicabilidade_municipio_10c AS

WITH base AS (

    SELECT *
    FROM analytics.vw_resumo_municipio_10b

),

estatisticas AS (

    SELECT

        AVG(prioridade_media_ponderada)
            AS media_pi_municipal,

        AVG(ipa)
            AS media_ipa_municipal,

        AVG(area_total_ha)
            AS media_area_total_ha,

        AVG(pct_area_excepcional)
            AS media_pct_excepcional,

        AVG(pct_area_robustez_alta)
            AS media_pct_robustez_alta

    FROM base

),

comparacao AS (

    SELECT

        b.*,

        e.media_pi_municipal,
        e.media_ipa_municipal,
        e.media_area_total_ha,
        e.media_pct_excepcional,
        e.media_pct_robustez_alta,

        b.prioridade_media_ponderada
            - e.media_pi_municipal
            AS delta_pi_municipal,

        b.ipa
            - e.media_ipa_municipal
            AS delta_ipa_municipal,

        b.area_total_ha
            - e.media_area_total_ha
            AS delta_area_total_ha,

        b.pct_area_excepcional
            - e.media_pct_excepcional
            AS delta_pct_excepcional,

        b.pct_area_robustez_alta
            - e.media_pct_robustez_alta
            AS delta_pct_robustez_alta,

        PERCENT_RANK() OVER (
            ORDER BY prioridade_media_ponderada
        ) * 100
            AS percentil_pi_municipal,

        PERCENT_RANK() OVER (
            ORDER BY ipa
        ) * 100
            AS percentil_ipa_municipal,

        PERCENT_RANK() OVER (
            ORDER BY area_total_ha
        ) * 100
            AS percentil_area_municipal,

        PERCENT_RANK() OVER (
            ORDER BY pct_area_excepcional
        ) * 100
            AS percentil_excepcional_municipal,

        PERCENT_RANK() OVER (
            ORDER BY pct_area_robustez_alta
        ) * 100
            AS percentil_robustez_municipal

    FROM base b

    CROSS JOIN estatisticas e

)

SELECT

    *,

    CONCAT(

        nome_municipio,
        ' ocupa a posição ',
        rank_municipio_10b,
        ' entre os 20 municípios na Prioridade Integrada média ponderada, com valor ',
        ROUND(
            prioridade_media_ponderada::NUMERIC,
            2
        ),
        '. ',

        'O IPA municipal é ',
        ROUND(
            ipa::NUMERIC,
            2
        ),
        '. ',

        'O município possui ',
        numero_areas,
        ' áreas prioritárias finais, totalizando ',
        ROUND(
            area_total_ha::NUMERIC,
            1
        ),
        ' ha. ',

        ROUND(
            pct_area_excepcional::NUMERIC,
            1
        ),
        '% da área priorizada está na faixa excepcional e ',

        ROUND(
            pct_area_robustez_alta::NUMERIC,
            1
        ),
        '% está na classe de robustez Alta. ',

        CASE

            WHEN prioridade_media_ponderada
                 >= media_pi_municipal + 2
                THEN
                    'A prioridade média do município está claramente acima da média do conjunto. '

            WHEN prioridade_media_ponderada
                 <= media_pi_municipal - 2
                THEN
                    'A prioridade média do município está abaixo da média do conjunto. '

            ELSE
                    'A prioridade média do município está próxima da média do conjunto. '

        END,

        CASE

            WHEN area_total_ha
                 >= media_area_total_ha * 2
                THEN
                    'O volume territorial priorizado é muito superior à média dos municípios.'

            WHEN area_total_ha
                 >= media_area_total_ha
                THEN
                    'O volume territorial priorizado está acima da média dos municípios.'

            ELSE
                    'O volume territorial priorizado está abaixo da média dos municípios.'

        END

    ) AS explicacao_automatica_municipio

FROM comparacao;


COMMIT;


-- ============================================================
-- 3. VALIDAÇÃO
-- ============================================================

SELECT
    COUNT(*) AS areas_explicadas,
    COUNT(DISTINCT codigo_ibge) AS municipios
FROM analytics.vw_explicabilidade_area_10c;


SELECT
    COUNT(*) AS municipios_explicados
FROM analytics.vw_explicabilidade_municipio_10c;


SELECT

    codigo_area,
    nome_municipio,
    rank_area_geral,
    prioridade_integrada_media,
    ipa_municipal,
    posicao_ipa_municipio,
    componente_1_nome,
    componente_1_score,
    componente_1_delta,
    componente_2_nome,
    componente_2_score,
    robustez_area,
    explicacao_automatica

FROM analytics.vw_explicabilidade_area_10c

ORDER BY rank_area_geral

LIMIT 10;


SELECT

    rank_municipio_10b,
    nome_municipio,
    prioridade_media_ponderada,
    ipa,
    area_total_ha,
    pct_area_excepcional,
    pct_area_robustez_alta,
    explicacao_automatica_municipio

FROM analytics.vw_explicabilidade_municipio_10c

ORDER BY rank_municipio_10b;
