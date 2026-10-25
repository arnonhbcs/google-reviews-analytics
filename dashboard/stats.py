import numpy as np
import pandas as pd

STARS = np.arange(1, 6)
PRIOR_WEIGHT = 20


def star_counts(ratings):
    return ratings.value_counts().reindex(STARS, fill_value=0).to_numpy()


def prior(counts):
    return PRIOR_WEIGHT * counts / counts.sum()


def posterior(counts, alpha, draws=4000, seed=0):
    params = counts + alpha
    samples = np.random.default_rng(seed).dirichlet(params, size=draws) @ STARS
    low, high = np.percentile(samples, [2.5, 97.5])
    return STARS @ params / params.sum(), low, high


def rolling_posterior(reviews, alpha, months=3):
    counts = (
        reviews.assign(month=reviews["created_at"].dt.to_period("M"))
        .pivot_table(index="month", columns="rating", aggfunc="size", fill_value=0)
        .reindex(columns=STARS, fill_value=0)
    )
    calendar = pd.period_range(counts.index.min(), counts.index.max(), freq="M")
    window = counts.reindex(calendar, fill_value=0).rolling(months, min_periods=1).sum()
    rows = [
        (month.to_timestamp(), *posterior(row.to_numpy(), alpha))
        for month, row in window.iterrows()
    ]
    return pd.DataFrame(rows, columns=["month", "mean", "low", "high"])
