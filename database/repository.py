from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def upsert_place(con, place_id, name, url, category=None, total_reviews=None):
    con.execute(
        """
        INSERT INTO places (place_id, name, url, category, total_reviews, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (place_id) DO UPDATE SET
            name = excluded.name,
            url = excluded.url,
            category = excluded.category,
            total_reviews = coalesce(excluded.total_reviews, places.total_reviews),
            updated_at = excluded.updated_at
        """,
        [place_id, name, url, category, total_reviews, utcnow()],
    )


def set_total_reviews(con, place_id, total):
    con.execute(
        "UPDATE places SET total_reviews = ?, updated_at = ? WHERE place_id = ?",
        [total, utcnow(), place_id],
    )


def insert_reviews(con, place_id, reviews):
    if not reviews:
        return 0
    count = "SELECT count(*) FROM reviews"
    before = con.execute(count).fetchone()[0]
    scraped_at = utcnow()
    con.executemany(
        """
        INSERT INTO reviews (
            review_id, place_id, author_hash, rating,
            comment, created_at, updated_at, scraped_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (review_id) DO UPDATE SET
            rating = excluded.rating,
            comment = excluded.comment,
            updated_at = excluded.updated_at,
            scraped_at = excluded.scraped_at
        """,
        [
            [r["review_id"], place_id, r["author_hash"], r["rating"],
             r["comment"], r["created_at"], r["updated_at"], scraped_at]
            for r in reviews
        ],
    )
    return con.execute(count).fetchone()[0] - before


def start_run(con, place_id):
    return con.execute(
        """
        INSERT INTO scrape_runs (place_id, started_at, status)
        VALUES (?, ?, 'running')
        RETURNING run_id
        """,
        [place_id, utcnow()],
    ).fetchone()[0]


def update_run(con, run_id, **fields):
    columns = ", ".join(f"{name} = ?" for name in fields)
    con.execute(
        f"UPDATE scrape_runs SET {columns} WHERE run_id = ?",
        [*fields.values(), run_id],
    )
