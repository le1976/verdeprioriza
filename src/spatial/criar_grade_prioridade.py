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


engine = create_engine(url)


sql = """
TRUNCATE TABLE
spatial.celula_prioridade;


WITH municipios AS (

    SELECT
        codigo_ibge,

        ST_Transform(
            geom,
            5880
        ) AS geom

    FROM spatial.municipio_alvo

),

grades AS (

    SELECT
        m.codigo_ibge,

        (
            ST_SquareGrid(
                250,
                m.geom
            )
        ).geom AS geom_grid,

        m.geom AS geom_municipio

    FROM municipios m

),

recorte AS (

    SELECT
        codigo_ibge,

        ST_Multi(
            ST_CollectionExtract(
                ST_Intersection(
                    geom_grid,
                    geom_municipio
                ),
                3
            )
        ) AS geom

    FROM grades

    WHERE
        ST_Intersects(
            geom_grid,
            geom_municipio
        )

)

INSERT INTO spatial.celula_prioridade (
    codigo_ibge,
    area_ha,
    geom
)

SELECT
    codigo_ibge,

    ST_Area(geom)
    / 10000.0
    AS area_ha,

    geom

FROM recorte

WHERE
    NOT ST_IsEmpty(geom)

    AND ST_Area(geom) >= 1000;
"""


with engine.begin() as conn:

    conn.execute(
        text(sql)
    )


print(
    "Grade espacial criada."
)