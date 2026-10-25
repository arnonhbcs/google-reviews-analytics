import csv
import logging
import sys
from pathlib import Path

from database import repository
from database.connection import get_connection
from scraping.pipeline import scrape

ROOT = Path(__file__).resolve().parent
PLACES = ROOT / "places.csv"
PROFILE = ROOT / ".chrome-profile"


def load_places(selected):
    with open(PLACES, encoding="utf-8-sig") as file:
        places = list(csv.DictReader(file))
    return [p for p in places if not selected or p["place_id"] in selected]


def main(selected):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    con = get_connection()
    for place in load_places(selected):
        place_id = place["place_id"]
        repository.upsert_place(con, place_id, place["name"], place["url"], place["category"])
        try:
            new = scrape(con, place_id, place["url"], PROFILE)
            logging.info("%s: done, %d new reviews", place_id, new)
        except Exception as error:
            logging.error("%s: %s: %s", place_id, type(error).__name__, error)
    con.close()


if __name__ == "__main__":
    main(sys.argv[1:])
