from datetime import datetime


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
        [place_id, name, url, category, total_reviews, datetime.now()],
    )


def insert_reviews(con, reviews):
    if not reviews:
        return 0
    before = con.execute("SELECT count(*) FROM reviews").fetchone()[0]
    scraped_at = datetime.now()
    con.executemany(
        """
        INSERT INTO reviews (review_id, place_id, author_hash, rating, comment, created_at, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (review_id) DO NOTHING
        """,
        [
            [
                review["review_id"],
                review["place_id"],
                review.get("author_hash"),
                review["rating"],
                review.get("comment"),
                review["created_at"],
                scraped_at,
            ]
            for review in reviews
        ],
    )
    after = con.execute("SELECT count(*) FROM reviews").fetchone()[0]
    return after - before


def latest_review_at(con, place_id):
    return con.execute(
        "SELECT max(created_at) FROM reviews WHERE place_id = ?", [place_id]
    ).fetchone()[0]


def start_run(con, place_id):
    return con.execute(
        """
        INSERT INTO scrape_runs (place_id, started_at, status)
        VALUES (?, ?, 'running')
        RETURNING run_id
        """,
        [place_id, datetime.now()],
    ).fetchone()[0]


def save_checkpoint(con, run_id, next_page_url, pages_fetched, reviews_new):
    con.execute(
        """
        UPDATE scrape_runs
        SET last_page_url = ?, pages_fetched = ?, reviews_new = ?
        WHERE run_id = ?
        """,
        [next_page_url, pages_fetched, reviews_new, run_id],
    )


def finish_run(con, run_id, status, error=None):
    con.execute(
        """
        UPDATE scrape_runs
        SET finished_at = ?, status = ?, error = ?
        WHERE run_id = ?
        """,
        [datetime.now(), status, error, run_id],
    )


def last_unfinished_run(con, place_id):
    return con.execute(
        """
        SELECT run_id, last_page_url
        FROM scrape_runs
        WHERE place_id = ?
          AND status IN ('running', 'failed')
          AND last_page_url IS NOT NULL
          AND run_id = (SELECT max(run_id) FROM scrape_runs WHERE place_id = ?)
        """,
        [place_id, place_id],
    ).fetchone()
