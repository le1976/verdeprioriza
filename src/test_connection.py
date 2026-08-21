import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, URL, text

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 5432)),
    database=os.getenv("DB_NAME"),
)

engine = create_engine(url)

with engine.connect() as conn:
    resultado = conn.execute(
        text("""
            SELECT
                current_database(),
                current_user,
                PostGIS_Version();
        """)
    )

    print(resultado.fetchone())