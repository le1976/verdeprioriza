-- ============================================================
-- VERDEPRIORIZA
-- MÓDULO 9G
-- VALIDAÇÃO E SENSIBILIDADE DOS LIMIARES
-- DAS ÁREAS PRIORITÁRIAS
--
-- Referência ambiental: 2024
--
-- Objetivo:
-- Comparar diferentes limiares de Prioridade Integrada
-- para formação de áreas prioritárias contínuas.
--
-- Cenários:
--   57,50  ~ cenário inclusivo / próximo ao P75
--   58,50  ~ cenário seletivo / próximo ao P90
--   59,00  ~ cenário muito seletivo / próximo ao P95
--
-- IMPORTANTE:
-- Os valores representam critérios analíticos de triagem.
-- Não significam obrigação de restauração, passivo ambiental,
-- APP degradada ou disponibilidade jurídica da área.
-- ============================================================



-- ============================================================
-- 0. LIMPEZA DA VERSÃO ANTERIOR
-- ============================================================

DROP VIEW IF EXISTS
spatial.vw_validacao_limiar_9g;


DROP TABLE IF EXISTS
spatial.area_prioritaria_teste_9g;



-- ============================================================
-- 1. TABELA DE RESULTADOS DOS CENÁRIOS
-- ============================================================

CREATE TABLE spatial.area_prioritaria_teste_9g (

    id_teste BIGSERIAL PRIMARY KEY,

    -- Limiar testado.
    -- NUMERIC é necessário porque agora usamos
    -- valores como 57,50 e 58,50.
    limiar NUMERIC(6,2) NOT NULL,

    codigo_ibge VARCHAR(7) NOT NULL,

    cluster_ref VARCHAR(150) NOT NULL,

    numero_celulas INTEGER,

    area_ha NUMERIC(14,4),

    prioridade_media NUMERIC(8,4),

    prioridade_min NUMERIC(8,4),

    prioridade_max NUMERIC(8,4),

    pct_estabilidade_alta NUMERIC(8,4),

    amplitude_ipl_media NUMERIC(8,4),

    status_area VARCHAR(40),

    robustez_area VARCHAR(20),

    geom GEOMETRY(
        MULTIPOLYGON,
        5880
    )

);



-- ============================================================
-- 2. ÍNDICES
-- ============================================================

CREATE INDEX
idx_area_teste_9g_geom

ON spatial.area_prioritaria_teste_9g

USING GIST (geom);



CREATE INDEX
idx_area_teste_9g_limiar

ON spatial.area_prioritaria_teste_9g (
    limiar
);



CREATE INDEX
idx_area_teste_9g_municipio

ON spatial.area_prioritaria_teste_9g (
    codigo_ibge
);



-- ============================================================
-- 3. PROCESSAMENTO DOS TRÊS CENÁRIOS
-- ============================================================

WITH


-- ============================================================
-- 3.1 LIMIARES
-- ============================================================

limiares(limiar) AS (

    VALUES

        (55.84::NUMERIC),
        (58.44::NUMERIC),
        (61.46::NUMERIC)

),



-- ============================================================
-- 3.2 CÉLULAS CANDIDATAS
--
-- Uma mesma célula pode participar de mais de um cenário.
--
-- Exemplo:
--
-- PI = 59,30
--
-- entra em:
-- 57,50
-- 58,50
-- 59,00
--
-- ============================================================

candidatas AS (

    SELECT

        l.limiar,

        c.id_celula,

        c.codigo_ibge,

        c.area_ha,

        c.prioridade_integrada,

        c.estabilidade_ipl,

        c.amplitude_ipl,

        c.geom


    FROM spatial.celula_prioridade c


    CROSS JOIN limiares l


    WHERE

        c.prioridade_integrada
            IS NOT NULL


        AND c.prioridade_integrada
            >= l.limiar


        AND c.estabilidade_ipl
            IN (
                'Alta',
                'Media'
            )


        AND c.versao_ipl =
            'ipl_v1.0_2024'


        AND c.area_ha >= 1


        AND c.pixels_validos >= 10

),



-- ============================================================
-- 3.3 CLUSTERIZAÇÃO
--
-- Agrupa células territorialmente contíguas.
--
-- eps = 0,5 m
--
-- Essa pequena tolerância serve apenas para evitar problemas
-- decorrentes de diferenças numéricas mínimas entre geometrias.
--
-- minpoints = 1
--
-- Permite manter também células isoladas.
-- ============================================================

clusterizado AS (

    SELECT

        c.*,


        ST_ClusterDBSCAN(

            c.geom,

            eps => 0.5,

            minpoints => 1

        ) OVER (

            PARTITION BY

                c.limiar,

                c.codigo_ibge


            ORDER BY

                c.id_celula

        ) AS cluster_id


    FROM candidatas c

),



-- ============================================================
-- 3.4 DISSOLVER CÉLULAS DO MESMO CLUSTER
-- ============================================================

dissolvido AS (

    SELECT

        limiar,

        codigo_ibge,

        cluster_id,


        ST_UnaryUnion(

            ST_Collect(
                geom
            )

        ) AS geom


    FROM clusterizado


    WHERE
        cluster_id IS NOT NULL


    GROUP BY

        limiar,

        codigo_ibge,

        cluster_id

),



-- ============================================================
-- 3.5 SEPARAR COMPONENTES POLIGONAIS
--
-- Essa etapa é importante porque duas células podem pertencer
-- ao mesmo cluster por tocarem apenas um vértice.
--
-- ST_Dump separa componentes poligonais independentes.
--
-- ATENÇÃO:
-- Quando a geometria já é um único Polygon,
-- (dumped).path[1] pode retornar NULL.
--
-- Por isso usamos:
--
-- COALESCE((dumped).path[1], 1)
--
-- ============================================================

componentes AS (

    SELECT

        limiar,

        codigo_ibge,

        cluster_id,


        COALESCE(

            (
                dumped
            ).path[1],

            1

        ) AS componente_id,


        (
            dumped
        ).geom AS geom


    FROM (

        SELECT

            limiar,

            codigo_ibge,

            cluster_id,


            ST_Dump(

                ST_CollectionExtract(

                    geom,

                    3

                )

            ) AS dumped


        FROM dissolvido

    ) x

),



-- ============================================================
-- 3.6 CRIAR IDENTIFICADOR ÚNICO DA ÁREA
--
-- CONCAT é utilizado em vez do operador ||
-- para tornar a construção mais defensiva.
-- ============================================================

areas AS (

    SELECT

        limiar,

        codigo_ibge,

        cluster_id,

        componente_id,


        CONCAT(

            limiar::TEXT,

            ':',

            codigo_ibge,

            ':',

            cluster_id::TEXT,

            ':',

            componente_id::TEXT

        ) AS cluster_ref,


        ST_Multi(

            geom

        )::geometry(

            MULTIPOLYGON,

            5880

        ) AS geom


    FROM componentes


    WHERE

        geom IS NOT NULL


        AND NOT ST_IsEmpty(
            geom
        )

),



-- ============================================================
-- 3.7 RELACIONAR CADA CÉLULA AO COMPONENTE FINAL
--
-- PointOnSurface garante um ponto localizado dentro
-- da própria célula.
--
-- ST_Covers identifica qual componente contém esse ponto.
-- ============================================================

relacao AS (

    SELECT

        a.limiar,

        a.codigo_ibge,

        a.cluster_ref,

        a.geom,


        c.id_celula,

        c.area_ha,

        c.prioridade_integrada,

        c.estabilidade_ipl,

        c.amplitude_ipl


    FROM areas a


    JOIN clusterizado c

        ON c.limiar =
           a.limiar


        AND c.codigo_ibge =
            a.codigo_ibge


        AND c.cluster_id =
            a.cluster_id


    WHERE

        ST_Covers(

            a.geom,

            ST_PointOnSurface(
                c.geom
            )

        )

),



-- ============================================================
-- 3.8 CALCULAR MÉTRICAS DAS ÁREAS
-- ============================================================

metricas AS (

    SELECT

        limiar,

        codigo_ibge,

        cluster_ref,

        geom,


        -- ----------------------------------------------------
        -- Número de células
        -- ----------------------------------------------------

        COUNT(*) AS
            numero_celulas,


        -- ----------------------------------------------------
        -- Área total
        -- ----------------------------------------------------

        SUM(
            area_ha
        ) AS
            area_ha,


        -- ----------------------------------------------------
        -- Prioridade Integrada média ponderada pela área
        -- ----------------------------------------------------

        SUM(

            prioridade_integrada
            *
            area_ha

        )

        /

        NULLIF(

            SUM(
                area_ha
            ),

            0

        ) AS
            prioridade_media,


        -- ----------------------------------------------------
        -- Mínimo e máximo
        -- ----------------------------------------------------

        MIN(
            prioridade_integrada
        ) AS
            prioridade_min,


        MAX(
            prioridade_integrada
        ) AS
            prioridade_max,


        -- ----------------------------------------------------
        -- Percentual de células com estabilidade ALTA
        -- ----------------------------------------------------

        COUNT(*)

        FILTER (

            WHERE

                estabilidade_ipl =
                'Alta'

        )

        *

        100.0

        /

        NULLIF(

            COUNT(*),

            0

        ) AS
            pct_estabilidade_alta,


        -- ----------------------------------------------------
        -- Amplitude média do IPL ponderada pela área
        -- ----------------------------------------------------

        SUM(

            amplitude_ipl
            *
            area_ha

        )

        /

        NULLIF(

            SUM(
                area_ha
            ),

            0

        ) AS
            amplitude_ipl_media


    FROM relacao


    GROUP BY

        limiar,

        codigo_ibge,

        cluster_ref,

        geom

)



-- ============================================================
-- 3.9 INSERIR RESULTADOS
-- ============================================================

INSERT INTO spatial.area_prioritaria_teste_9g (

    limiar,

    codigo_ibge,

    cluster_ref,

    numero_celulas,

    area_ha,

    prioridade_media,

    prioridade_min,

    prioridade_max,

    pct_estabilidade_alta,

    amplitude_ipl_media,

    status_area,

    robustez_area,

    geom

)


SELECT

    limiar,

    codigo_ibge,

    cluster_ref,

    numero_celulas,

    area_ha,

    prioridade_media,

    prioridade_min,

    prioridade_max,

    pct_estabilidade_alta,

    amplitude_ipl_media,


    -- ========================================================
    -- STATUS DA ÁREA
    --
    -- Mantemos núcleos pequenos para não perder informação.
    -- ========================================================

    CASE

        WHEN

            numero_celulas >= 2

            AND

            area_ha >= 10

        THEN

            'Área prioritária contínua'


        ELSE

            'Núcleo isolado'

    END AS status_area,


    -- ========================================================
    -- ROBUSTEZ
    -- ========================================================

    CASE

        WHEN

            pct_estabilidade_alta >= 70

            AND

            amplitude_ipl_media <= 5

        THEN

            'Alta'


        WHEN

            pct_estabilidade_alta >= 40

            AND

            amplitude_ipl_media <= 10

        THEN

            'Media'


        ELSE

            'Baixa'

    END AS robustez_area,


    geom


FROM metricas;



-- ============================================================
-- 4. VIEW PARA QGIS
-- ============================================================

CREATE OR REPLACE VIEW
spatial.vw_validacao_limiar_9g AS


SELECT

    a.id_teste,

    a.limiar,

    a.codigo_ibge,

    m.nome_municipio,

    a.cluster_ref,

    a.numero_celulas,

    a.area_ha,

    a.prioridade_media,

    a.prioridade_min,

    a.prioridade_max,

    a.pct_estabilidade_alta,

    a.amplitude_ipl_media,

    a.status_area,

    a.robustez_area,

    a.geom


FROM spatial.area_prioritaria_teste_9g a


JOIN core.dim_municipio m

    ON m.codigo_ibge =
       a.codigo_ibge;



-- ============================================================
-- 5. VALIDAÇÃO 1
-- QUANTIDADE DE REGISTROS POR LIMIAR
-- ============================================================

SELECT

    limiar,

    COUNT(*) AS registros,

    ROUND(

        SUM(
            area_ha
        ),

        2

    ) AS area_ha


FROM spatial.area_prioritaria_teste_9g


GROUP BY
    limiar


ORDER BY
    limiar;



-- ============================================================
-- 6. VALIDAÇÃO 2
-- CLUSTER_REF NULO
--
-- Esperado:
-- sem_cluster_ref = 0
-- ============================================================

SELECT

    COUNT(*) AS total,

    COUNT(
        cluster_ref
    ) AS com_cluster_ref,

    COUNT(*)
    -
    COUNT(
        cluster_ref
    ) AS sem_cluster_ref


FROM spatial.area_prioritaria_teste_9g;



-- ============================================================
-- 7. VALIDAÇÃO 3
-- CLUSTER_REF DUPLICADO
--
-- Esperado:
-- 0 registros
-- ============================================================

SELECT

    limiar,

    cluster_ref,

    COUNT(*) AS quantidade


FROM spatial.area_prioritaria_teste_9g


GROUP BY

    limiar,

    cluster_ref


HAVING
    COUNT(*) > 1;



-- ============================================================
-- 8. RESUMO PRINCIPAL DOS CENÁRIOS
-- ============================================================

SELECT

    limiar,


    COUNT(*) AS
        agrupamentos,


    COUNT(*)

    FILTER (

        WHERE

            status_area =
            'Área prioritária contínua'

    ) AS
        areas_continuas,


    COUNT(*)

    FILTER (

        WHERE

            status_area =
            'Núcleo isolado'

    ) AS
        nucleos_isolados,


    ROUND(

        SUM(
            area_ha
        ),

        1

    ) AS
        area_total_ha,


    ROUND(

        AVG(
            area_ha
        ),

        1

    ) AS
        area_media_ha,


    ROUND(

        PERCENTILE_CONT(0.50)

        WITHIN GROUP (

            ORDER BY
                area_ha

        )::NUMERIC,

        1

    ) AS
        area_mediana_ha,


    ROUND(

        PERCENTILE_CONT(0.90)

        WITHIN GROUP (

            ORDER BY
                area_ha

        )::NUMERIC,

        1

    ) AS
        area_p90_ha,


    ROUND(

        MAX(
            area_ha
        ),

        1

    ) AS
        maior_area_ha,


    ROUND(

        SUM(

            prioridade_media
            *
            area_ha

        )

        /

        NULLIF(

            SUM(
                area_ha
            ),

            0

        ),

        2

    ) AS
        prioridade_media_ponderada


FROM spatial.area_prioritaria_teste_9g


GROUP BY
    limiar


ORDER BY
    limiar;



-- ============================================================
-- 9. PERCENTUAL DE NÚCLEOS ISOLADOS
-- ============================================================

SELECT

    limiar,


    COUNT(*) AS
        total,


    COUNT(*)

    FILTER (

        WHERE

            status_area =
            'Núcleo isolado'

    ) AS
        isolados,


    ROUND(

        COUNT(*)

        FILTER (

            WHERE

                status_area =
                'Núcleo isolado'

        )

        *

        100.0

        /

        NULLIF(

            COUNT(*),

            0

        ),

        2

    ) AS
        pct_isolados


FROM spatial.area_prioritaria_teste_9g


GROUP BY
    limiar


ORDER BY
    limiar;



-- ============================================================
-- 10. ÍNDICE SIMPLES DE FRAGMENTAÇÃO
--
-- Número de agrupamentos para cada 1.000 ha selecionados.
-- ============================================================

SELECT

    limiar,


    COUNT(*) AS
        agrupamentos,


    ROUND(

        SUM(
            area_ha
        ),

        1

    ) AS
        area_ha,


    ROUND(

        COUNT(*)

        /

        NULLIF(

            SUM(
                area_ha
            ),

            0

        )

        *

        1000,

        2

    ) AS
        agrupamentos_por_1000_ha


FROM spatial.area_prioritaria_teste_9g


GROUP BY
    limiar


ORDER BY
    limiar;



-- ============================================================
-- 11. ROBUSTEZ POR LIMIAR
-- ============================================================

SELECT

    limiar,

    robustez_area,


    COUNT(*) AS
        areas,


    ROUND(

        SUM(
            area_ha
        ),

        1

    ) AS
        area_ha,


    ROUND(

        SUM(
            area_ha
        )

        /

        NULLIF(

            SUM(

                SUM(
                    area_ha
                )

            ) OVER (

                PARTITION BY
                    limiar

            ),

            0

        )

        *

        100,

        2

    ) AS
        pct_area


FROM spatial.area_prioritaria_teste_9g


GROUP BY

    limiar,

    robustez_area


ORDER BY

    limiar,

    area_ha DESC;



-- ============================================================
-- 12. APENAS ÁREAS CONTÍNUAS
-- ============================================================

SELECT

    limiar,


    COUNT(*) AS
        areas_continuas,


    ROUND(

        SUM(
            area_ha
        ),

        1

    ) AS
        area_total_ha,


    ROUND(

        PERCENTILE_CONT(0.50)

        WITHIN GROUP (

            ORDER BY
                area_ha

        )::NUMERIC,

        1

    ) AS
        mediana_ha,


    ROUND(

        PERCENTILE_CONT(0.75)

        WITHIN GROUP (

            ORDER BY
                area_ha

        )::NUMERIC,

        1

    ) AS
        p75_ha,


    ROUND(

        PERCENTILE_CONT(0.90)

        WITHIN GROUP (

            ORDER BY
                area_ha

        )::NUMERIC,

        1

    ) AS
        p90_ha,


    ROUND(

        MAX(
            area_ha
        ),

        1

    ) AS
        maximo_ha


FROM spatial.area_prioritaria_teste_9g


WHERE

    status_area =
    'Área prioritária contínua'


GROUP BY
    limiar


ORDER BY
    limiar;



-- ============================================================
-- 13. MAIORES ÁREAS
-- ============================================================

SELECT

    limiar,

    codigo_ibge,

    cluster_ref,

    numero_celulas,


    ROUND(
        area_ha,
        1
    ) AS area_ha,


    ROUND(
        prioridade_media,
        2
    ) AS prioridade_media,


    robustez_area


FROM spatial.area_prioritaria_teste_9g


ORDER BY

    area_ha DESC


LIMIT 30;



-- ============================================================
-- 14. ÁREAS MENORES QUE 10 ha
-- ============================================================

SELECT

    limiar,

    COUNT(*) AS quantidade


FROM spatial.area_prioritaria_teste_9g


WHERE
    area_ha < 10


GROUP BY
    limiar


ORDER BY
    limiar;



-- ============================================================
-- 15. RESULTADOS POR MUNICÍPIO
-- ============================================================

SELECT

    a.limiar,

    m.nome_municipio,


    COUNT(*) AS
        agrupamentos,


    COUNT(*)

    FILTER (

        WHERE

            a.status_area =
            'Área prioritária contínua'

    ) AS
        areas_continuas,


    ROUND(

        SUM(
            a.area_ha
        ),

        1

    ) AS
        area_ha,


    ROUND(

        AVG(
            a.prioridade_media
        ),

        2

    ) AS
        prioridade_media


FROM spatial.area_prioritaria_teste_9g a


JOIN core.dim_municipio m

    ON m.codigo_ibge =
       a.codigo_ibge


GROUP BY

    a.limiar,

    m.nome_municipio


ORDER BY

    m.nome_municipio,

    a.limiar;



SELECT

    limiar,

    COUNT(*) AS
        agrupamentos,

    COUNT(*)
    FILTER (
        WHERE status_area =
        'Área prioritária contínua'
    ) AS
        areas_continuas,

    COUNT(*)
    FILTER (
        WHERE status_area =
        'Núcleo isolado'
    ) AS
        nucleos_isolados,


    ROUND(

        SUM(area_ha),

        1

    ) AS
        area_total_ha,


    ROUND(

        AVG(area_ha),

        1

    ) AS
        area_media_ha,


    ROUND(

        PERCENTILE_CONT(0.50)

        WITHIN GROUP (
            ORDER BY area_ha
        )::NUMERIC,

        1

    ) AS
        area_mediana_ha,


    ROUND(

        PERCENTILE_CONT(0.90)

        WITHIN GROUP (
            ORDER BY area_ha
        )::NUMERIC,

        1

    ) AS
        area_p90_ha,


    ROUND(

        MAX(area_ha),

        1

    ) AS
        maior_area_ha,


    ROUND(

        SUM(
            prioridade_media
            *
            area_ha
        )

        /

        NULLIF(
            SUM(area_ha),
            0
        ),

        2

    ) AS
        prioridade_media_ponderada


FROM spatial.area_prioritaria_teste_9g


GROUP BY
    limiar


ORDER BY
    limiar;



SELECT

    limiar,

    COUNT(*) AS
        total,


    COUNT(*)
    FILTER (
        WHERE status_area =
        'Núcleo isolado'
    ) AS
        isolados,


    ROUND(

        COUNT(*)
        FILTER (
            WHERE status_area =
            'Núcleo isolado'
        )

        *
        100.0

        /

        COUNT(*),

        2

    ) AS
        pct_isolados


FROM spatial.area_prioritaria_teste_9g


GROUP BY
    limiar


ORDER BY
    limiar;



SELECT

    limiar,

    COUNT(*) AS
        agrupamentos,


    ROUND(
        SUM(area_ha),
        1
    ) AS
        area_ha,


    ROUND(

        COUNT(*)
        /
        NULLIF(
            SUM(area_ha),
            0
        )
        *
        1000,

        2

    ) AS
        agrupamentos_por_1000_ha


FROM spatial.area_prioritaria_teste_9g


GROUP BY
    limiar


ORDER BY
    limiar;



SELECT

    limiar,

    robustez_area,

    COUNT(*) AS
        areas,

    ROUND(

        SUM(area_ha),

        1

    ) AS
        area_ha,


    ROUND(

        SUM(area_ha)

        /
        SUM(
            SUM(area_ha)
        ) OVER (
            PARTITION BY limiar
        )

        *
        100,

        2

    ) AS
        pct_area


FROM spatial.area_prioritaria_teste_9g


GROUP BY

    limiar,

    robustez_area


ORDER BY

    limiar,

    area_ha DESC;



SELECT

    limiar,

    COUNT(*) AS
        areas_continuas,


    ROUND(
        SUM(area_ha),
        1
    ) AS
        area_total_ha,


    ROUND(

        PERCENTILE_CONT(0.50)

        WITHIN GROUP (
            ORDER BY area_ha
        )::NUMERIC,

        1

    ) AS
        mediana_ha,


    ROUND(

        PERCENTILE_CONT(0.75)

        WITHIN GROUP (
            ORDER BY area_ha
        )::NUMERIC,

        1

    ) AS
        p75_ha,


    ROUND(

        PERCENTILE_CONT(0.90)

        WITHIN GROUP (
            ORDER BY area_ha
        )::NUMERIC,

        1

    ) AS
        p90_ha,


    ROUND(
        MAX(area_ha),
        1
    ) AS
        maximo_ha


FROM spatial.area_prioritaria_teste_9g


WHERE
    status_area =
    'Área prioritária contínua'


GROUP BY
    limiar


ORDER BY
    limiar;



SELECT

    limiar,

    codigo_ibge,

    cluster_ref,

    numero_celulas,

    ROUND(
        area_ha,
        1
    ) AS area_ha,

    ROUND(
        prioridade_media,
        1
    ) AS prioridade_media

FROM spatial.area_prioritaria_teste_9g


ORDER BY
    area_ha DESC


LIMIT 30;



SELECT

    limiar,

    COUNT(*) AS
        quantidade

FROM spatial.area_prioritaria_teste_9g


WHERE
    area_ha < 10


GROUP BY
    limiar


ORDER BY
    limiar;



SELECT
    limiar,
    COUNT(*) AS registros,
    ROUND(SUM(area_ha), 2) AS area_ha
FROM spatial.area_prioritaria_teste_9g
GROUP BY limiar
ORDER BY limiar;




SELECT

    COUNT(*) AS total_celulas,

    COUNT(prioridade_integrada)
        AS com_prioridade_integrada,

    ROUND(
        MIN(prioridade_integrada),
        2
    ) AS pi_min,

    ROUND(
        MAX(prioridade_integrada),
        2
    ) AS pi_max,


    COUNT(*) FILTER (
        WHERE prioridade_integrada >= 75
    ) AS pi_75,


    COUNT(*) FILTER (
        WHERE prioridade_integrada >= 80
    ) AS pi_80,


    COUNT(*) FILTER (
        WHERE prioridade_integrada >= 85
    ) AS pi_85,


    COUNT(*) FILTER (
        WHERE estabilidade_ipl IN ('Alta', 'Media')
    ) AS estabilidade_ok,


    COUNT(*) FILTER (
        WHERE versao_ipl = 'ipl_v1.0_2024'
    ) AS versao_ok,


    COUNT(*) FILTER (
        WHERE
            prioridade_integrada >= 75
            AND estabilidade_ipl IN ('Alta', 'Media')
            AND versao_ipl = 'ipl_v1.0_2024'
            AND area_ha >= 1
            AND pixels_validos >= 10
    ) AS candidatas_9g

FROM spatial.celula_prioridade;




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

    AND pixels_validos >= 10;



SELECT
    COUNT(*) AS total,
    COUNT(cluster_ref) AS com_cluster_ref,
    COUNT(*) - COUNT(cluster_ref) AS sem_cluster_ref
FROM spatial.area_prioritaria_teste_9g;



SELECT

    ROUND(
        MIN(pct_estabilidade_alta),
        2
    ) AS min_estabilidade,

    ROUND(
        AVG(pct_estabilidade_alta),
        2
    ) AS media_estabilidade,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY pct_estabilidade_alta
        )::NUMERIC,
        2
    ) AS mediana_estabilidade,

    ROUND(
        PERCENTILE_CONT(0.75)
        WITHIN GROUP (
            ORDER BY pct_estabilidade_alta
        )::NUMERIC,
        2
    ) AS p75_estabilidade,

    ROUND(
        MAX(pct_estabilidade_alta),
        2
    ) AS max_estabilidade,


    ROUND(
        MIN(amplitude_ipl_media),
        2
    ) AS min_amplitude,

    ROUND(
        AVG(amplitude_ipl_media),
        2
    ) AS media_amplitude,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY amplitude_ipl_media
        )::NUMERIC,
        2
    ) AS mediana_amplitude,

    ROUND(
        PERCENTILE_CONT(0.75)
        WITHIN GROUP (
            ORDER BY amplitude_ipl_media
        )::NUMERIC,
        2
    ) AS p75_amplitude,

    ROUND(
        MAX(amplitude_ipl_media),
        2
    ) AS max_amplitude

FROM spatial.area_prioritaria_teste_9g

WHERE limiar = 57.50;




SELECT

    ROUND(
        PERCENTILE_CONT(0.25)
        WITHIN GROUP (
            ORDER BY amplitude_ipl_media
        )::NUMERIC,
        2
    ) AS p25_amplitude,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY amplitude_ipl_media
        )::NUMERIC,
        2
    ) AS mediana_amplitude,

    ROUND(
        PERCENTILE_CONT(0.75)
        WITHIN GROUP (
            ORDER BY amplitude_ipl_media
        )::NUMERIC,
        2
    ) AS p75_amplitude

FROM spatial.area_prioritaria_teste_9g

WHERE limiar = 57.50;



UPDATE spatial.area_prioritaria_teste_9g

SET robustez_area =

    CASE

        WHEN amplitude_ipl_media <= 8.23
            THEN 'Alta'

        WHEN amplitude_ipl_media <= 9.18
            THEN 'Media'

        ELSE
            'Baixa'

    END;




SELECT

    limiar,

    robustez_area,

    COUNT(*) AS areas,

    ROUND(
        SUM(area_ha),
        1
    ) AS area_ha

FROM spatial.area_prioritaria_teste_9g

GROUP BY
    limiar,
    robustez_area

ORDER BY
    limiar,
    robustez_area;


SELECT

    limiar,

    COUNT(*) AS registros,

    ROUND(
        SUM(area_ha),
        2
    ) AS area_ha

FROM spatial.area_prioritaria_teste_9g

GROUP BY limiar

ORDER BY limiar;



SELECT

    COUNT(*) AS areas,

    ROUND(
        MIN(amplitude_ipl_media),
        2
    ) AS minimo,

    ROUND(
        PERCENTILE_CONT(0.25)
        WITHIN GROUP (
            ORDER BY amplitude_ipl_media
        )::NUMERIC,
        2
    ) AS p25,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY amplitude_ipl_media
        )::NUMERIC,
        2
    ) AS mediana,

    ROUND(
        PERCENTILE_CONT(0.75)
        WITHIN GROUP (
            ORDER BY amplitude_ipl_media
        )::NUMERIC,
        2
    ) AS p75,

    ROUND(
        MAX(amplitude_ipl_media),
        2
    ) AS maximo

FROM spatial.area_prioritaria_teste_9g

WHERE limiar = 55.84;



UPDATE spatial.area_prioritaria_teste_9g

SET robustez_area =

    CASE

        WHEN amplitude_ipl_media <= 7.04
            THEN 'Alta'

        WHEN amplitude_ipl_media <= 9.18
            THEN 'Media'

        ELSE
            'Baixa'

    END;




SELECT

    limiar,

    robustez_area,

    COUNT(*) AS areas,

    ROUND(
        SUM(area_ha),
        1
    ) AS area_ha

FROM spatial.area_prioritaria_teste_9g

GROUP BY
    limiar,
    robustez_area

ORDER BY
    limiar,
    robustez_area;