from pathlib import Path

import duckdb

DB_PATH = Path(__file__).parent.parent / "data" / "reviews.duckdb"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
QUERIES_DIR = Path(__file__).parent / "queries"


def get_connection(path=DB_PATH, read_only=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path), read_only=read_only)
    if not read_only:
        con.execute(SCHEMA_PATH.read_text())
    return con


def load_query(name):
    return (QUERIES_DIR / f"{name}.sql").read_text()
