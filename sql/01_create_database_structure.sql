-- ================================================
-- Projeto: VerdePrioriza
-- Script: Estrutura inicial do banco de dados
-- ================================================

CREATE EXTENSION IF NOT EXISTS postgis;


-- SCHEMAS

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS spatial;
CREATE SCHEMA IF NOT EXISTS analytics;


-- DIMENSÃO MUNICÍPIO

CREATE TABLE IF NOT EXISTS core.dim_municipio (
    id_municipio BIGSERIAL PRIMARY KEY,
    codigo_ibge VARCHAR(7) NOT NULL UNIQUE,
    nome_municipio VARCHAR(150) NOT NULL,
    uf CHAR(2) NOT NULL,
    area_km2 NUMERIC(15,4),
    geom GEOMETRY(MULTIPOLYGON, 4674),
    data_carga TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_municipio_geom
ON core.dim_municipio
USING GIST (geom);


-- MAPBIOMAS RAW

CREATE TABLE IF NOT EXISTS raw.mapbiomas_municipio (
    id BIGSERIAL PRIMARY KEY,
    codigo_ibge VARCHAR(7),
    municipio VARCHAR(150),
    uf CHAR(2),
    ano INTEGER,
    classe VARCHAR(200),
    area_ha NUMERIC(18,4),
    arquivo_origem VARCHAR(255),
    data_carga TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- INPE QUEIMADAS

CREATE TABLE IF NOT EXISTS raw.inpe_foco_queimada (
    id BIGSERIAL PRIMARY KEY,
    data_hora TIMESTAMP,
    satelite VARCHAR(100),
    pais VARCHAR(100),
    estado VARCHAR(100),
    municipio VARCHAR(150),
    bioma VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOMETRY(POINT, 4674),
    arquivo_origem VARCHAR(255),
    data_carga TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inpe_foco_geom
ON raw.inpe_foco_queimada
USING GIST (geom);


-- INDICADORES

CREATE TABLE IF NOT EXISTS analytics.indicador_municipio (
    id BIGSERIAL PRIMARY KEY,
    codigo_ibge VARCHAR(7) NOT NULL,
    ano INTEGER NOT NULL,
    vegetacao_nativa_ha NUMERIC(18,4),
    vegetacao_nativa_pct NUMERIC(10,4),
    agropecuaria_ha NUMERIC(18,4),
    agropecuaria_pct NUMERIC(10,4),
    perda_vegetacao_ha NUMERIC(18,4),
    focos_queimada INTEGER,
    data_calculo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_indicador_municipio
        FOREIGN KEY (codigo_ibge)
        REFERENCES core.dim_municipio(codigo_ibge),

    CONSTRAINT uq_indicador_municipio_ano
        UNIQUE (codigo_ibge, ano)
);


-- ÍNDICE DE PRIORIDADE AMBIENTAL

CREATE TABLE IF NOT EXISTS analytics.ipa_municipio (
    id BIGSERIAL PRIMARY KEY,
    codigo_ibge VARCHAR(7) NOT NULL,
    ano_referencia INTEGER NOT NULL,
    score_vegetacao NUMERIC(6,2),
    score_perda_vegetacao NUMERIC(6,2),
    score_pressao_agropecuaria NUMERIC(6,2),
    score_fogo NUMERIC(6,2),
    ipa NUMERIC(6,2),
    classificacao VARCHAR(30),
    versao_modelo VARCHAR(20),
    data_calculo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_ipa_municipio
        FOREIGN KEY (codigo_ibge)
        REFERENCES core.dim_municipio(codigo_ibge),

    CONSTRAINT uq_ipa_municipio_ano_modelo
        UNIQUE (
            codigo_ibge,
            ano_referencia,
            versao_modelo
        )
);


-- LOG DE CARGAS

CREATE TABLE IF NOT EXISTS core.log_carga_dados (
    id_carga BIGSERIAL PRIMARY KEY,
    fonte VARCHAR(100) NOT NULL,
    arquivo VARCHAR(255),
    data_inicio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_fim TIMESTAMP,
    registros_lidos INTEGER,
    registros_inseridos INTEGER,
    registros_rejeitados INTEGER,
    status VARCHAR(30),
    observacao TEXT
);