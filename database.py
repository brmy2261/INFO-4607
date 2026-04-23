# bridge between fastapi and postgres
# how to talk to postgres

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

host = os.getenv("POSTGRES_HOST", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
db = os.getenv("POSTGRES_DB")
user = os.getenv("POSTGRES_USER")
pw = os.getenv("POSTGRES_PASSWORD")

if not all([db, user, pw]):
    raise RuntimeError("missing pw, db, user")

database_url = (
    f"postgresql+psycopg2://{user}:{quote_plus(pw)}@{host}:{port}/{quote_plus(db)}"
)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    connect_args={"options": "-csearch_path=third_iteration"}
)  # this is what fastapi talks to

sessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# each api request gets its own database session

def test_connection():
    with engine.connect() as conn:
        return conn.execute(text("select 1")).scalar_one()