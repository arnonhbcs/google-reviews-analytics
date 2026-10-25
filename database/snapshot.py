import duckdb

from database.connection import DB_PATH, SNAPSHOT_PATH


def export():
    SNAPSHOT_PATH.parent.mkdir(exist_ok=True)
    SNAPSHOT_PATH.unlink(missing_ok=True)
    with duckdb.connect(str(SNAPSHOT_PATH)) as con:
        con.execute(f"ATTACH '{DB_PATH.as_posix()}' AS source (READ_ONLY)")
        con.execute("CREATE TABLE places AS SELECT * FROM source.places")
        con.execute(
            """
            CREATE TABLE reviews AS
            SELECT review_id, place_id, rating, comment, created_at, updated_at, scraped_at
            FROM source.reviews
            """
        )
        return con.execute("SELECT count(*) FROM reviews").fetchone()[0]


if __name__ == "__main__":
    print(f"{export()} reviews exported to {SNAPSHOT_PATH}")
