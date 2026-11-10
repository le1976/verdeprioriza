-- ============================================================
-- VERDEPRIORIZA
-- Módulo 7
-- Índice de Prioridade Ambiental
-- Referência: 2024
-- ============================================================


ALTER TABLE analytics.ipa_municipio

    ADD COLUMN IF NOT EXISTS
        ipa_cenario_conservacao NUMERIC(6,2),

    ADD COLUMN IF NOT EXISTS
        ipa_cenario_disturbio NUMERIC(6,2),

    ADD COLUMN IF NOT EXISTS
        ipa_media_cenarios NUMERIC(6,2),

    ADD COLUMN IF NOT EXISTS
        amplitude_cenarios NUMERIC(6,2),

    ADD COLUMN IF NOT EXISTS
        rank_ipa INTEGER,

    ADD COLUMN IF NOT EXISTS
        rank_conservacao INTEGER,

    ADD COLUMN IF NOT EXISTS
        rank_disturbio INTEGER,

    ADD COLUMN IF NOT EXISTS
        amplitude_rank INTEGER,

    ADD COLUMN IF NOT EXISTS
        estabilidade VARCHAR(20);


COMMENT ON TABLE analytics.ipa_municipio IS
'Índice relativo de Prioridade Ambiental do VerdePrioriza.';


COMMENT ON COLUMN analytics.ipa_municipio.ipa IS
'Score relativo de prioridade ambiental de 0 a 100. Não representa déficit ambiental legal.';


COMMENT ON COLUMN analytics.ipa_municipio.estabilidade IS
'Estabilidade do IPA diante dos cenários alternativos de pesos.';

SELECT COUNT(*)
FROM analytics.ipa_municipio
WHERE
    ano_referencia = 2024
    AND versao_modelo = 'ipa_v1.0_2024';


SELECT

    classificacao,

    COUNT(*) AS municipios,

    ROUND(
        AVG(ipa),
        2
    ) AS ipa_medio,

    ROUND(
        MIN(ipa),
        2
    ) AS minimo,

    ROUND(
        MAX(ipa),
        2
    ) AS maximo

FROM analytics.ipa_municipio

WHERE
    ano_referencia = 2024
    AND versao_modelo = 'ipa_v1.0_2024'

GROUP BY classificacao

ORDER BY MIN(ipa);


SELECT

    i.rank_ipa AS posicao,

    m.nome_municipio,

    ROUND(
        i.ipa,
        2
    ) AS ipa,

    i.classificacao,

    ROUND(
        i.score_vegetacao,
        1
    ) AS baixa_cobertura,

    ROUND(
        i.score_perda_vegetacao,
        1
    ) AS perda_recente,

    ROUND(
        i.score_pressao_agropecuaria,
        1
    ) AS pressao_agro,

    ROUND(
        i.score_fogo,
        1
    ) AS fogo,

    i.estabilidade

FROM analytics.ipa_municipio i

JOIN core.dim_municipio m
    ON m.codigo_ibge = i.codigo_ibge

WHERE
    i.ano_referencia = 2024
    AND i.versao_modelo = 'ipa_v1.0_2024'

ORDER BY
    i.rank_ipa

LIMIT 20;


SELECT

    m.nome_municipio,

    ROUND(i.ipa, 2)
        AS ipa,

    ROUND(i.score_vegetacao, 2)
        AS baixa_cobertura,

    ROUND(i.score_perda_vegetacao, 2)
        AS perda_vegetacao,

    ROUND(i.score_pressao_agropecuaria, 2)
        AS pressao_agropecuaria,

    ROUND(i.score_fogo, 2)
        AS pressao_fogo,

    ROUND(i.ipa_cenario_conservacao, 2)
        AS ipa_conservacao,

    ROUND(i.ipa_cenario_disturbio, 2)
        AS ipa_disturbio,

    i.rank_ipa,

    i.amplitude_rank,

    i.estabilidade

FROM analytics.ipa_municipio i

JOIN core.dim_municipio m
    ON m.codigo_ibge = i.codigo_ibge

WHERE
    i.ano_referencia = 2024
    AND i.versao_modelo = 'ipa_v1.0_2024'

ORDER BY
    i.rank_ipa;


SELECT

    m.nome_municipio,

    i.rank_ipa,

    i.rank_conservacao,

    i.rank_disturbio,

    i.amplitude_rank,

    i.estabilidade

FROM analytics.ipa_municipio i

JOIN core.dim_municipio m
    ON m.codigo_ibge = i.codigo_ibge

WHERE
    i.ano_referencia = 2024
    AND i.versao_modelo = 'ipa_v1.0_2024'

ORDER BY
    i.amplitude_rank DESC

LIMIT 30;


SELECT COUNT(*)
FROM analytics.ipa_municipio
WHERE ano_referencia = 2024;


SELECT
    COUNT(*)
FROM analytics.ipa_municipio
WHERE
    ipa IS NULL
    OR ipa < 0
    OR ipa > 100;

SELECT
    COUNT(DISTINCT codigo_ibge)
FROM analytics.feature_municipio
WHERE ano_referencia = 2024;