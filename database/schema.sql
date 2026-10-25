CREATE TABLE IF NOT EXISTS places (
    place_id      VARCHAR PRIMARY KEY,
    name          VARCHAR NOT NULL,
    url           VARCHAR NOT NULL,
    category      VARCHAR,
    total_reviews INTEGER,
    updated_at    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id   VARCHAR PRIMARY KEY,
    place_id    VARCHAR NOT NULL REFERENCES places (place_id),
    author_hash VARCHAR,
    rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment     VARCHAR,
    created_at  TIMESTAMP NOT NULL,
    updated_at  TIMESTAMP,
    scraped_at  TIMESTAMP NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS scrape_runs_seq;

CREATE TABLE IF NOT EXISTS scrape_runs (
    run_id        INTEGER PRIMARY KEY DEFAULT nextval('scrape_runs_seq'),
    place_id      VARCHAR NOT NULL REFERENCES places (place_id),
    started_at    TIMESTAMP NOT NULL,
    finished_at   TIMESTAMP,
    status        VARCHAR NOT NULL,
    pages_fetched INTEGER DEFAULT 0,
    reviews_new   INTEGER DEFAULT 0,
    last_page_url VARCHAR,
    error         VARCHAR
);
