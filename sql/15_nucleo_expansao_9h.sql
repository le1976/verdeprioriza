-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 9H
-- NÚCLEO + EXPANSÃO CONTROLADA
-- VERSÃO ESTADUAL v1.1 / REFERÊNCIA 2024
--
-- METODOLOGIA CALIBRADA NA ETAPA 9G
--
-- SUPORTE:
-- 55,84 <= Prioridade Integrada < 58,44
--
-- NÚCLEO:
-- Prioridade Integrada >= 58,44
--
-- PRIORIDADE EXCEPCIONAL (informativa):
-- Prioridade Integrada >= 61,46
--
-- DISTÂNCIA MÁXIMA SUPORTE -> NÚCLEO:
-- 500 m
--
-- ROBUSTEZ DA ÁREA:
-- amplitude IPL média <= 7,04          -> Alta
-- 7,04 < amplitude IPL média <= 9,18  -> Media
-- amplitude IPL média > 9,18          -> Baixa
--
-- ÁREA OPERACIONAL MÍNIMA:
-- 10 ha
--
-- CRS MÉTRICO:
-- SIRGAS 2000 / Brazil Polyconic
-- EPSG:5880
-- ============================================================

BEGIN;

DROP VIEW IF EXISTS spatial.vw_areas_prioritarias_9h;
DROP TABLE IF EXISTS spatial.area_prioritaria_9h_celula;
DROP TABLE IF EXISTS spatial.area_prioritaria_9h;
DROP TABLE IF EXISTS spatial.celula_selecao_9h;
DROP TABLE IF EXISTS staging.area_resultado_9h;
DROP TABLE IF EXISTS staging.area_celula_9h;
DROP TABLE IF EXISTS staging.area_geom_9h;
DROP TABLE IF EXISTS staging.celula_cluster_9h;

CREATE TABLE spatial.celula_selecao_9h (
    id_celula BIGINT PRIMARY KEY,
    codigo_ibge VARCHAR(7) NOT NULL,
    tipo_selecao VARCHAR(20) NOT NULL,
    nivel_prioridade VARCHAR(20) NOT NULL,
    prioridade_integrada NUMERIC(8,4),
    distancia_nucleo_m NUMERIC(12,2),
    id_nucleo_proximo BIGINT,
    geom GEOMETRY(MULTIPOLYGON, 5880),
    data_calculo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_selecao_celula
        FOREIGN KEY (id_celula)
        REFERENCES spatial.celula_prioridade(id_celula),

    CONSTRAINT fk_selecao_municipio
        FOREIGN KEY (codigo_ibge)
        REFERENCES core.dim_municipio(codigo_ibge),

    CONSTRAINT ck_tipo_selecao
        CHECK (tipo_selecao IN ('Nucleo','Suporte')),

    CONSTRAINT ck_nivel_prioridade_9h
        CHECK (nivel_prioridade IN ('Excepcional','Nucleo','Suporte'))
);

CREATE INDEX idx_celula_selecao_9h_geom
ON spatial.celula_selecao_9h USING GIST (geom);

CREATE INDEX idx_celula_selecao_9h_municipio
ON spatial.celula_selecao_9h (codigo_ibge);

CREATE INDEX idx_celula_selecao_9h_tipo
ON spatial.celula_selecao_9h (tipo_selecao);

CREATE INDEX idx_celula_selecao_9h_nivel
ON spatial.celula_selecao_9h (nivel_prioridade);

-- ============================================================
-- 2. NÚCLEOS
-- ============================================================

INSERT INTO spatial.celula_selecao_9h (
    id_celula,
    codigo_ibge,
    tipo_selecao,
    nivel_prioridade,
    prioridade_integrada,
    distancia_nucleo_m,
    id_nucleo_proximo,
    geom
)
SELECT
    c.id_celula,
    c.codigo_ibge,
    'Nucleo',
    CASE
        WHEN c.prioridade_integrada >= 61.46 THEN 'Excepcional'
        ELSE 'Nucleo'
    END,
    c.prioridade_integrada,
    0,
    c.id_celula,
    ST_Multi(ST_CollectionExtract(c.geom,3))::geometry(MULTIPOLYGON,5880)
FROM spatial.celula_prioridade c
JOIN spatial.municipio_alvo m
  ON m.codigo_ibge = c.codigo_ibge
WHERE c.prioridade_integrada IS NOT NULL
  AND c.prioridade_integrada >= 58.44
  AND c.estabilidade_ipl IN ('Alta','Media')
  AND c.versao_ipl = 'ipl_v1.0_2024'
  AND c.area_ha >= 1
  AND c.pixels_validos >= 10
  AND c.geom IS NOT NULL
  AND NOT ST_IsEmpty(c.geom);

-- ============================================================
-- 3. SUPORTES
-- ============================================================

INSERT INTO spatial.celula_selecao_9h (
    id_celula,
    codigo_ibge,
    tipo_selecao,
    nivel_prioridade,
    prioridade_integrada,
    distancia_nucleo_m,
    id_nucleo_proximo,
    geom
)
SELECT
    s.id_celula,
    s.codigo_ibge,
    'Suporte',
    'Suporte',
    s.prioridade_integrada,
    nucleo.distancia_m,
    nucleo.id_nucleo,
    ST_Multi(ST_CollectionExtract(s.geom,3))::geometry(MULTIPOLYGON,5880)
FROM spatial.celula_prioridade s
JOIN spatial.municipio_alvo m
  ON m.codigo_ibge = s.codigo_ibge
JOIN LATERAL (
    SELECT
        n.id_celula AS id_nucleo,
        ST_Distance(
            ST_PointOnSurface(s.geom),
            ST_PointOnSurface(n.geom)
        ) AS distancia_m
    FROM spatial.celula_selecao_9h n
    WHERE n.codigo_ibge = s.codigo_ibge
      AND n.tipo_selecao = 'Nucleo'
      AND ST_DWithin(
            ST_PointOnSurface(s.geom),
            ST_PointOnSurface(n.geom),
            500
          )
    ORDER BY
        ST_Distance(
            ST_PointOnSurface(s.geom),
            ST_PointOnSurface(n.geom)
        ),
        n.id_celula
    LIMIT 1
) nucleo ON TRUE
WHERE s.prioridade_integrada IS NOT NULL
  AND s.prioridade_integrada >= 55.84
  AND s.prioridade_integrada < 58.44
  AND s.estabilidade_ipl IN ('Alta','Media')
  AND s.versao_ipl = 'ipl_v1.0_2024'
  AND s.area_ha >= 1
  AND s.pixels_validos >= 10
  AND s.geom IS NOT NULL
  AND NOT ST_IsEmpty(s.geom);

-- ============================================================
-- 4. CLUSTERIZAÇÃO
-- ============================================================

CREATE TABLE staging.celula_cluster_9h AS
SELECT
    s.*,
    ST_ClusterDBSCAN(
        s.geom,
        eps => 0.5,
        minpoints => 1
    ) OVER (
        PARTITION BY s.codigo_ibge
        ORDER BY s.id_celula
    ) AS cluster_id
FROM spatial.celula_selecao_9h s;

CREATE INDEX idx_celula_cluster_9h_geom
ON staging.celula_cluster_9h USING GIST (geom);

-- ============================================================
-- 5. DISSOLVER CLUSTERS
-- ============================================================

CREATE TABLE staging.area_geom_9h AS
WITH dissolvido AS (
    SELECT
        codigo_ibge,
        cluster_id,
        ST_UnaryUnion(ST_Collect(geom)) AS geom
    FROM staging.celula_cluster_9h
    WHERE cluster_id IS NOT NULL
    GROUP BY codigo_ibge, cluster_id
),
partes AS (
    SELECT
        codigo_ibge,
        cluster_id,
        COALESCE((dumped).path[1],1) AS componente_id,
        (dumped).geom AS geom
    FROM (
        SELECT
            codigo_ibge,
            cluster_id,
            ST_Dump(ST_CollectionExtract(geom,3)) AS dumped
        FROM dissolvido
    ) x
)
SELECT
    codigo_ibge,
    cluster_id,
    componente_id,
    CONCAT(
        codigo_ibge, ':', cluster_id::TEXT, ':', componente_id::TEXT
    ) AS cluster_ref,
    ST_Multi(ST_CollectionExtract(geom,3))::geometry(MULTIPOLYGON,5880) AS geom
FROM partes
WHERE geom IS NOT NULL
  AND NOT ST_IsEmpty(geom);

CREATE INDEX idx_area_geom_9h_geom
ON staging.area_geom_9h USING GIST (geom);

CREATE INDEX idx_area_geom_9h_cluster
ON staging.area_geom_9h (cluster_ref);

-- ============================================================
-- 6. CÉLULA -> ÁREA
-- ============================================================

CREATE TABLE staging.area_celula_9h AS
SELECT
    a.codigo_ibge,
    a.cluster_id,
    a.componente_id,
    a.cluster_ref,
    c.id_celula,
    c.tipo_selecao,
    c.nivel_prioridade
FROM staging.area_geom_9h a
JOIN staging.celula_cluster_9h c
  ON c.codigo_ibge = a.codigo_ibge
 AND c.cluster_id = a.cluster_id
WHERE ST_Covers(
    a.geom,
    ST_PointOnSurface(c.geom)
);

CREATE INDEX idx_area_celula_9h_id
ON staging.area_celula_9h (id_celula);

CREATE INDEX idx_area_celula_9h_cluster
ON staging.area_celula_9h (cluster_ref);

-- ============================================================
-- 7. TABELA FINAL
-- ============================================================

CREATE TABLE spatial.area_prioritaria_9h (
    id_area BIGSERIAL PRIMARY KEY,
    codigo_area VARCHAR(40) NOT NULL,
    cluster_ref VARCHAR(150) NOT NULL,
    codigo_ibge VARCHAR(7) NOT NULL,

    numero_celulas INTEGER,
    numero_nucleos INTEGER,
    numero_suportes INTEGER,
    numero_excepcionais INTEGER,

    area_total_ha NUMERIC(14,4),
    area_geometrica_ha NUMERIC(14,4),
    area_nucleo_ha NUMERIC(14,4),
    area_suporte_ha NUMERIC(14,4),
    area_excepcional_ha NUMERIC(14,4),
    pct_area_nucleo NUMERIC(8,2),
    pct_area_excepcional NUMERIC(8,2),

    area_uso_candidato_ha NUMERIC(14,4),
    vegetacao_interna_estimada_ha NUMERIC(14,4),

    ipa_municipal NUMERIC(8,2),

    ipl_medio NUMERIC(8,2),
    ipl_min NUMERIC(8,2),
    ipl_max NUMERIC(8,2),

    prioridade_integrada_media NUMERIC(8,2),
    prioridade_integrada_min NUMERIC(8,2),
    prioridade_integrada_max NUMERIC(8,2),

    score_hidrologia_medio NUMERIC(8,2),
    score_conectividade_medio NUMERIC(8,2),
    score_declividade_medio NUMERIC(8,2),
    score_elegibilidade_medio NUMERIC(8,2),

    distancia_drenagem_media_m NUMERIC(12,2),
    vegetacao_entorno_media_pct NUMERIC(8,2),
    declividade_media_pct NUMERIC(8,2),
    uso_predominante VARCHAR(120),

    distancia_suporte_nucleo_media_m NUMERIC(12,2),
    distancia_suporte_nucleo_max_m NUMERIC(12,2),

    amplitude_ipl_media NUMERIC(8,2),
    pct_celulas_estabilidade_alta NUMERIC(8,2),
    robustez_area VARCHAR(20),

    percentil_prioridade NUMERIC(8,2),
    classe_relativa VARCHAR(30),

    status_area VARCHAR(40),
    rank_area_municipio INTEGER,
    rank_area_geral INTEGER,
    rank_nucleo_isolado_municipio INTEGER,
    rank_nucleo_isolado_geral INTEGER,

    versao_areas VARCHAR(30) NOT NULL,

    geom GEOMETRY(MULTIPOLYGON,5880),

    data_calculo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_area_9h_municipio
        FOREIGN KEY (codigo_ibge)
        REFERENCES core.dim_municipio(codigo_ibge),

    CONSTRAINT uq_area_9h_cluster
        UNIQUE (versao_areas, cluster_ref),

    CONSTRAINT uq_area_9h_codigo
        UNIQUE (versao_areas, codigo_area)
);

CREATE INDEX idx_area_prioritaria_9h_geom
ON spatial.area_prioritaria_9h USING GIST (geom);

CREATE INDEX idx_area_prioritaria_9h_municipio
ON spatial.area_prioritaria_9h (codigo_ibge);

CREATE INDEX idx_area_prioritaria_9h_rank
ON spatial.area_prioritaria_9h (rank_area_geral);

-- ============================================================
-- 8. RASTREABILIDADE
-- ============================================================

CREATE TABLE spatial.area_prioritaria_9h_celula (
    id_area BIGINT NOT NULL,
    id_celula BIGINT NOT NULL,
    tipo_selecao VARCHAR(20) NOT NULL,
    nivel_prioridade VARCHAR(20) NOT NULL,

    PRIMARY KEY (id_area,id_celula),

    FOREIGN KEY (id_area)
        REFERENCES spatial.area_prioritaria_9h(id_area)
        ON DELETE CASCADE,

    FOREIGN KEY (id_celula)
        REFERENCES spatial.celula_prioridade(id_celula)
        ON DELETE CASCADE
);

-- ============================================================
-- 9. MÉTRICAS DAS ÁREAS
-- ============================================================

CREATE TABLE staging.area_resultado_9h AS
WITH metricas AS (
    SELECT
        a.codigo_ibge,
        a.cluster_ref,
        a.geom,

        COUNT(*) AS numero_celulas,
        COUNT(*) FILTER (WHERE s.tipo_selecao='Nucleo') AS numero_nucleos,
        COUNT(*) FILTER (WHERE s.tipo_selecao='Suporte') AS numero_suportes,
        COUNT(*) FILTER (WHERE s.nivel_prioridade='Excepcional') AS numero_excepcionais,

        SUM(c.area_ha) AS area_total_ha,
        ST_Area(a.geom)/10000.0 AS area_geometrica_ha,

        COALESCE(SUM(c.area_ha) FILTER (WHERE s.tipo_selecao='Nucleo'),0) AS area_nucleo_ha,
        COALESCE(SUM(c.area_ha) FILTER (WHERE s.tipo_selecao='Suporte'),0) AS area_suporte_ha,
        COALESCE(SUM(c.area_ha) FILTER (WHERE s.nivel_prioridade='Excepcional'),0) AS area_excepcional_ha,

        SUM(c.area_ha*c.pct_uso_elegivel/100.0) AS area_uso_candidato_ha,
        SUM(c.area_ha*c.pct_vegetacao_natural/100.0) AS vegetacao_interna_estimada_ha,

        SUM(c.prioridade_local*c.area_ha)/NULLIF(SUM(c.area_ha),0) AS ipl_medio,
        MIN(c.prioridade_local) AS ipl_min,
        MAX(c.prioridade_local) AS ipl_max,

        SUM(c.prioridade_integrada*c.area_ha)/NULLIF(SUM(c.area_ha),0) AS prioridade_integrada_media,
        MIN(c.prioridade_integrada) AS prioridade_integrada_min,
        MAX(c.prioridade_integrada) AS prioridade_integrada_max,

        SUM(c.score_hidrologia*c.area_ha)/NULLIF(SUM(c.area_ha),0) AS score_hidrologia_medio,
        SUM(c.score_conectividade*c.area_ha)/NULLIF(SUM(c.area_ha),0) AS score_conectividade_medio,
        SUM(c.score_declividade*c.area_ha)/NULLIF(SUM(c.area_ha),0) AS score_declividade_medio,
        SUM(c.score_elegibilidade*c.area_ha)/NULLIF(SUM(c.area_ha),0) AS score_elegibilidade_medio,

        SUM(c.distancia_drenagem_m*c.area_ha)/NULLIF(SUM(c.area_ha),0) AS distancia_drenagem_media_m,
        SUM(c.vegetacao_entorno_pct*c.area_ha)/NULLIF(SUM(c.area_ha),0) AS vegetacao_entorno_media_pct,
        SUM(c.declividade_media_pct*c.area_ha)/NULLIF(SUM(c.area_ha),0) AS declividade_media_pct,

        MODE() WITHIN GROUP (ORDER BY c.uso_predominante) AS uso_predominante,

        AVG(s.distancia_nucleo_m) FILTER (WHERE s.tipo_selecao='Suporte') AS distancia_suporte_nucleo_media_m,
        MAX(s.distancia_nucleo_m) FILTER (WHERE s.tipo_selecao='Suporte') AS distancia_suporte_nucleo_max_m,

        SUM(c.amplitude_ipl*c.area_ha)/NULLIF(SUM(c.area_ha),0) AS amplitude_ipl_media,

        COUNT(*) FILTER (WHERE c.estabilidade_ipl='Alta')*100.0/NULLIF(COUNT(*),0) AS pct_celulas_estabilidade_alta

    FROM staging.area_geom_9h a
    JOIN staging.area_celula_9h r
      ON r.cluster_ref = a.cluster_ref
    JOIN spatial.celula_selecao_9h s
      ON s.id_celula = r.id_celula
    JOIN spatial.celula_prioridade c
      ON c.id_celula = r.id_celula
    GROUP BY a.codigo_ibge,a.cluster_ref,a.geom
    HAVING COUNT(*) FILTER (WHERE s.tipo_selecao='Nucleo') > 0
),
com_ipa AS (
    SELECT
        x.*,
        i.ipa AS ipa_municipal
    FROM metricas x
    JOIN analytics.ipa_municipio i
      ON i.codigo_ibge = x.codigo_ibge
     AND i.ano_referencia = 2024
     AND i.versao_modelo = 'ipa_v1.0_2024'
),
classificado AS (
    SELECT
        *,
        area_nucleo_ha/NULLIF(area_total_ha,0)*100 AS pct_area_nucleo,
        area_excepcional_ha/NULLIF(area_total_ha,0)*100 AS pct_area_excepcional,

        CASE
            WHEN amplitude_ipl_media <= 7.04 THEN 'Alta'
            WHEN amplitude_ipl_media <= 9.18 THEN 'Media'
            ELSE 'Baixa'
        END AS robustez_area,

        CASE
            WHEN area_total_ha >= 10 AND numero_nucleos >= 1
                THEN 'Área prioritária final'
            ELSE 'Núcleo isolado'
        END AS status_area
    FROM com_ipa
),
ranqueado AS (
    SELECT
        *,

        CASE
            WHEN status_area='Área prioritária final'
            THEN ROW_NUMBER() OVER (
                PARTITION BY codigo_ibge,status_area
                ORDER BY prioridade_integrada_media DESC,
                         pct_area_nucleo DESC,
                         area_total_ha DESC,
                         cluster_ref
            )::INTEGER
        END AS rank_area_municipio,

        CASE
            WHEN status_area='Área prioritária final'
            THEN ROW_NUMBER() OVER (
                PARTITION BY status_area
                ORDER BY prioridade_integrada_media DESC,
                         pct_area_nucleo DESC,
                         area_total_ha DESC,
                         codigo_ibge,
                         cluster_ref
            )::INTEGER
        END AS rank_area_geral,

        CASE
            WHEN status_area='Núcleo isolado'
            THEN ROW_NUMBER() OVER (
                PARTITION BY codigo_ibge,status_area
                ORDER BY prioridade_integrada_media DESC,
                         area_total_ha DESC,
                         cluster_ref
            )::INTEGER
        END AS rank_nucleo_isolado_municipio,

        CASE
            WHEN status_area='Núcleo isolado'
            THEN ROW_NUMBER() OVER (
                PARTITION BY status_area
                ORDER BY prioridade_integrada_media DESC,
                         area_total_ha DESC,
                         codigo_ibge,
                         cluster_ref
            )::INTEGER
        END AS rank_nucleo_isolado_geral,

        CUME_DIST() OVER (
            PARTITION BY status_area
            ORDER BY prioridade_integrada_media
        )*100 AS percentil_prioridade

    FROM classificado
),
final AS (
    SELECT
        *,

        CASE
            WHEN percentil_prioridade >= 90 THEN 'Muito alta'
            WHEN percentil_prioridade >= 75 THEN 'Alta'
            WHEN percentil_prioridade >= 50 THEN 'Media'
            WHEN percentil_prioridade >= 25 THEN 'Baixa'
            ELSE 'Muito baixa'
        END AS classe_relativa,

        CASE
            WHEN status_area='Área prioritária final'
            THEN CONCAT(
                codigo_ibge,
                '-H',
                LPAD(rank_area_municipio::TEXT,3,'0')
            )
            ELSE CONCAT(
                codigo_ibge,
                '-I',
                LPAD(rank_nucleo_isolado_municipio::TEXT,3,'0')
            )
        END AS codigo_area

    FROM ranqueado
)
SELECT *
FROM final;

-- ============================================================
-- 10. INSERIR RESULTADO FINAL
-- ============================================================

INSERT INTO spatial.area_prioritaria_9h (
    codigo_area,
    cluster_ref,
    codigo_ibge,
    numero_celulas,
    numero_nucleos,
    numero_suportes,
    numero_excepcionais,
    area_total_ha,
    area_geometrica_ha,
    area_nucleo_ha,
    area_suporte_ha,
    area_excepcional_ha,
    pct_area_nucleo,
    pct_area_excepcional,
    area_uso_candidato_ha,
    vegetacao_interna_estimada_ha,
    ipa_municipal,
    ipl_medio,
    ipl_min,
    ipl_max,
    prioridade_integrada_media,
    prioridade_integrada_min,
    prioridade_integrada_max,
    score_hidrologia_medio,
    score_conectividade_medio,
    score_declividade_medio,
    score_elegibilidade_medio,
    distancia_drenagem_media_m,
    vegetacao_entorno_media_pct,
    declividade_media_pct,
    uso_predominante,
    distancia_suporte_nucleo_media_m,
    distancia_suporte_nucleo_max_m,
    amplitude_ipl_media,
    pct_celulas_estabilidade_alta,
    robustez_area,
    percentil_prioridade,
    classe_relativa,
    status_area,
    rank_area_municipio,
    rank_area_geral,
    rank_nucleo_isolado_municipio,
    rank_nucleo_isolado_geral,
    versao_areas,
    geom
)
SELECT
    codigo_area,
    cluster_ref,
    codigo_ibge,
    numero_celulas,
    numero_nucleos,
    numero_suportes,
    numero_excepcionais,
    area_total_ha,
    area_geometrica_ha,
    area_nucleo_ha,
    area_suporte_ha,
    area_excepcional_ha,
    pct_area_nucleo,
    pct_area_excepcional,
    area_uso_candidato_ha,
    vegetacao_interna_estimada_ha,
    ipa_municipal,
    ipl_medio,
    ipl_min,
    ipl_max,
    prioridade_integrada_media,
    prioridade_integrada_min,
    prioridade_integrada_max,
    score_hidrologia_medio,
    score_conectividade_medio,
    score_declividade_medio,
    score_elegibilidade_medio,
    distancia_drenagem_media_m,
    vegetacao_entorno_media_pct,
    declividade_media_pct,
    uso_predominante,
    distancia_suporte_nucleo_media_m,
    distancia_suporte_nucleo_max_m,
    amplitude_ipl_media,
    pct_celulas_estabilidade_alta,
    robustez_area,
    percentil_prioridade,
    classe_relativa,
    status_area,
    rank_area_municipio,
    rank_area_geral,
    rank_nucleo_isolado_municipio,
    rank_nucleo_isolado_geral,
    'areas_9h_v1.1_2024',
    ST_Multi(ST_CollectionExtract(geom,3))::geometry(MULTIPOLYGON,5880)
FROM staging.area_resultado_9h;

-- ============================================================
-- 11. RASTREABILIDADE
-- ============================================================

INSERT INTO spatial.area_prioritaria_9h_celula (
    id_area,
    id_celula,
    tipo_selecao,
    nivel_prioridade
)
SELECT
    a.id_area,
    r.id_celula,
    s.tipo_selecao,
    s.nivel_prioridade
FROM spatial.area_prioritaria_9h a
JOIN staging.area_celula_9h r
  ON r.cluster_ref = a.cluster_ref
JOIN spatial.celula_selecao_9h s
  ON s.id_celula = r.id_celula
WHERE a.versao_areas = 'areas_9h_v1.1_2024';

-- ============================================================
-- 12. VIEW FINAL
-- ============================================================

CREATE OR REPLACE VIEW spatial.vw_areas_prioritarias_9h AS
SELECT
    a.id_area,
    a.codigo_area,
    a.codigo_ibge,
    m.nome_municipio,
    a.status_area,
    a.rank_area_municipio,
    a.rank_area_geral,
    a.rank_nucleo_isolado_municipio,
    a.rank_nucleo_isolado_geral,
    a.numero_celulas,
    a.numero_nucleos,
    a.numero_suportes,
    a.numero_excepcionais,
    a.area_total_ha,
    a.area_nucleo_ha,
    a.area_suporte_ha,
    a.area_excepcional_ha,
    a.pct_area_nucleo,
    a.pct_area_excepcional,
    a.area_uso_candidato_ha,
    a.vegetacao_interna_estimada_ha,
    a.ipa_municipal,
    a.ipl_medio,
    a.prioridade_integrada_media,
    a.prioridade_integrada_min,
    a.prioridade_integrada_max,
    a.percentil_prioridade,
    a.classe_relativa,
    a.score_hidrologia_medio,
    a.score_conectividade_medio,
    a.score_declividade_medio,
    a.score_elegibilidade_medio,
    a.distancia_drenagem_media_m,
    a.vegetacao_entorno_media_pct,
    a.declividade_media_pct,
    a.uso_predominante,
    a.distancia_suporte_nucleo_media_m,
    a.distancia_suporte_nucleo_max_m,
    a.amplitude_ipl_media,
    a.pct_celulas_estabilidade_alta,
    a.robustez_area,
    a.versao_areas,
    a.geom
FROM spatial.area_prioritaria_9h a
JOIN core.dim_municipio m
  ON m.codigo_ibge = a.codigo_ibge
WHERE a.versao_areas = 'areas_9h_v1.1_2024';

COMMIT;

-- ============================================================
-- 13. VALIDAÇÕES
-- ============================================================

-- 13.1 Tipos geométricos
SELECT
    GeometryType(geom) AS tipo,
    ST_SRID(geom) AS srid,
    COUNT(*) AS quantidade
FROM spatial.celula_selecao_9h
GROUP BY GeometryType(geom),ST_SRID(geom)
ORDER BY tipo;

-- 13.2 Núcleo / suporte / excepcional
SELECT
    s.tipo_selecao,
    s.nivel_prioridade,
    COUNT(*) AS celulas,
    ROUND(SUM(c.area_ha),2) AS area_ha
FROM spatial.celula_selecao_9h s
JOIN spatial.celula_prioridade c
  ON c.id_celula = s.id_celula
GROUP BY s.tipo_selecao,s.nivel_prioridade
ORDER BY s.tipo_selecao,s.nivel_prioridade;

-- 13.3 Distância suporte -> núcleo
SELECT
    COUNT(*) AS suportes,
    ROUND(MIN(distancia_nucleo_m),2) AS minimo_m,
    ROUND(AVG(distancia_nucleo_m),2) AS media_m,
    ROUND(MAX(distancia_nucleo_m),2) AS maximo_m
FROM spatial.celula_selecao_9h
WHERE tipo_selecao='Suporte';

-- 13.4 Áreas sem núcleo
SELECT COUNT(*) AS areas_sem_nucleo
FROM spatial.area_prioritaria_9h
WHERE numero_nucleos IS NULL
   OR numero_nucleos=0;

-- 13.5 Células duplicadas entre áreas
SELECT id_celula,COUNT(*) AS quantidade
FROM spatial.area_prioritaria_9h_celula
GROUP BY id_celula
HAVING COUNT(*)>1;

-- 13.6 Área total = núcleo + suporte
SELECT
    codigo_area,
    ROUND(area_total_ha,4) AS area_total_ha,
    ROUND(area_nucleo_ha,4) AS nucleo_ha,
    ROUND(area_suporte_ha,4) AS suporte_ha,
    ROUND(
        ABS(area_total_ha-(area_nucleo_ha+area_suporte_ha)),
        6
    ) AS diferenca_ha
FROM spatial.area_prioritaria_9h
ORDER BY diferenca_ha DESC
LIMIT 20;

-- 13.7 Área das células x geometria
SELECT
    codigo_area,
    ROUND(area_total_ha,4) AS soma_celulas_ha,
    ROUND(area_geometrica_ha,4) AS geometria_ha,
    ROUND(ABS(area_total_ha-area_geometrica_ha),6) AS diferenca_ha
FROM spatial.area_prioritaria_9h
ORDER BY diferenca_ha DESC
LIMIT 20;

-- 13.8 Validade geométrica
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE ST_IsValid(geom)) AS validas,
    COUNT(*) FILTER (WHERE NOT ST_IsValid(geom)) AS invalidas
FROM spatial.area_prioritaria_9h;

-- 13.9 Resumo por status
SELECT
    status_area,
    COUNT(*) AS areas,
    ROUND(SUM(area_total_ha),1) AS area_total_ha,
    ROUND(SUM(area_nucleo_ha),1) AS area_nucleo_ha,
    ROUND(SUM(area_suporte_ha),1) AS area_suporte_ha,
    ROUND(SUM(area_excepcional_ha),1) AS area_excepcional_ha
FROM spatial.area_prioritaria_9h
GROUP BY status_area
ORDER BY status_area;

-- 13.10 Robustez
SELECT
    robustez_area,
    COUNT(*) AS areas,
    ROUND(SUM(area_total_ha),1) AS area_ha,
    ROUND(
        SUM(area_total_ha)
        /NULLIF(SUM(SUM(area_total_ha)) OVER (),0)
        *100,
        2
    ) AS pct_area
FROM spatial.area_prioritaria_9h
GROUP BY robustez_area
ORDER BY area_ha DESC;

-- 13.11 Municípios representados
SELECT
    COUNT(DISTINCT codigo_ibge) AS municipios_com_areas
FROM spatial.area_prioritaria_9h;

-- 13.12 Resumo por município
SELECT
    m.nome_municipio,
    COUNT(*) AS objetos,
    COUNT(*) FILTER (
        WHERE a.status_area='Área prioritária final'
    ) AS areas_finais,
    COUNT(*) FILTER (
        WHERE a.status_area='Núcleo isolado'
    ) AS nucleos_isolados,
    ROUND(SUM(a.area_total_ha),1) AS area_total_ha,
    ROUND(SUM(a.area_excepcional_ha),1) AS area_excepcional_ha
FROM spatial.area_prioritaria_9h a
JOIN core.dim_municipio m
  ON m.codigo_ibge = a.codigo_ibge
GROUP BY m.nome_municipio
ORDER BY areas_finais DESC,area_total_ha DESC;

-- 13.13 TOP 50 áreas prioritárias finais
SELECT
    a.rank_area_geral,
    a.codigo_area,
    m.nome_municipio,
    ROUND(a.area_total_ha,1) AS area_total_ha,
    ROUND(a.area_nucleo_ha,1) AS nucleo_ha,
    ROUND(a.area_suporte_ha,1) AS suporte_ha,
    ROUND(a.area_excepcional_ha,1) AS excepcional_ha,
    ROUND(a.pct_area_nucleo,1) AS pct_nucleo,
    ROUND(a.pct_area_excepcional,1) AS pct_excepcional,
    ROUND(a.prioridade_integrada_media,2) AS prioridade,
    ROUND(a.percentil_prioridade,1) AS percentil,
    a.classe_relativa,
    a.robustez_area,
    a.uso_predominante
FROM spatial.area_prioritaria_9h a
JOIN core.dim_municipio m
  ON m.codigo_ibge = a.codigo_ibge
WHERE a.status_area='Área prioritária final'
ORDER BY a.rank_area_geral
LIMIT 50;

-- 13.14 TOP 30 núcleos isolados
SELECT
    a.rank_nucleo_isolado_geral,
    a.codigo_area,
    m.nome_municipio,
    ROUND(a.area_total_ha,2) AS area_total_ha,
    ROUND(a.prioridade_integrada_media,2) AS prioridade,
    ROUND(a.percentil_prioridade,1) AS percentil,
    a.classe_relativa,
    a.robustez_area
FROM spatial.area_prioritaria_9h a
JOIN core.dim_municipio m
  ON m.codigo_ibge = a.codigo_ibge
WHERE a.status_area='Núcleo isolado'
ORDER BY a.rank_nucleo_isolado_geral
LIMIT 30;




UPDATE spatial.celula_prioridade c

SET score_conectividade =

    ROUND(

        LEAST(

            100.0,

            GREATEST(

                0.0,

                (
                    c.vegetacao_entorno_pct
                    /
                    60.0
                )
                *
                100.0

            )

        )::NUMERIC,

        2

    )

WHERE

    c.codigo_ibge IN (

        SELECT codigo_ibge
        FROM spatial.municipio_alvo

    )

    AND c.vegetacao_entorno_pct IS NOT NULL;



SELECT

    m.nome_municipio,

    COUNT(c.id_celula) AS total_celulas,

    COUNT(c.vegetacao_entorno_pct)
        AS com_entorno,

    COUNT(c.score_conectividade)
        AS com_score_conectividade

FROM spatial.municipio_alvo a

JOIN core.dim_municipio m
    ON m.codigo_ibge = a.codigo_ibge

LEFT JOIN spatial.celula_prioridade c
    ON c.codigo_ibge = a.codigo_ibge

GROUP BY
    m.nome_municipio

ORDER BY
    m.nome_municipio;



SELECT
    m.nome_municipio,

    COUNT(*) FILTER (
        WHERE
            c.score_hidrologia IS NOT NULL
            AND c.score_conectividade IS NOT NULL
            AND c.score_declividade IS NOT NULL
            AND c.score_elegibilidade IS NOT NULL
    ) AS componentes_completos,

    COUNT(c.prioridade_local)
        AS com_ipl,

    COUNT(c.prioridade_integrada)
        AS com_prioridade_integrada

FROM spatial.municipio_alvo a

JOIN core.dim_municipio m
    ON m.codigo_ibge = a.codigo_ibge

LEFT JOIN spatial.celula_prioridade c
    ON c.codigo_ibge = a.codigo_ibge

GROUP BY
    m.nome_municipio

ORDER BY
    m.nome_municipio;



SELECT

    COUNT(*) AS celulas_validas,

    ROUND(
        MIN(prioridade_integrada),
        2
    ) AS minimo,

    ROUND(
        PERCENTILE_CONT(0.25)
        WITHIN GROUP (
            ORDER BY prioridade_integrada
        )::NUMERIC,
        2
    ) AS p25,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY prioridade_integrada
        )::NUMERIC,
        2
    ) AS mediana,

    ROUND(
        PERCENTILE_CONT(0.75)
        WITHIN GROUP (
            ORDER BY prioridade_integrada
        )::NUMERIC,
        2
    ) AS p75,

    ROUND(
        PERCENTILE_CONT(0.80)
        WITHIN GROUP (
            ORDER BY prioridade_integrada
        )::NUMERIC,
        2
    ) AS p80,

    ROUND(
        PERCENTILE_CONT(0.85)
        WITHIN GROUP (
            ORDER BY prioridade_integrada
        )::NUMERIC,
        2
    ) AS p85,

    ROUND(
        PERCENTILE_CONT(0.90)
        WITHIN GROUP (
            ORDER BY prioridade_integrada
        )::NUMERIC,
        2
    ) AS p90,

    ROUND(
        PERCENTILE_CONT(0.95)
        WITHIN GROUP (
            ORDER BY prioridade_integrada
        )::NUMERIC,
        2
    ) AS p95,

    ROUND(
        MAX(prioridade_integrada),
        2
    ) AS maximo

FROM spatial.celula_prioridade

WHERE

    prioridade_integrada IS NOT NULL

    AND estabilidade_ipl
        IN ('Alta', 'Media')

    AND versao_ipl =
        'ipl_v1.0_2024'

    AND area_ha >= 1

    AND pixels_validos >= 10

    AND codigo_ibge IN (

        SELECT codigo_ibge
        FROM spatial.municipio_alvo

    );