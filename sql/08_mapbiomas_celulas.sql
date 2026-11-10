-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 9B
-- MAPBIOMAS COBERTURA 2024
-- ============================================================


ALTER TABLE spatial.celula_prioridade

    ADD COLUMN IF NOT EXISTS
        pct_vegetacao_natural NUMERIC(8,2),

    ADD COLUMN IF NOT EXISTS
        pct_agua NUMERIC(8,2),

    ADD COLUMN IF NOT EXISTS
        pct_area_urbanizada NUMERIC(8,2),

    ADD COLUMN IF NOT EXISTS
        classe_predominante INTEGER,

    ADD COLUMN IF NOT EXISTS
        uso_predominante VARCHAR(120),

    ADD COLUMN IF NOT EXISTS
        pixels_validos INTEGER,

    ADD COLUMN IF NOT EXISTS
        ano_mapbiomas SMALLINT,

    ADD COLUMN IF NOT EXISTS
        colecao_mapbiomas VARCHAR(20);


COMMENT ON COLUMN
spatial.celula_prioridade.pct_vegetacao_natural

IS
'Percentual da célula classificado como vegetação natural no MapBiomas Cobertura 30m.';


COMMENT ON COLUMN
spatial.celula_prioridade.pct_uso_elegivel

IS
'Percentual da célula em classes antrópicas selecionadas como candidatas analíticas. Não implica elegibilidade jurídica ou recomendação automática de restauração.';


COMMENT ON COLUMN
spatial.celula_prioridade.vegetacao_entorno_pct

IS
'Percentual de vegetação natural no entorno da célula. Será calculado posteriormente na análise de conectividade.';


SELECT

    m.nome_municipio,

    COUNT(*) AS celulas,

    COUNT(
        c.pct_uso_elegivel
    ) AS processadas,

    COUNT(*)
    -
    COUNT(
        c.pct_uso_elegivel
    ) AS sem_mapbiomas,

    ROUND(
        AVG(
            c.pct_vegetacao_natural
        ),
        2
    ) AS vegetacao_media_pct,

    ROUND(
        AVG(
            c.pct_uso_elegivel
        ),
        2
    ) AS uso_candidato_medio_pct

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m
    ON m.codigo_ibge =
       c.codigo_ibge

WHERE c.ano_mapbiomas = 2024

GROUP BY
    m.nome_municipio;


SELECT

    MIN(pixels_validos)
        AS minimo,

    ROUND(
        AVG(pixels_validos),
        1
    ) AS media,

    PERCENTILE_CONT(0.5)
    WITHIN GROUP (
        ORDER BY pixels_validos
    ) AS mediana,

    MAX(pixels_validos)
        AS maximo

FROM spatial.celula_prioridade

WHERE
    ano_mapbiomas = 2024;


SELECT

    uso_predominante,

    COUNT(*) AS celulas,

    ROUND(
        COUNT(*) * 100.0
        /
        SUM(COUNT(*)) OVER (),
        2
    ) AS percentual

FROM spatial.celula_prioridade

WHERE
    ano_mapbiomas = 2024

    AND pixels_validos >= 10

GROUP BY
    uso_predominante

ORDER BY
    celulas DESC;


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

    c.score_hidrologia,

    ROUND(
        c.pct_vegetacao_natural,
        1
    ) AS vegetacao_pct,

    ROUND(
        c.pct_uso_elegivel,
        1
    ) AS uso_candidato_pct,

    c.uso_predominante

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m

    ON m.codigo_ibge =
       c.codigo_ibge

WHERE

    c.score_hidrologia >= 80

    AND c.pct_uso_elegivel >= 70

    AND c.pct_vegetacao_natural <= 30

    AND c.area_ha >= 1

    AND c.pixels_validos >= 10

ORDER BY

    c.score_hidrologia DESC,

    c.pct_uso_elegivel DESC;


CREATE OR REPLACE VIEW
spatial.vw_validacao_mapbiomas AS

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

    c.pct_agua,

    c.pct_area_urbanizada,

    c.classe_predominante,

    c.uso_predominante,

    c.pixels_validos,

    c.score_elegibilidade,

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
        'ipa_v1.0_2024';


SELECT

    m.nome_municipio,

    COUNT(*) AS celulas,

    ROUND(
        SUM(c.area_ha),
        1
    ) AS area_total_grade_ha,

    ROUND(
        SUM(
            c.area_ha
            *
            c.pct_uso_elegivel
            /
            100
        ),
        1
    ) AS area_candidata_estimada_ha,

    ROUND(
        SUM(
            c.area_ha
            *
            c.pct_vegetacao_natural
            /
            100
        ),
        1
    ) AS vegetacao_estimada_ha

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m

    ON m.codigo_ibge =
       c.codigo_ibge

WHERE

    c.ano_mapbiomas = 2024

    AND c.pixels_validos >= 10

GROUP BY

    m.nome_municipio

ORDER BY

    area_candidata_estimada_ha DESC;


CREATE OR REPLACE VIEW
spatial.vw_celulas_preselecionadas AS

SELECT

    c.*,

    m.nome_municipio,

    i.ipa,

    i.rank_ipa

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m

    ON m.codigo_ibge =
       c.codigo_ibge

JOIN analytics.ipa_municipio i

    ON i.codigo_ibge =
       c.codigo_ibge

    AND i.ano_referencia =
        2024

    AND i.versao_modelo =
        'ipa_v1.0_2024'

WHERE

    c.area_ha >= 1

    AND c.pixels_validos >= 10

    AND c.pct_uso_elegivel >= 30

    AND c.pct_area_urbanizada < 20

    AND c.pct_agua < 50;


SELECT

    COUNT(DISTINCT codigo_ibge)
        AS municipios,

    COUNT(*) AS celulas,

    COUNT(pct_uso_elegivel)
        AS processadas,

    COUNT(*)
    -
    COUNT(pct_uso_elegivel)
        AS sem_mapbiomas

FROM spatial.celula_prioridade

WHERE ano_mapbiomas = 2024;


WITH grade AS (

    SELECT

        codigo_ibge,

        SUM(area_ha) AS area_grade_ha,

        SUM(
            area_ha
            *
            pct_vegetacao_natural
            /
            100
        ) AS vegetacao_grade_ha

    FROM spatial.celula_prioridade

    WHERE

        ano_mapbiomas = 2024

        AND pixels_validos >= 10

    GROUP BY codigo_ibge

)

SELECT

    m.nome_municipio,

    ROUND(
        g.vegetacao_grade_ha,
        1
    ) AS vegetacao_raster_ha,

    ROUND(
        mb.vegetacao_nativa_ha,
        1
    ) AS vegetacao_tabela_ha,

    ROUND(

        (
            g.vegetacao_grade_ha
            -
            mb.vegetacao_nativa_ha
        )

        /

        NULLIF(
            mb.vegetacao_nativa_ha,
            0
        )

        *
        100,

        2

    ) AS diferenca_pct

FROM grade g

JOIN core.dim_municipio m

    ON m.codigo_ibge =
       g.codigo_ibge


JOIN staging.mapbiomas_municipio_ano mb

    ON mb.codigo_ibge =
       g.codigo_ibge

    AND mb.ano = 2024

ORDER BY

    ABS(

        g.vegetacao_grade_ha
        -
        mb.vegetacao_nativa_ha

    ) DESC;
