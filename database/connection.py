from pathlib import Path

import duckdb

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "reviews.duckdb"
SNAPSHOT_PATH = ROOT / "snapshot" / "reviews.duckdb"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
QUERIES_DIR = Path(__file__).parent / "queries"


def get_connection(path=None, read_only=False):
    if path is None:
        path = SNAPSHOT_PATH if read_only and not DB_PATH.exists() else DB_PATH
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path), read_only=read_only)
    if not read_only:
        con.execute(SCHEMA_PATH.read_text())
    return con


def load_query(name):
    return (QUERIES_DIR / f"{name}.sql").read_text()
