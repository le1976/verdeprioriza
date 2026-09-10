-- ============================================================
-- VerdePrioriza
-- Módulo 5
-- Fogo e Queimadas
-- ============================================================


-- ------------------------------------------------------------
-- INPE - ampliar tabela RAW
-- ------------------------------------------------------------

ALTER TABLE raw.inpe_foco_queimada

    ADD COLUMN IF NOT EXISTS codigo_ibge VARCHAR(7),

    ADD COLUMN IF NOT EXISTS ano SMALLINT,

    ADD COLUMN IF NOT EXISTS dia_sem_chuva INTEGER,

    ADD COLUMN IF NOT EXISTS precipitacao DOUBLE PRECISION,

    ADD COLUMN IF NOT EXISTS risco_fogo DOUBLE PRECISION,

    ADD COLUMN IF NOT EXISTS frp DOUBLE PRECISION,

    ADD COLUMN IF NOT EXISTS satelite_referencia BOOLEAN

        NOT NULL DEFAULT FALSE;


CREATE INDEX IF NOT EXISTS idx_inpe_foco_ano
ON raw.inpe_foco_queimada (ano);


CREATE INDEX IF NOT EXISTS idx_inpe_codigo_ano
ON raw.inpe_foco_queimada (
    codigo_ibge,
    ano
);

CREATE TABLE IF NOT EXISTS staging.inpe_fogo_municipio_ano (

    codigo_ibge VARCHAR(7) NOT NULL,

    ano SMALLINT NOT NULL,

    focos_referencia INTEGER NOT NULL DEFAULT 0,

    frp_medio NUMERIC(12,4),

    frp_maximo NUMERIC(12,4),

    risco_fogo_medio NUMERIC(10,4),

    dias_sem_chuva_medio NUMERIC(10,2),

    focos_por_100_km2 NUMERIC(12,4),

    data_processamento
        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (
        codigo_ibge,
        ano
    ),

    FOREIGN KEY (codigo_ibge)
        REFERENCES core.dim_municipio(codigo_ibge)

);

CREATE TABLE IF NOT EXISTS raw.mapbiomas_fogo_municipio (

    id BIGSERIAL PRIMARY KEY,

    codigo_ibge VARCHAR(7),

    municipio VARCHAR(150),

    ano SMALLINT,

    area_queimada_ha NUMERIC(18,4),

    colecao VARCHAR(20),

    arquivo_origem VARCHAR(255),

    data_carga
        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP

);

CREATE INDEX IF NOT EXISTS idx_mapbiomas_fogo_codigo_ano
ON raw.mapbiomas_fogo_municipio (
    codigo_ibge,
    ano
);

CREATE TABLE IF NOT EXISTS staging.fogo_municipio_ano (

    codigo_ibge VARCHAR(7) NOT NULL,

    ano SMALLINT NOT NULL,

    area_queimada_ha NUMERIC(18,4)
        NOT NULL DEFAULT 0,

    area_queimada_pct NUMERIC(12,6)
        NOT NULL DEFAULT 0,

    colecao VARCHAR(20) NOT NULL,

    data_processamento
        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (
        codigo_ibge,
        ano,
        colecao
    ),

    FOREIGN KEY (codigo_ibge)
        REFERENCES core.dim_municipio(codigo_ibge)

);

CREATE TABLE IF NOT EXISTS analytics.fogo_municipio (

    codigo_ibge VARCHAR(7) PRIMARY KEY,

    ano_referencia SMALLINT NOT NULL,

    area_queimada_ha_ano NUMERIC(18,4),

    area_queimada_pct_ano NUMERIC(12,6),

    media_anual_queimada_5a_ha NUMERIC(18,4),

    media_anual_queimada_5a_pct NUMERIC(12,6),

    carga_fogo_10a_pct NUMERIC(12,6),

    anos_com_fogo_10a INTEGER,

    focos_inpe_ano INTEGER,

    focos_inpe_5a INTEGER,

    data_calculo
        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (codigo_ibge)
        REFERENCES core.dim_municipio(codigo_ibge)

);