-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 9E
-- IPL E PRIORIDADE INTEGRADA
-- Referência: 2024
-- ============================================================


ALTER TABLE spatial.celula_prioridade

    ADD COLUMN IF NOT EXISTS
        ipl_cenario_hidrologico NUMERIC(6,2),

    ADD COLUMN IF NOT EXISTS
        ipl_cenario_paisagem NUMERIC(6,2),

    ADD COLUMN IF NOT EXISTS
        ipl_media_cenarios NUMERIC(6,2),

    ADD COLUMN IF NOT EXISTS
        amplitude_ipl NUMERIC(6,2),

    ADD COLUMN IF NOT EXISTS
        rank_ipl_municipio INTEGER,

    ADD COLUMN IF NOT EXISTS
        rank_integrada_municipio INTEGER,

    ADD COLUMN IF NOT EXISTS
        rank_integrada_geral INTEGER,

    ADD COLUMN IF NOT EXISTS
        amplitude_rank_local INTEGER,

    ADD COLUMN IF NOT EXISTS
        estabilidade_ipl VARCHAR(20),

    ADD COLUMN IF NOT EXISTS
        classificacao_ipl VARCHAR(30),

    ADD COLUMN IF NOT EXISTS
        classificacao_integrada VARCHAR(30),

    ADD COLUMN IF NOT EXISTS
        versao_ipl VARCHAR(30);


COMMENT ON COLUMN
spatial.celula_prioridade.prioridade_local

IS
'IPL - Índice de Prioridade Local, de 0 a 100.';


COMMENT ON COLUMN
spatial.celula_prioridade.prioridade_integrada

IS
'Prioridade integrada = 75% IPL + 25% IPA municipal.';


COMMENT ON COLUMN
spatial.celula_prioridade.estabilidade_ipl

IS
'Estabilidade da célula diante dos cenários alternativos de ponderação.';


SELECT

    COUNT(*) AS celulas,

    COUNT(prioridade_local)
        AS com_ipl,

    COUNT(prioridade_integrada)
        AS com_prioridade_integrada

FROM spatial.celula_prioridade;


SELECT

    MIN(prioridade_local)
        AS ipl_min,

    MAX(prioridade_local)
        AS ipl_max,

    MIN(prioridade_integrada)
        AS integrada_min,

    MAX(prioridade_integrada)
        AS integrada_max

FROM spatial.celula_prioridade

WHERE
    prioridade_local IS NOT NULL;


SELECT

    m.nome_municipio,

    c.rank_ipl_municipio,

    c.id_celula,

    ROUND(
        c.prioridade_local,
        1
    ) AS ipl,

    ROUND(
        c.prioridade_integrada,
        1
    ) AS prioridade_integrada,

    c.estabilidade_ipl,

    ROUND(
        c.score_hidrologia,
        1
    ) AS h,

    ROUND(
        c.score_conectividade,
        1
    ) AS c,

    ROUND(
        c.score_declividade,
        1
    ) AS s,

    ROUND(
        c.score_elegibilidade,
        1
    ) AS e,

    c.uso_predominante

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m
    ON m.codigo_ibge = c.codigo_ibge

WHERE

    c.rank_ipl_municipio <= 20

ORDER BY

    m.nome_municipio,

    c.rank_ipl_municipio;



SELECT

    m.nome_municipio,

    c.rank_ipl_municipio,

    c.id_celula,

    ROUND(
        c.prioridade_local,
        1
    ) AS ipl,

    ROUND(
        c.prioridade_integrada,
        1
    ) AS prioridade_integrada,

    c.estabilidade_ipl,

    ROUND(
        c.score_hidrologia,
        1
    ) AS h,

    ROUND(
        c.score_conectividade,
        1
    ) AS c,

    ROUND(
        c.score_declividade,
        1
    ) AS s,

    ROUND(
        c.score_elegibilidade,
        1
    ) AS e,

    c.uso_predominante

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m
    ON m.codigo_ibge = c.codigo_ibge

WHERE

    c.rank_ipl_municipio <= 20

ORDER BY

    m.nome_municipio,

    c.rank_ipl_municipio;


SELECT

    c.rank_integrada_geral,

    m.nome_municipio,

    c.id_celula,

    ROUND(
        i.ipa,
        1
    ) AS ipa,

    ROUND(
        c.prioridade_local,
        1
    ) AS ipl,

    ROUND(
        c.prioridade_integrada,
        1
    ) AS prioridade_integrada,

    c.estabilidade_ipl,

    c.uso_predominante

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m
    ON m.codigo_ibge = c.codigo_ibge

JOIN analytics.ipa_municipio i

    ON i.codigo_ibge =
       c.codigo_ibge

    AND i.ano_referencia = 2024

    AND i.versao_modelo =
        'ipa_v1.0_2024'

WHERE
    c.prioridade_integrada
    IS NOT NULL

ORDER BY
    c.rank_integrada_geral

LIMIT 100;


SELECT

    m.nome_municipio,

    c.id_celula,

    ROUND(
        c.prioridade_local,
        1
    ) AS ipl,

    ROUND(
        c.ipl_cenario_hidrologico,
        1
    ) AS hidro,

    ROUND(
        c.ipl_cenario_paisagem,
        1
    ) AS paisagem,

    ROUND(
        c.amplitude_ipl,
        1
    ) AS amplitude,

    c.amplitude_rank_local,

    c.estabilidade_ipl

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m
    ON m.codigo_ibge = c.codigo_ibge

WHERE
    c.prioridade_local
    IS NOT NULL

ORDER BY
    c.amplitude_ipl ASC

LIMIT 100;


SELECT

    c.rank_integrada_geral,

    m.nome_municipio,

    c.id_celula,

    ROUND(
        c.prioridade_integrada,
        1
    ) AS prioridade,

    ROUND(
        c.prioridade_local,
        1
    ) AS ipl,

    c.estabilidade_ipl,

    ROUND(
        c.area_ha,
        2
    ) AS area_ha,

    c.uso_predominante

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m
    ON m.codigo_ibge = c.codigo_ibge

WHERE

    c.prioridade_integrada >= 80

    AND c.estabilidade_ipl = 'Alta'

ORDER BY
    c.prioridade_integrada DESC;


CREATE OR REPLACE VIEW
spatial.vw_prioridade_integrada AS

SELECT

    c.id_celula,

    c.codigo_ibge,

    m.nome_municipio,


    -- MUNICÍPIO

    i.ipa,

    i.rank_ipa,


    -- IPL

    c.prioridade_local AS ipl,

    c.prioridade_integrada,

    c.classificacao_ipl,

    c.classificacao_integrada,

    c.rank_ipl_municipio,

    c.rank_integrada_geral,

    c.estabilidade_ipl,

    c.amplitude_ipl,


    -- COMPONENTES

    c.score_hidrologia,

    c.score_conectividade,

    c.score_declividade,

    c.score_elegibilidade,


    -- INTERPRETAÇÃO FÍSICA

    c.distancia_drenagem_m,

    c.pct_vegetacao_natural,

    c.pct_uso_elegivel,

    c.vegetacao_entorno_pct,

    c.declividade_media_pct,

    c.declividade_p90_pct,

    c.uso_predominante,

    c.area_ha,


    -- GEOMETRIA

    c.geom


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
    c.prioridade_integrada
    IS NOT NULL;



SELECT

    classificacao_integrada,

    COUNT(*) AS celulas,

    ROUND(
        SUM(area_ha),
        1
    ) AS area_grade_ha

FROM spatial.celula_prioridade

WHERE
    prioridade_integrada
    IS NOT NULL

GROUP BY
    classificacao_integrada

ORDER BY
    MIN(
        prioridade_integrada
    );



SELECT

    estabilidade_ipl,

    COUNT(*) AS celulas,

    ROUND(
        SUM(area_ha),
        1
    ) AS area_ha

FROM spatial.celula_prioridade

WHERE

    prioridade_integrada >= 80

GROUP BY
    estabilidade_ipl

ORDER BY
    area_ha DESC;



SELECT

    COUNT(*) AS celulas,

    COUNT(*)
    FILTER (
        WHERE prioridade_local
              BETWEEN 0 AND 100
    ) AS ipl_valido,

    COUNT(*)
    FILTER (
        WHERE prioridade_integrada
              BETWEEN 0 AND 100
    ) AS integrada_valida,

    COUNT(*)
    FILTER (
        WHERE estabilidade_ipl
              IS NOT NULL
    ) AS estabilidade_valida

FROM spatial.celula_prioridade

WHERE
    prioridade_local
    IS NOT NULL;