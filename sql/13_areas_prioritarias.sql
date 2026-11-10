-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 9F
-- ÁREAS PRIORITÁRIAS CONTÍNUAS
-- Referência: 2024
-- ============================================================


DROP TABLE IF EXISTS
spatial.area_prioritaria_celula;


DROP TABLE IF EXISTS
spatial.area_prioritaria;


-- ============================================================
-- ÁREAS
-- ============================================================

CREATE TABLE spatial.area_prioritaria (

    id_area BIGSERIAL PRIMARY KEY,

    codigo_area VARCHAR(30),

    cluster_ref VARCHAR(100) NOT NULL,

    codigo_ibge VARCHAR(7) NOT NULL,

    numero_celulas INTEGER NOT NULL,

    area_grade_ha NUMERIC(14,4),

    area_geometrica_ha NUMERIC(14,4),

    area_uso_candidato_ha NUMERIC(14,4),

    vegetacao_interna_estimada_ha NUMERIC(14,4),


    -- MUNICÍPIO

    ipa_municipal NUMERIC(6,2),


    -- IPL

    ipl_medio NUMERIC(6,2),

    ipl_min NUMERIC(6,2),

    ipl_max NUMERIC(6,2),


    -- PRIORIDADE INTEGRADA

    prioridade_integrada_media NUMERIC(6,2),

    prioridade_integrada_min NUMERIC(6,2),

    prioridade_integrada_max NUMERIC(6,2),


    -- COMPONENTES

    score_hidrologia_medio NUMERIC(6,2),

    score_conectividade_medio NUMERIC(6,2),

    score_declividade_medio NUMERIC(6,2),

    score_elegibilidade_medio NUMERIC(6,2),


    -- CARACTERIZAÇÃO

    distancia_drenagem_media_m NUMERIC(12,2),

    distancia_drenagem_min_m NUMERIC(12,2),

    vegetacao_entorno_media_pct NUMERIC(8,2),

    declividade_media_pct NUMERIC(8,2),

    uso_predominante VARCHAR(120),


    -- ROBUSTEZ

    pct_celulas_estabilidade_alta NUMERIC(6,2),

    amplitude_ipl_media NUMERIC(6,2),

    robustez_area VARCHAR(20),


    -- CLASSIFICAÇÃO

    classificacao_area VARCHAR(30),

    status_area VARCHAR(40),


    -- RANK

    rank_area_municipio INTEGER,

    rank_area_geral INTEGER,


    versao_areas VARCHAR(30) NOT NULL,


    geom GEOMETRY(MULTIPOLYGON, 5880),


    data_calculo TIMESTAMP
        NOT NULL
        DEFAULT CURRENT_TIMESTAMP,


    CONSTRAINT fk_area_municipio

        FOREIGN KEY (codigo_ibge)

        REFERENCES core.dim_municipio(
            codigo_ibge
        ),


    CONSTRAINT uq_area_cluster

        UNIQUE (
            versao_areas,
            cluster_ref
        )
);


CREATE INDEX idx_area_prioritaria_geom

ON spatial.area_prioritaria

USING GIST (geom);


CREATE INDEX idx_area_prioritaria_municipio

ON spatial.area_prioritaria(
    codigo_ibge
);


-- ============================================================
-- RASTREABILIDADE
-- CÉLULA → ÁREA
-- ============================================================

CREATE TABLE spatial.area_prioritaria_celula (

    id_area BIGINT NOT NULL,

    id_celula BIGINT NOT NULL,


    PRIMARY KEY (
        id_area,
        id_celula
    ),


    FOREIGN KEY (id_area)

        REFERENCES spatial.area_prioritaria(
            id_area
        )

        ON DELETE CASCADE,


    FOREIGN KEY (id_celula)

        REFERENCES spatial.celula_prioridade(
            id_celula
        )

        ON DELETE CASCADE

);




-- ============================================================
-- 1. MUNICÍPIOS DESTA EXECUÇÃO
-- ============================================================

DROP TABLE IF EXISTS
staging.municipio_9f;


CREATE TABLE staging.municipio_9f AS

SELECT

    codigo_ibge,

    rank_ipa

FROM spatial.municipio_alvo

ORDER BY rank_ipa

LIMIT {LIMITE_MUNICIPIOS};


SELECT
    to_regclass('staging.municipio_9f') AS municipio,
    to_regclass('staging.celula_cluster_9f') AS celulas,
    to_regclass('staging.area_geom_9f') AS areas,
    to_regclass('staging.area_celula_9f') AS relacionamento;



SELECT

    m.nome_municipio,

    COUNT(*) AS agrupamentos,

    COUNT(*)
    FILTER (
        WHERE a.status_area =
        'Área prioritária contínua'
    ) AS areas_continuas,

    COUNT(*)
    FILTER (
        WHERE a.status_area =
        'Núcleo isolado'
    ) AS nucleos_isolados

FROM spatial.area_prioritaria a

JOIN core.dim_municipio m
    ON m.codigo_ibge = a.codigo_ibge

WHERE
    a.versao_areas =
    'areas_v1.0_2024'

GROUP BY
    m.nome_municipio;



WITH candidatas AS (

    SELECT
        COUNT(*) AS total

    FROM spatial.celula_prioridade

    WHERE

        prioridade_integrada >= 80

        AND estabilidade_ipl
            IN ('Alta', 'Media')

        AND versao_ipl =
            'ipl_v1.0_2024'

        AND codigo_ibge IN (

            SELECT codigo_ibge
            FROM staging.municipio_9f

        )
),

associadas AS (

    SELECT
        COUNT(DISTINCT ac.id_celula)
        AS total

    FROM spatial.area_prioritaria_celula ac

    JOIN spatial.area_prioritaria a
        ON a.id_area = ac.id_area

    WHERE
        a.versao_areas =
        'areas_v1.0_2024'

)

SELECT

    candidatas.total
        AS candidatas,

    associadas.total
        AS associadas,

    candidatas.total
    -
    associadas.total
        AS diferenca

FROM candidatas,
     associadas;



SELECT

    id_celula,

    COUNT(*) AS quantidade

FROM spatial.area_prioritaria_celula

GROUP BY id_celula

HAVING COUNT(*) > 1;



SELECT

    COUNT(*) AS areas,

    COUNT(*)
    FILTER (
        WHERE ST_IsValid(geom)
    ) AS validas,

    COUNT(*)
    FILTER (
        WHERE NOT ST_IsValid(geom)
    ) AS invalidas

FROM spatial.area_prioritaria

WHERE
    versao_areas =
    'areas_v1.0_2024';



SELECT

    codigo_area,

    ROUND(
        area_grade_ha,
        2
    ) AS soma_celulas_ha,

    ROUND(
        area_geometrica_ha,
        2
    ) AS geometria_ha,

    ROUND(

        ABS(
            area_grade_ha
            -
            area_geometrica_ha
        ),

        4

    ) AS diferenca_ha

FROM spatial.area_prioritaria

WHERE
    versao_areas =
    'areas_v1.0_2024'

ORDER BY
    diferenca_ha DESC

LIMIT 20;



SELECT

    a.rank_area_geral,

    a.codigo_area,

    m.nome_municipio,

    a.numero_celulas,

    ROUND(
        a.area_grade_ha,
        1
    ) AS area_ha,

    ROUND(
        a.ipa_municipal,
        1
    ) AS ipa,

    ROUND(
        a.ipl_medio,
        1
    ) AS ipl,

    ROUND(
        a.prioridade_integrada_media,
        1
    ) AS prioridade,

    a.robustez_area,

    a.status_area,

    a.uso_predominante

FROM spatial.area_prioritaria a

JOIN core.dim_municipio m
    ON m.codigo_ibge = a.codigo_ibge

WHERE

    a.versao_areas =
        'areas_v1.0_2024'

ORDER BY
    a.rank_area_geral

LIMIT 50;



SELECT

    a.codigo_area,

    m.nome_municipio,

    ROUND(
        a.area_grade_ha,
        1
    ) AS area_ha,

    ROUND(
        a.prioridade_integrada_media,
        1
    ) AS prioridade_media,

    ROUND(
        a.prioridade_integrada_min,
        1
    ) AS prioridade_min,

    ROUND(
        a.prioridade_integrada_max,
        1
    ) AS prioridade_max,

    ROUND(
        a.distancia_drenagem_media_m,
        0
    ) AS distancia_agua_m,

    ROUND(
        a.vegetacao_entorno_media_pct,
        1
    ) AS vegetacao_entorno,

    ROUND(
        a.declividade_media_pct,
        1
    ) AS declividade,

    a.uso_predominante,

    a.robustez_area

FROM spatial.area_prioritaria a

JOIN core.dim_municipio m
    ON m.codigo_ibge = a.codigo_ibge

WHERE

    a.status_area =
        'Área prioritária contínua'

    AND a.robustez_area =
        'Alta'

ORDER BY

    a.prioridade_integrada_media DESC;




CREATE OR REPLACE VIEW
spatial.vw_areas_prioritarias AS

SELECT

    a.id_area,

    a.codigo_area,

    a.codigo_ibge,

    m.nome_municipio,

    a.rank_area_municipio,

    a.rank_area_geral,

    a.numero_celulas,

    a.area_grade_ha,

    a.area_uso_candidato_ha,

    a.ipa_municipal,

    a.ipl_medio,

    a.prioridade_integrada_media,

    a.prioridade_integrada_min,

    a.prioridade_integrada_max,

    a.score_hidrologia_medio,

    a.score_conectividade_medio,

    a.score_declividade_medio,

    a.score_elegibilidade_medio,

    a.distancia_drenagem_media_m,

    a.vegetacao_entorno_media_pct,

    a.declividade_media_pct,

    a.uso_predominante,

    a.pct_celulas_estabilidade_alta,

    a.robustez_area,

    a.status_area,

    a.geom

FROM spatial.area_prioritaria a

JOIN core.dim_municipio m

    ON m.codigo_ibge =
       a.codigo_ibge

WHERE
    a.versao_areas =
    'areas_v1.0_2024';




SELECT

    status_area,

    COUNT(*) AS areas,

    ROUND(
        SUM(area_grade_ha),
        1
    ) AS area_total_ha

FROM spatial.area_prioritaria

WHERE
    versao_areas =
    'areas_v1.0_2024'

GROUP BY
    status_area;


PARTITION BY codigo_ibge