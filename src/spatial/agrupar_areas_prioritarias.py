import os

from pathlib import Path

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL
from sqlalchemy import text


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]


ANO_REFERENCIA = 2024

VERSAO_IPA = "ipa_v1.0_2024"

VERSAO_IPL = "ipl_v1.0_2024"

VERSAO_AREAS = "areas_v1.0_2024"


# ============================================================
# CRITÉRIOS
# ============================================================

PRIORIDADE_MINIMA = 80


# Pequena tolerância para células que deveriam
# ser contíguas.

EPS_CLUSTER_M = 0.5


# Para ser considerada uma área contínua e não
# apenas um núcleo isolado.

MIN_CELULAS_AREA = 2

MIN_AREA_HA = 10


# ------------------------------------------------------------
# PRIMEIRO TESTE
# ------------------------------------------------------------

LIMITE_MUNICIPIOS = 20


# ============================================================
# BANCO
# ============================================================

load_dotenv(
    ROOT_DIR / ".env"
)


url = URL.create(

    drivername="postgresql+psycopg",

    username=os.getenv("DB_USER"),

    password=os.getenv("DB_PASSWORD"),

    host=os.getenv("DB_HOST"),

    port=int(
        os.getenv(
            "DB_PORT",
            5432,
        )
    ),

    database=os.getenv("DB_NAME"),
)


engine = create_engine(
    url,
    pool_pre_ping=True,
)

# ============================================================
# PROCESSAMENTO SQL
# ============================================================

sql_processamento = f"""

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


-- ============================================================
-- 2. CÉLULAS CANDIDATAS
-- ============================================================

DROP TABLE IF EXISTS
staging.celula_cluster_9f;


CREATE TABLE staging.celula_cluster_9f AS

SELECT

    c.id_celula,

    c.codigo_ibge,

    c.area_ha,

    c.prioridade_local,

    c.prioridade_integrada,

    c.score_hidrologia,

    c.score_conectividade,

    c.score_declividade,

    c.score_elegibilidade,

    c.pct_uso_elegivel,

    c.pct_vegetacao_natural,

    c.vegetacao_entorno_pct,

    c.distancia_drenagem_m,

    c.declividade_media_pct,

    c.uso_predominante,

    c.estabilidade_ipl,

    c.amplitude_ipl,

    c.geom,


    ST_ClusterDBSCAN(

        c.geom,

        eps => {EPS_CLUSTER_M},

        minpoints => 1

    ) OVER (

        PARTITION BY
            c.codigo_ibge

        ORDER BY
            c.id_celula

    ) AS cluster_id


FROM spatial.celula_prioridade c


JOIN staging.municipio_9f a

    ON a.codigo_ibge =
       c.codigo_ibge


WHERE

    c.prioridade_integrada
        >= {PRIORIDADE_MINIMA}

    AND c.estabilidade_ipl
        IN ('Alta', 'Media')

    AND c.versao_ipl =
        '{VERSAO_IPL}'

    AND c.area_ha >= 1

    AND c.pixels_validos >= 10;


CREATE INDEX

ON staging.celula_cluster_9f

USING GIST (geom);

"""

# ============================================================
# 3. DISSOLVER AS CÉLULAS DE CADA CLUSTER
# ============================================================

sql_processamento += """

DROP TABLE IF EXISTS
staging.area_geom_9f;


CREATE TABLE staging.area_geom_9f AS


WITH dissolvido AS (

    SELECT

        codigo_ibge,

        cluster_id,

        ST_UnaryUnion(

            ST_Collect(
                geom
            )

        ) AS geom


    FROM staging.celula_cluster_9f


    GROUP BY

        codigo_ibge,

        cluster_id

),


partes AS (

    SELECT

        codigo_ibge,

        cluster_id,

        (
            dumped
        ).path[1]
            AS componente_id,

        (
            dumped
        ).geom
            AS geom


    FROM (

        SELECT

            codigo_ibge,

            cluster_id,

            ST_Dump(

                ST_CollectionExtract(
                    geom,
                    3
                )

            ) AS dumped


        FROM dissolvido

    ) q

)


SELECT

    codigo_ibge,

    cluster_id,

    componente_id,

    (
        codigo_ibge
        ||
        ':'
        ||
        cluster_id::TEXT
        ||
        ':'
        ||
        componente_id::TEXT
    ) AS cluster_ref,

    ST_Multi(
        geom
    )::geometry(
        MULTIPOLYGON,
        5880
    ) AS geom


FROM partes


WHERE

    NOT ST_IsEmpty(
        geom
    );


CREATE INDEX

ON staging.area_geom_9f

USING GIST (geom);

"""


# ============================================================
# 4. RELACIONAR AS CÉLULAS À ÁREA FINAL
# ============================================================

sql_processamento += """

DROP TABLE IF EXISTS
staging.area_celula_9f;


CREATE TABLE staging.area_celula_9f AS

SELECT

    a.codigo_ibge,

    a.cluster_id,

    a.componente_id,

    a.cluster_ref,

    c.id_celula


FROM staging.area_geom_9f a


JOIN staging.celula_cluster_9f c

    ON c.codigo_ibge =
       a.codigo_ibge

    AND c.cluster_id =
        a.cluster_id


WHERE

    ST_Covers(

        a.geom,

        ST_PointOnSurface(
            c.geom
        )

    );


CREATE INDEX

ON staging.area_celula_9f(
    id_celula
);

"""

sql_processamento += f"""

-- ============================================================
-- 5. MÉTRICAS DAS ÁREAS
-- ============================================================

DROP TABLE IF EXISTS
staging.area_resultado_9f;


CREATE TABLE staging.area_resultado_9f AS


WITH metricas AS (

    SELECT

        a.codigo_ibge,

        a.cluster_ref,

        a.geom,


        COUNT(
            c.id_celula
        ) AS numero_celulas,


        SUM(
            c.area_ha
        ) AS area_grade_ha,


        ST_Area(
            a.geom
        )
        /
        10000.0
            AS area_geometrica_ha,


        SUM(

            c.area_ha
            *
            c.pct_uso_elegivel
            /
            100.0

        ) AS area_uso_candidato_ha,


        SUM(

            c.area_ha
            *
            c.pct_vegetacao_natural
            /
            100.0

        ) AS vegetacao_interna_estimada_ha,


        -- ================================================
        -- IPL
        -- ================================================

        SUM(

            c.prioridade_local
            *
            c.area_ha

        )

        /

        NULLIF(
            SUM(c.area_ha),
            0
        )
            AS ipl_medio,


        MIN(
            c.prioridade_local
        ) AS ipl_min,


        MAX(
            c.prioridade_local
        ) AS ipl_max,


        -- ================================================
        -- PRIORIDADE INTEGRADA
        -- ================================================

        SUM(

            c.prioridade_integrada
            *
            c.area_ha

        )

        /

        NULLIF(
            SUM(c.area_ha),
            0
        )
            AS prioridade_integrada_media,


        MIN(
            c.prioridade_integrada
        ) AS prioridade_integrada_min,


        MAX(
            c.prioridade_integrada
        ) AS prioridade_integrada_max,


        -- ================================================
        -- COMPONENTES
        -- ================================================

        SUM(
            c.score_hidrologia
            *
            c.area_ha
        )

        /
        NULLIF(
            SUM(c.area_ha),
            0
        )
            AS score_hidrologia_medio,


        SUM(
            c.score_conectividade
            *
            c.area_ha
        )

        /
        NULLIF(
            SUM(c.area_ha),
            0
        )
            AS score_conectividade_medio,


        SUM(
            c.score_declividade
            *
            c.area_ha
        )

        /
        NULLIF(
            SUM(c.area_ha),
            0
        )
            AS score_declividade_medio,


        SUM(
            c.score_elegibilidade
            *
            c.area_ha
        )

        /
        NULLIF(
            SUM(c.area_ha),
            0
        )
            AS score_elegibilidade_medio,


        -- ================================================
        -- CARACTERIZAÇÃO
        -- ================================================

        SUM(
            c.distancia_drenagem_m
            *
            c.area_ha
        )

        /
        NULLIF(
            SUM(c.area_ha),
            0
        )
            AS distancia_drenagem_media_m,


        MIN(
            c.distancia_drenagem_m
        )
            AS distancia_drenagem_min_m,


        SUM(
            c.vegetacao_entorno_pct
            *
            c.area_ha
        )

        /
        NULLIF(
            SUM(c.area_ha),
            0
        )
            AS vegetacao_entorno_media_pct,


        SUM(
            c.declividade_media_pct
            *
            c.area_ha
        )

        /
        NULLIF(
            SUM(c.area_ha),
            0
        )
            AS declividade_media_pct,


        MODE()

        WITHIN GROUP (

            ORDER BY
                c.uso_predominante

        ) AS uso_predominante,


        -- ================================================
        -- ROBUSTEZ
        -- ================================================

        COUNT(*)

        FILTER (

            WHERE
                c.estabilidade_ipl =
                'Alta'

        )
        *
        100.0
        /
        COUNT(*)
            AS pct_celulas_estabilidade_alta,


        SUM(
            c.amplitude_ipl
            *
            c.area_ha
        )

        /
        NULLIF(
            SUM(c.area_ha),
            0
        )
            AS amplitude_ipl_media


    FROM staging.area_geom_9f a


    JOIN staging.area_celula_9f r

        ON r.cluster_ref =
           a.cluster_ref


    JOIN spatial.celula_prioridade c

        ON c.id_celula =
           r.id_celula


    GROUP BY

        a.codigo_ibge,

        a.cluster_ref,

        a.geom

),


com_ipa AS (

    SELECT

        x.*,

        i.ipa
            AS ipa_municipal


    FROM metricas x


    JOIN analytics.ipa_municipio i

        ON i.codigo_ibge =
           x.codigo_ibge

        AND i.ano_referencia =
            {ANO_REFERENCIA}

        AND i.versao_modelo =
            '{VERSAO_IPA}'

),


classificado AS (

    SELECT

        *,


        CASE

            WHEN
                numero_celulas
                >= {MIN_CELULAS_AREA}

                AND

                area_grade_ha
                >= {MIN_AREA_HA}

            THEN
                'Área prioritária contínua'

            ELSE
                'Núcleo isolado'

        END
            AS status_area,


        CASE

            WHEN
                pct_celulas_estabilidade_alta
                >= 70

                AND

                amplitude_ipl_media <= 5

            THEN
                'Alta'


            WHEN
                pct_celulas_estabilidade_alta
                >= 40

                AND

                amplitude_ipl_media <= 10

            THEN
                'Media'


            ELSE
                'Baixa'

        END
            AS robustez_area,


        CASE

            WHEN prioridade_integrada_media <= 20
                THEN 'Muito baixa'

            WHEN prioridade_integrada_media <= 40
                THEN 'Baixa'

            WHEN prioridade_integrada_media <= 60
                THEN 'Media'

            WHEN prioridade_integrada_media <= 80
                THEN 'Alta'

            ELSE
                'Muito alta'

        END
            AS classificacao_area


    FROM com_ipa

),


ranqueado AS (

    SELECT

        *,


        ROW_NUMBER()

        OVER (

            PARTITION BY
                codigo_ibge

            ORDER BY

                prioridade_integrada_media
                    DESC,

                area_grade_ha
                    DESC,

                cluster_ref

        ) AS rank_area_municipio,


        ROW_NUMBER()

        OVER (

            ORDER BY

                prioridade_integrada_media
                    DESC,

                area_grade_ha
                    DESC,

                codigo_ibge,

                cluster_ref

        ) AS rank_area_geral


    FROM classificado

)


SELECT

    *,


    codigo_ibge

    ||

    '-A'

    ||

    LPAD(
        rank_area_municipio::TEXT,
        3,
        '0'
    )
        AS codigo_area


FROM ranqueado;
"""


sql_processamento += f"""

-- ============================================================
-- 6. APAGAR VERSÃO ANTERIOR
-- ============================================================

DELETE FROM spatial.area_prioritaria

WHERE
    versao_areas =
    '{VERSAO_AREAS}';


-- ============================================================
-- 7. INSERIR ÁREAS
-- ============================================================

INSERT INTO spatial.area_prioritaria (

    codigo_area,

    cluster_ref,

    codigo_ibge,

    numero_celulas,

    area_grade_ha,

    area_geometrica_ha,

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

    distancia_drenagem_min_m,

    vegetacao_entorno_media_pct,

    declividade_media_pct,

    uso_predominante,

    pct_celulas_estabilidade_alta,

    amplitude_ipl_media,

    robustez_area,

    classificacao_area,

    status_area,

    rank_area_municipio,

    rank_area_geral,

    versao_areas,

    geom

)

SELECT

    codigo_area,

    cluster_ref,

    codigo_ibge,

    numero_celulas,

    area_grade_ha,

    area_geometrica_ha,

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

    distancia_drenagem_min_m,

    vegetacao_entorno_media_pct,

    declividade_media_pct,

    uso_predominante,

    pct_celulas_estabilidade_alta,

    amplitude_ipl_media,

    robustez_area,

    classificacao_area,

    status_area,

    rank_area_municipio,

    rank_area_geral,

    '{VERSAO_AREAS}',

    geom


FROM staging.area_resultado_9f;


-- ============================================================
-- 8. RASTREABILIDADE
-- ============================================================

INSERT INTO spatial.area_prioritaria_celula (

    id_area,

    id_celula

)

SELECT

    a.id_area,

    r.id_celula


FROM spatial.area_prioritaria a


JOIN staging.area_celula_9f r

    ON r.cluster_ref =
       a.cluster_ref


WHERE
    a.versao_areas =
    '{VERSAO_AREAS}';

"""

print("=" * 72)
print("VERDEPRIORIZA - ÁREAS PRIORITÁRIAS")
print("=" * 72)


with engine.begin() as conn:

    conn.execute(
        text(
            sql_processamento
        )
    )


print(
    "\nAgrupamento concluído."
)