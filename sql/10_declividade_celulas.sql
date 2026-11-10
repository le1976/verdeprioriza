-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 9D
-- RELEVO E DECLIVIDADE
-- Fonte: TOPODATA / INPE
-- ============================================================


ALTER TABLE spatial.celula_prioridade

    ADD COLUMN IF NOT EXISTS
        declividade_p90_pct NUMERIC(10,4),

    ADD COLUMN IF NOT EXISTS
        declividade_max_pct NUMERIC(10,4),

    ADD COLUMN IF NOT EXISTS
        pixels_declividade_validos INTEGER,

    ADD COLUMN IF NOT EXISTS
        fonte_relevo VARCHAR(80);


COMMENT ON COLUMN
spatial.celula_prioridade.declividade_media_pct

IS
'Declividade média da célula em percentual, derivada do TOPODATA SN.';


COMMENT ON COLUMN
spatial.celula_prioridade.declividade_p90_pct

IS
'Percentil 90 da declividade dentro da célula, em percentual.';


COMMENT ON COLUMN
spatial.celula_prioridade.score_declividade

IS
'Score de sensibilidade relativa do relevo, 0 a 100. Não representa risco de erosão calculado nem aptidão jurídica para restauração.';


COMMENT ON COLUMN
spatial.celula_prioridade.fonte_relevo

IS
'Produto geomorfométrico utilizado para cálculo da declividade.';


SELECT

    COUNT(*) AS celulas,


    ROUND(
        MIN(
            declividade_media_pct
        ),
        2
    ) AS media_min,


    ROUND(
        AVG(
            declividade_media_pct
        ),
        2
    ) AS media_geral,


    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY declividade_media_pct
        )::NUMERIC,
        2
    ) AS mediana_media,


    ROUND(
        PERCENTILE_CONT(0.90)
        WITHIN GROUP (
            ORDER BY declividade_media_pct
        )::NUMERIC,
        2
    ) AS p90_das_medias,


    ROUND(
        MAX(
            declividade_media_pct
        ),
        2
    ) AS media_max,


    ROUND(
        AVG(
            declividade_p90_pct
        ),
        2
    ) AS p90_medio

FROM spatial.celula_prioridade

WHERE
    declividade_media_pct
    IS NOT NULL;