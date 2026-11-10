-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 9 — ANÁLISE GEOESPACIAL AVANÇADA
-- Referência: 2024
-- ============================================================


DROP TABLE IF EXISTS spatial.municipio_alvo;


CREATE TABLE spatial.municipio_alvo AS

SELECT

    m.codigo_ibge,

    m.nome_municipio,

    i.rank_ipa,

    i.ipa,

    i.estabilidade,

    m.geom

FROM analytics.ipa_municipio i

JOIN core.dim_municipio m
    ON m.codigo_ibge = i.codigo_ibge

WHERE
    i.ano_referencia = 2024

    AND i.versao_modelo = 'ipa_v1.0_2024'

    AND i.estabilidade = 'Alta'

ORDER BY
    i.ipa DESC

LIMIT 20;


ALTER TABLE spatial.municipio_alvo
ADD PRIMARY KEY (codigo_ibge);


CREATE INDEX idx_municipio_alvo_geom
ON spatial.municipio_alvo
USING GIST (geom);


SELECT
    rank_ipa,
    nome_municipio,
    ipa,
    estabilidade
FROM spatial.municipio_alvo
ORDER BY ipa DESC;


CREATE TABLE IF NOT EXISTS spatial.celula_prioridade (

    id_celula BIGSERIAL PRIMARY KEY,

    codigo_ibge VARCHAR(7) NOT NULL,

    area_ha NUMERIC(12,4),

    pct_uso_elegivel NUMERIC(8,2),

    distancia_drenagem_m NUMERIC(12,2),

    declividade_media_pct NUMERIC(8,2),

    vegetacao_entorno_pct NUMERIC(8,2),

    score_hidrologia NUMERIC(6,2),

    score_declividade NUMERIC(6,2),

    score_conectividade NUMERIC(6,2),

    score_elegibilidade NUMERIC(6,2),

    prioridade_local NUMERIC(6,2),

    prioridade_integrada NUMERIC(6,2),

    geom GEOMETRY(POLYGON, 5880),

    data_calculo TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (codigo_ibge)
        REFERENCES core.dim_municipio(codigo_ibge)
);


CREATE INDEX IF NOT EXISTS idx_celula_prioridade_geom
ON spatial.celula_prioridade
USING GIST (geom);


ALTER TABLE spatial.celula_prioridade
ALTER COLUMN geom
TYPE geometry(MultiPolygon, 5880)
USING ST_Multi(geom);

SELECT
    GeometryType(geom) AS tipo_geometria,
    COUNT(*) AS quantidade
FROM spatial.celula_prioridade
GROUP BY GeometryType(geom);


SELECT
    codigo_ibge,
    COUNT(*) AS celulas
FROM spatial.celula_prioridade
GROUP BY codigo_ibge
ORDER BY celulas DESC;