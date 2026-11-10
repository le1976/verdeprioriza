-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 9A
-- BHO6 - HIDROGRAFIA
-- ============================================================


DROP TABLE IF EXISTS spatial.bho6_drenagem_alvo;


CREATE TABLE spatial.bho6_drenagem_alvo (

    id BIGSERIAL PRIMARY KEY,

    codigo_ibge VARCHAR(7) NOT NULL,

    drn_pk VARCHAR(50),

    cotrecho VARCHAR(50),

    cobacia VARCHAR(100),

    cocursodag VARCHAR(100),

    nome_rio VARCHAR(255),

    ordem_strahler INTEGER,

    area_montante_km2 DOUBLE PRECISION,

    comprimento_trecho DOUBLE PRECISION,

    versao_bho VARCHAR(100),

    geom GEOMETRY(MULTILINESTRING, 5880),

    data_carga TIMESTAMP
        NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_bho6_municipio

        FOREIGN KEY (codigo_ibge)

        REFERENCES core.dim_municipio(codigo_ibge)

);


CREATE INDEX idx_bho6_codigo

ON spatial.bho6_drenagem_alvo (
    codigo_ibge
);


CREATE INDEX idx_bho6_geom

ON spatial.bho6_drenagem_alvo

USING GIST (geom);


CREATE INDEX idx_bho6_codigo_geom

ON spatial.bho6_drenagem_alvo

USING GIST (geom);


SELECT

    m.nome_municipio,

    COUNT(*) AS trechos,

    COUNT(DISTINCT d.drn_pk)
        AS trechos_origem

FROM spatial.bho6_drenagem_alvo d

JOIN core.dim_municipio m
    ON m.codigo_ibge = d.codigo_ibge

GROUP BY
    m.nome_municipio

ORDER BY
    trechos DESC;


SELECT

    ST_SRID(geom)
        AS srid,

    GeometryType(geom)
        AS tipo,

    COUNT(*)

FROM spatial.bho6_drenagem_alvo

GROUP BY
    ST_SRID(geom),
    GeometryType(geom);


SELECT

    m.nome_municipio,

    COUNT(c.id_celula)
        AS celulas,

    ROUND(
        AVG(c.area_ha),
        2
    ) AS area_media_ha

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m
    ON m.codigo_ibge = c.codigo_ibge

GROUP BY
    m.nome_municipio

ORDER BY
    celulas DESC;



SELECT

    COUNT(*) AS celulas,

    COUNT(
        distancia_drenagem_m
    ) AS com_distancia,

    COUNT(*)
    -
    COUNT(
        distancia_drenagem_m
    ) AS sem_distancia,

    ROUND(
        MIN(distancia_drenagem_m)::NUMERIC,
        2
    ) AS minimo_m,

    ROUND(
        AVG(distancia_drenagem_m)::NUMERIC,
        2
    ) AS media_m,

    ROUND(
        MAX(distancia_drenagem_m)::NUMERIC,
        2
    ) AS maximo_m

FROM spatial.celula_prioridade

WHERE codigo_ibge IN (

    SELECT codigo_ibge

    FROM spatial.bho6_drenagem_alvo
);


SELECT

    ROUND(
        PERCENTILE_CONT(0.10)
        WITHIN GROUP (
            ORDER BY distancia_drenagem_m
        )::NUMERIC,
        2
    ) AS p10,

    ROUND(
        PERCENTILE_CONT(0.25)
        WITHIN GROUP (
            ORDER BY distancia_drenagem_m
        )::NUMERIC,
        2
    ) AS p25,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY distancia_drenagem_m
        )::NUMERIC,
        2
    ) AS mediana,

    ROUND(
        PERCENTILE_CONT(0.75)
        WITHIN GROUP (
            ORDER BY distancia_drenagem_m
        )::NUMERIC,
        2
    ) AS p75,

    ROUND(
        PERCENTILE_CONT(0.90)
        WITHIN GROUP (
            ORDER BY distancia_drenagem_m
        )::NUMERIC,
        2
    ) AS p90

FROM spatial.celula_prioridade

WHERE distancia_drenagem_m IS NOT NULL;


SELECT

    CASE

        WHEN distancia_drenagem_m <= 100
            THEN '01 - 0 a 100 m'

        WHEN distancia_drenagem_m <= 250
            THEN '02 - 100 a 250 m'

        WHEN distancia_drenagem_m <= 500
            THEN '03 - 250 a 500 m'

        WHEN distancia_drenagem_m <= 1000
            THEN '04 - 500 a 1000 m'

        ELSE
            '05 - acima de 1000 m'

    END AS faixa,

    COUNT(*) AS celulas,

    ROUND(
        COUNT(*) * 100.0
        /
        SUM(COUNT(*)) OVER (),
        2
    ) AS percentual

FROM spatial.celula_prioridade

WHERE
    distancia_drenagem_m IS NOT NULL

GROUP BY 1

ORDER BY 1;


CREATE OR REPLACE VIEW
spatial.vw_validacao_hidrologia AS

SELECT

    c.id_celula,

    c.codigo_ibge,

    m.nome_municipio,

    i.ipa,

    i.rank_ipa,

    c.area_ha,

    c.distancia_drenagem_m,

    c.score_hidrologia,

    c.geom

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m

    ON m.codigo_ibge =
       c.codigo_ibge


LEFT JOIN analytics.ipa_municipio i

    ON i.codigo_ibge =
       c.codigo_ibge

    AND i.ano_referencia = 2024

    AND i.versao_modelo =
        'ipa_v1.0_2024';



SELECT

    ordem_strahler,

    COUNT(*) AS trechos,

    ROUND(
        AVG(
            comprimento_trecho
        )::NUMERIC,
        2
    ) AS comprimento_medio

FROM spatial.bho6_drenagem_alvo

GROUP BY
    ordem_strahler

ORDER BY
    ordem_strahler;


SELECT

    m.nome_municipio,

    c.id_celula,

    ROUND(
        c.area_ha,
        2
    ) AS area_ha,

    ROUND(
        c.distancia_drenagem_m,
        2
    ) AS distancia_m,

    c.score_hidrologia

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m

    ON m.codigo_ibge =
       c.codigo_ibge

WHERE
    c.distancia_drenagem_m
    IS NOT NULL

ORDER BY
    c.distancia_drenagem_m

LIMIT 30;


SELECT

    COUNT(DISTINCT codigo_ibge)
        AS municipios,

    COUNT(*)
        AS celulas,

    COUNT(distancia_drenagem_m)
        AS celulas_com_distancia,

    COUNT(score_hidrologia)
        AS celulas_com_score

FROM spatial.celula_prioridade

WHERE codigo_ibge IN (

    SELECT DISTINCT codigo_ibge

    FROM spatial.bho6_drenagem_alvo
);