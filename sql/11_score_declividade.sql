CREATE OR REPLACE FUNCTION
analytics.score_declividade_pct(
    valor NUMERIC
)

RETURNS NUMERIC

LANGUAGE plpgsql

IMMUTABLE

AS $$

BEGIN

    IF valor IS NULL THEN
        RETURN NULL;


    ELSIF valor <= 0 THEN
        RETURN 0;


    ELSIF valor <= 3 THEN

        RETURN
            valor
            /
            3.0
            *
            10;


    ELSIF valor <= 8 THEN

        RETURN
            10
            +
            (
                (valor - 3)
                /
                5.0
            )
            *
            20;


    ELSIF valor <= 20 THEN

        RETURN
            30
            +
            (
                (valor - 8)
                /
                12.0
            )
            *
            30;


    ELSIF valor <= 45 THEN

        RETURN
            60
            +
            (
                (valor - 20)
                /
                25.0
            )
            *
            25;


    ELSIF valor <= 75 THEN

        RETURN
            85
            +
            (
                (valor - 45)
                /
                30.0
            )
            *
            15;


    ELSE

        RETURN 100;

    END IF;

END;

$$;


UPDATE spatial.celula_prioridade

SET score_declividade =

    ROUND(

        (

            0.65
            *
            analytics.score_declividade_pct(
                declividade_media_pct
            )

            +

            0.35
            *
            analytics.score_declividade_pct(
                declividade_p90_pct
            )

        ),

        2
    )

WHERE

    declividade_media_pct IS NOT NULL

    AND declividade_p90_pct IS NOT NULL;


SELECT

    MIN(score_declividade)
        AS minimo,

    ROUND(
        AVG(score_declividade),
        2
    ) AS media,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY score_declividade
        )::NUMERIC,
        2
    ) AS mediana,

    MAX(score_declividade)
        AS maximo

FROM spatial.celula_prioridade

WHERE
    score_declividade
    IS NOT NULL;


SELECT

    m.nome_municipio,

    c.id_celula,

    ROUND(
        c.declividade_media_pct,
        1
    ) AS declividade_media,

    ROUND(
        c.declividade_p90_pct,
        1
    ) AS declividade_p90,

    ROUND(
        c.declividade_max_pct,
        1
    ) AS declividade_max,

    ROUND(
        c.score_declividade,
        1
    ) AS score_relevo,

    c.pixels_declividade_validos

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m

    ON m.codigo_ibge =
       c.codigo_ibge

WHERE
    c.score_declividade
    IS NOT NULL

ORDER BY
    c.score_declividade DESC

LIMIT 50;


CREATE OR REPLACE VIEW
spatial.vw_validacao_declividade AS

SELECT

    c.id_celula,

    c.codigo_ibge,

    m.nome_municipio,

    i.ipa,

    c.distancia_drenagem_m,

    c.score_hidrologia,

    c.pct_uso_elegivel,

    c.score_elegibilidade,

    c.vegetacao_entorno_pct,

    c.score_conectividade,

    c.declividade_media_pct,

    c.declividade_p90_pct,

    c.score_declividade,

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
        'ipa_v1.0_2024'


WHERE
    c.score_declividade
    IS NOT NULL;


SELECT

    COUNT(*) AS processadas,

    COUNT(*)
    FILTER (
        WHERE declividade_media_pct >= 0
    ) AS media_valida,

    COUNT(*)
    FILTER (
        WHERE declividade_p90_pct
              >= declividade_media_pct
    ) AS p90_coerente,

    COUNT(*)
    FILTER (
        WHERE score_declividade
              BETWEEN 0 AND 100
    ) AS score_valido,

    COUNT(*)
    FILTER (
        WHERE pixels_declividade_validos = 0
    ) AS sem_pixels

FROM spatial.celula_prioridade

WHERE
    fonte_relevo =
    'TOPODATA_SN_INPE';


SELECT

    m.nome_municipio,

    c.id_celula,

    ROUND(
        c.area_ha,
        2
    ) AS area_ha,

    ROUND(
        c.score_hidrologia,
        1
    ) AS h,

    ROUND(
        c.score_elegibilidade,
        1
    ) AS e,

    ROUND(
        c.score_conectividade,
        1
    ) AS c,

    ROUND(
        c.score_declividade,
        1
    ) AS s,

    c.uso_predominante

FROM spatial.celula_prioridade c

JOIN core.dim_municipio m

    ON m.codigo_ibge =
       c.codigo_ibge

WHERE

    c.score_hidrologia
        IS NOT NULL

    AND c.score_elegibilidade
        IS NOT NULL

    AND c.score_conectividade
        IS NOT NULL

    AND c.score_declividade
        IS NOT NULL

    AND c.area_ha >= 1

    AND c.pixels_validos >= 10

ORDER BY

    c.score_hidrologia DESC,

    c.score_conectividade DESC,

    c.score_elegibilidade DESC;