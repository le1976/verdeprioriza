import os
from pathlib import Path

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import URL
from sqlalchemy import text


ROOT_DIR = Path(__file__).resolve().parents[2]


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
# DISTÂNCIA
# ============================================================

sql_distancia = """

WITH calculo AS (

    SELECT

        c.id_celula,

        (

            SELECT

                ST_Distance(
                    c.geom,
                    d.geom
                )

            FROM spatial.bho6_drenagem_alvo d

            WHERE
                d.codigo_ibge =
                c.codigo_ibge

            ORDER BY
                c.geom
                <->
                d.geom

            LIMIT 1

        ) AS distancia

    FROM spatial.celula_prioridade c

    WHERE EXISTS (

        SELECT 1

        FROM spatial.bho6_drenagem_alvo d

        WHERE
            d.codigo_ibge =
            c.codigo_ibge
    )

)

UPDATE spatial.celula_prioridade c

SET

    distancia_drenagem_m =
        calculo.distancia,

    data_calculo =
        CURRENT_TIMESTAMP

FROM calculo

WHERE
    c.id_celula =
    calculo.id_celula;

"""


# ============================================================
# SCORE HIDROLÓGICO
# ============================================================

sql_score = """

UPDATE spatial.celula_prioridade

SET score_hidrologia =

    CASE

        WHEN distancia_drenagem_m IS NULL
            THEN NULL

        WHEN distancia_drenagem_m <= 100
            THEN 100

        WHEN distancia_drenagem_m <= 250
            THEN 80

        WHEN distancia_drenagem_m <= 500
            THEN 60

        WHEN distancia_drenagem_m <= 1000
            THEN 30

        ELSE 0

    END

WHERE distancia_drenagem_m IS NOT NULL;

"""


with engine.begin() as conn:

    print(
        "Calculando distância à drenagem..."
    )

    conn.execute(
        text(
            sql_distancia
        )
    )


    print(
        "Calculando score hidrológico..."
    )

    conn.execute(
        text(
            sql_score
        )
    )


print(
    "Distâncias e scores calculados."
)