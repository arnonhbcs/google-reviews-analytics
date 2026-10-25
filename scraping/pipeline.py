import logging

from database import repository
from scraping import browser, reviews


def scrape(con, place_id, url, profile):
    run_id = repository.start_run(con, place_id)
    new = 0
    try:
        with browser.session(profile) as driver:
            browser.open_reviews(driver, url)
            for page, body in enumerate(browser.responses(driver), 1):
                page_reviews, token = reviews.parse_page(body)
                new += repository.insert_reviews(con, place_id, page_reviews)
                repository.update_run(con, run_id, pages_fetched=page, reviews_new=new)
                logging.info("%s: page %d, %d new reviews", place_id, page, new)
                if not token:
                    logging.info("%s: last page reached", place_id)
                    break
        repository.update_run(
            con, run_id, status="done", finished_at=repository.utcnow()
        )
        return new
    except Exception as error:
        repository.update_run(
            con, run_id, status="failed", error=str(error), finished_at=repository.utcnow()
        )
        raise
