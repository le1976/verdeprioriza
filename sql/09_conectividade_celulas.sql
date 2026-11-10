-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 9C
-- CONECTIVIDADE DA VEGETAÇÃO
-- Referência: MapBiomas 2024
-- ============================================================


ALTER TABLE spatial.celula_prioridade

    ADD COLUMN IF NOT EXISTS
        area_entorno_ha NUMERIC(14,4),

    ADD COLUMN IF NOT EXISTS
        vegetacao_entorno_ha NUMERIC(14,4),

    ADD COLUMN IF NOT EXISTS
        pixels_entorno_validos INTEGER,

    ADD COLUMN IF NOT EXISTS
        raio_conectividade_m INTEGER;


COMMENT ON COLUMN
spatial.celula_prioridade.vegetacao_entorno_pct

IS
'Percentual estimado de vegetação natural em um anel de 1 km ao redor da célula, excluindo a própria célula.';


COMMENT ON COLUMN
spatial.celula_prioridade.score_conectividade

IS
'Score preliminar de contexto de vegetação no entorno. Não representa índice oficial de conectividade ecológica.';


COMMENT ON COLUMN
spatial.celula_prioridade.raio_conectividade_m

IS
'Raio utilizado para análise do entorno da célula, em metros.';


SELECT

    COUNT(*) AS celulas,

    ROUND(
        MIN(
            vegetacao_entorno_pct
        ),
        2
    ) AS minimo,

    ROUND(
        AVG(
            vegetacao_entorno_pct
        ),
        2
    ) AS media,

    ROUND(
        PERCENTILE_CONT(0.10)
        WITHIN GROUP (
            ORDER BY vegetacao_entorno_pct
        )::NUMERIC,
        2
    ) AS p10,

    ROUND(
        PERCENTILE_CONT(0.25)
        WITHIN GROUP (
            ORDER BY vegetacao_entorno_pct
        )::NUMERIC,
        2
    ) AS p25,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY vegetacao_entorno_pct
        )::NUMERIC,
        2
    ) AS mediana,

    ROUND(
        PERCENTILE_CONT(0.75)
        WITHIN GROUP (
            ORDER BY vegetacao_entorno_pct
        )::NUMERIC,
        2
    ) AS p75,

    ROUND(
        PERCENTILE_CONT(0.90)
        WITHIN GROUP (
            ORDER BY vegetacao_entorno_pct
        )::NUMERIC,
        2
    ) AS p90,

    ROUND(
        MAX(
            vegetacao_entorno_pct
        ),
        2
    ) AS maximo

FROM spatial.celula_prioridade

WHERE
    vegetacao_entorno_pct IS NOT NULL

    AND raio_conectividade_m = 1000;


UPDATE spatial.celula_prioridade

SET score_conectividade =

    ROUND(

        LEAST(

            100,

            GREATEST(

                0,

                (
                    vegetacao_entorno_pct
                    /
                    60.0
                )
                *
                100

            )

        ),

        2
    )

WHERE
    vegetacao_entorno_pct IS NOT NULL

    AND raio_conectividade_m = 1000;


SELECT

    MIN(score_conectividade)
        AS minimo,

    ROUND(
        AVG(score_conectividade),
        2
    ) AS media,

    MAX(score_conectividade)
        AS maximo

FROM spatial.celula_prioridade

WHERE
    score_conectividade
    IS NOT NULL;


SELECT

    m.nome_municipio,

    c.id_celula,

    ROUND(
        c.area_ha,
        2
    ) AS area_ha,

    ROUND(
        c.distancia_drenagem_m,
        0
    ) AS distancia_agua_m,

    ROUND(
        c.pct_uso_elegivel,
        1
    ) AS uso_candidato_pct,

    ROUND(
        c.pct_vegetacao_natural,
        1
    ) AS vegetacao_celula_pct,

    ROUND(
        c.vegetacao_entorno_pct,
        1
    ) AS vegetacao_entorno_pct,

    ROUND(
        c.score_hidrologia,
        1
    ) AS hidrologia,

    ROUND(
        c.score_elegibilidade,
        1
    ) AS elegibilidade,

    ROUND(
        c.score_conectividade,
        1
    ) AS conectividade,

    c.uso_predominante

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m

    ON m.codigo_ibge =
       c.codigo_ibge

WHERE

    c.score_hidrologia >= 80

    AND c.score_elegibilidade >= 70

    AND c.score_conectividade >= 50

    AND c.area_ha >= 1

    AND c.pixels_validos >= 10

ORDER BY

    c.score_conectividade DESC,

    c.score_hidrologia DESC,

    c.score_elegibilidade DESC

LIMIT 100;


CREATE OR REPLACE VIEW
spatial.vw_validacao_conectividade AS

SELECT

    c.id_celula,

    c.codigo_ibge,

    m.nome_municipio,

    i.ipa,

    i.rank_ipa,

    c.area_ha,

    c.distancia_drenagem_m,

    c.score_hidrologia,

    c.pct_vegetacao_natural,

    c.pct_uso_elegivel,

    c.vegetacao_entorno_pct,

    c.vegetacao_entorno_ha,

    c.score_elegibilidade,

    c.score_conectividade,

    c.uso_predominante,

    c.geom

FROM spatial.celula_prioridade c


JOIN core.dim_municipio m

    ON m.codigo_ibge =
       c.codigo_ibge


LEFT JOIN analytics.ipa_municipio i

    ON i.codigo_ibge =
       c.codigo_ibge

    AND i.ano_referencia =
        2024

    AND i.versao_modelo =
        'ipa_v1.0_2024'


WHERE
    c.vegetacao_entorno_pct
    IS NOT NULL;


SELECT

    m.nome_municipio,

    COUNT(*) AS celulas,

    ROUND(
        SUM(c.area_ha),
        1
    ) AS area_grade_ha

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m

    ON m.codigo_ibge =
       c.codigo_ibge

WHERE

    c.score_hidrologia >= 80

    AND c.score_elegibilidade >= 70

    AND c.score_conectividade >= 60

    AND c.pct_vegetacao_natural <= 30

    AND c.area_ha >= 1

    AND c.pixels_validos >= 10

GROUP BY
    m.nome_municipio

ORDER BY
    area_grade_ha DESC;


SELECT

    COUNT(*) AS processadas,

    COUNT(*)
    FILTER (
        WHERE vegetacao_entorno_pct
              BETWEEN 0 AND 100
    ) AS pct_valido,

    COUNT(*)
    FILTER (
        WHERE score_conectividade
              BETWEEN 0 AND 100
    ) AS score_valido,

    COUNT(*)
    FILTER (
        WHERE pixels_entorno_validos = 0
    ) AS sem_pixels

FROM spatial.celula_prioridade

WHERE
    raio_conectividade_m = 1000;