-- ============================================================
-- Projeto: VerdePrioriza
-- Módulo 4
-- MapBiomas - Coleção 11
-- ============================================================


-- ------------------------------------------------------------
-- 1. EVOLUÇÃO DA TABELA RAW
-- ------------------------------------------------------------

ALTER TABLE raw.mapbiomas_municipio
    ADD COLUMN IF NOT EXISTS colecao VARCHAR(20),
    ADD COLUMN IF NOT EXISTS bioma VARCHAR(80),
    ADD COLUMN IF NOT EXISTS nivel SMALLINT,
    ADD COLUMN IF NOT EXISTS classe_id INTEGER;


CREATE INDEX IF NOT EXISTS idx_mapbiomas_municipio_ano
ON raw.mapbiomas_municipio (
    codigo_ibge,
    ano
);


CREATE INDEX IF NOT EXISTS idx_mapbiomas_colecao_classe
ON raw.mapbiomas_municipio (
    colecao,
    classe_id
);


-- ------------------------------------------------------------
-- 2. TABELA MUNICÍPIO × ANO CONSOLIDADA
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS staging.mapbiomas_municipio_ano (

    codigo_ibge VARCHAR(7) NOT NULL,

    ano SMALLINT NOT NULL,

    colecao VARCHAR(20) NOT NULL,

    formacao_florestal_ha NUMERIC(18,4) NOT NULL DEFAULT 0,

    vegetacao_herbacea_arbustiva_ha
        NUMERIC(18,4) NOT NULL DEFAULT 0,

    vegetacao_nativa_ha
        NUMERIC(18,4) NOT NULL DEFAULT 0,

    agropecuaria_ha
        NUMERIC(18,4) NOT NULL DEFAULT 0,

    area_nao_vegetada_ha
        NUMERIC(18,4) NOT NULL DEFAULT 0,

    corpo_agua_ha
        NUMERIC(18,4) NOT NULL DEFAULT 0,

    area_mapeada_ha
        NUMERIC(18,4) NOT NULL DEFAULT 0,

    data_processamento
        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_mapbiomas_municipio_ano
        PRIMARY KEY (
            codigo_ibge,
            ano,
            colecao
        ),

    CONSTRAINT fk_mapbiomas_municipio
        FOREIGN KEY (codigo_ibge)
        REFERENCES core.dim_municipio(codigo_ibge)

);


-- ------------------------------------------------------------
-- 3. COMPLEMENTAR INDICADORES
-- ------------------------------------------------------------

ALTER TABLE analytics.indicador_municipio

    ADD COLUMN IF NOT EXISTS colecao_mapbiomas
        VARCHAR(20),

    ADD COLUMN IF NOT EXISTS variacao_liquida_vegetacao_ha_5a
        NUMERIC(18,4),

    ADD COLUMN IF NOT EXISTS variacao_liquida_vegetacao_ha_10a
        NUMERIC(18,4),

    ADD COLUMN IF NOT EXISTS variacao_liquida_vegetacao_ha_40a
        NUMERIC(18,4);


COMMENT ON COLUMN
analytics.indicador_municipio.variacao_liquida_vegetacao_ha_10a

IS
'Variação líquida da área de cobertura natural nos últimos 10 anos. Não representa desmatamento bruto.';