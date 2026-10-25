import hashlib
import json
from datetime import datetime, timezone


def dig(obj, *path):
    for key in path:
        try:
            obj = obj[key]
        except (IndexError, KeyError, TypeError):
            return None
    return obj


def payload(body, rpcid="qv9Egd"):
    for line in body.split("\n"):
        if line.startswith('[["wrb.fr"'):
            entry = json.loads(line)[0]
            if entry[1] == rpcid and entry[2]:
                return json.loads(entry[2])
    return None


def timestamp(micros):
    if micros:
        return datetime.fromtimestamp(micros / 1e6, timezone.utc).replace(tzinfo=None)


def parse_review(raw):
    review = dig(raw, 0)
    author = dig(review, 1, 4, 5, 0) or ""
    created_at = timestamp(dig(review, 1, 2))
    return {
        "review_id": dig(review, 0),
        "author_hash": hashlib.sha256(author.encode()).hexdigest(),
        "rating": dig(review, 2, 0, 0),
        "comment": dig(review, 2, 15, 0, 0),
        "created_at": created_at,
        "updated_at": timestamp(dig(review, 1, 3)) or created_at,
    }


def parse_page(body):
    data = payload(body)
    if dig(data, 5) is True:
        raise PermissionError("Google Maps returned the limited view")
    reviews = [parse_review(r) for r in dig(data, 2) or []]
    valid = [r for r in reviews if r["review_id"] and r["rating"] and r["created_at"]]
    return valid, dig(data, 1)
