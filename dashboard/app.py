import sys
from datetime import timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.stats import posterior, prior, rolling_posterior, star_counts
from database.connection import get_connection, load_query

st.set_page_config(
    page_title="Google reviews analytics",
    page_icon=":material/reviews:",
    layout="wide",
)

GOLD = "#F2C14E"
HAZE = "#8E98B3"
PERIODS = {"6 months": 182, "1 year": 365, "3 years": 1095, "All time": None}


@st.cache_data(ttl="10m", show_spinner="Loading reviews...")
def load(query):
    with get_connection(read_only=True) as con:
        return con.sql(load_query(query)).df()


def since(df, column, days):
    if days is None or df.empty:
        return df
    return df[df[column] >= df[column].max() - timedelta(days=days)]


def rating_chart(monthly, bayes):
    x = alt.X("month:T", title=None)
    y = alt.Scale(domain=[1, 5])
    band = (
        alt.Chart(bayes)
        .mark_area(color=GOLD, opacity=0.22)
        .encode(
            x=x,
            y=alt.Y("low:Q", title="Rating", scale=y),
            y2="high:Q",
            tooltip=[
                alt.Tooltip("month:T", title="Month", format="%b %Y"),
                alt.Tooltip("low:Q", title="95% lower", format=".2f"),
                alt.Tooltip("high:Q", title="95% upper", format=".2f"),
            ],
        )
    )
    series = pd.concat([
        monthly[["month", "avg_rating"]]
        .rename(columns={"avg_rating": "rating"})
        .assign(series="Monthly average"),
        bayes[["month", "mean"]]
        .rename(columns={"mean": "rating"})
        .assign(series="Bayesian rating (3 months)"),
    ])
    lines = (
        alt.Chart(series)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=x,
            y=alt.Y("rating:Q", scale=y),
            color=alt.Color(
                "series:N",
                title=None,
                scale=alt.Scale(
                    domain=["Bayesian rating (3 months)", "Monthly average"],
                    range=[GOLD, HAZE],
                ),
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("month:T", title="Month", format="%b %Y"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("rating:Q", title="Rating", format=".2f"),
            ],
        )
    )
    return (band + lines).properties(height=400)


def volume_chart(monthly):
    return (
        alt.Chart(monthly)
        .mark_bar(color=HAZE, cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("yearmonth(month):O", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("n_reviews:Q", title="Reviews"),
            tooltip=[
                alt.Tooltip("yearmonth(month):O", title="Month"),
                alt.Tooltip("n_reviews:Q", title="Reviews"),
            ],
        )
        .properties(height=300)
    )


def distribution_chart(reviews):
    counts = star_counts(reviews["rating"])
    data = pd.DataFrame({"stars": range(1, 6), "reviews": counts})
    data["share"] = data["reviews"] / max(counts.sum(), 1)
    return (
        alt.Chart(data)
        .mark_bar(color=HAZE, cornerRadiusTopRight=3, cornerRadiusBottomRight=3)
        .encode(
            x=alt.X("reviews:Q", title="Reviews"),
            y=alt.Y("stars:O", title="Stars", sort="descending"),
            tooltip=[
                alt.Tooltip("stars:O", title="Stars"),
                alt.Tooltip("reviews:Q", title="Reviews"),
                alt.Tooltip("share:Q", title="Share", format=".1%"),
            ],
        )
        .properties(height=300)
    )


"""
# :material/reviews: Google reviews analytics

How a place is rated over time, with the uncertainty of each rating.
"""

try:
    reviews, monthly, places = load("reviews"), load("monthly"), load("places")
except Exception as error:
    st.error(str(error).split("\n")[0], title="Could not open the database")
    st.stop()

if reviews.empty:
    st.info("Run `python main.py` to collect reviews.", title="No reviews yet")
    st.stop()

st.space("small")
cols = st.columns([1, 3])

controls = cols[0].container(border=True, height="stretch", vertical_alignment="center")
with controls:
    place = st.selectbox(
        "Place", sorted(reviews["place"].unique()), key="place", bind="query-params"
    )
    period = st.pills("Period", list(PERIODS), default="1 year")

if period is None:
    controls.info("Pick a period", icon=":material/info:")
    st.stop()

days = PERIODS[period]
alpha = prior(star_counts(reviews["rating"]))
place_all = reviews[reviews["place"] == place]
place_reviews = since(place_all, "created_at", days)
place_monthly = since(monthly[monthly["place"] == place], "month", days)
place_bayes = since(rolling_posterior(place_all, alpha), "month", days)
mean, low, high = posterior(star_counts(place_reviews["rating"]), alpha)
listed = places.loc[places["place"] == place, "total_reviews"].dropna()

summary = cols[0].container(border=True, height="stretch", vertical_alignment="center")
with summary:
    top, bottom = st.columns(2), st.columns(2)
    top[0].metric(
        "Rating",
        f"{mean:.2f}",
        help="Bayesian rating: posterior mean of a Dirichlet model with a "
        "prior worth 20 reviews",
        width="content",
    )
    top[1].metric("95% interval", f"{low:.2f}–{high:.2f}", width="content")
    bottom[0].metric("Reviews", f"{len(place_reviews):,}", width="content")
    bottom[1].metric(
        "Coverage",
        f"{len(place_all) / listed.iloc[0]:.0%}" if not listed.empty else "-",
        help="Collected reviews out of the total Google Maps lists",
        width="content",
    )

with cols[1].container(border=True, height="stretch", vertical_alignment="center"):
    st.markdown("**Rating over time**")
    st.altair_chart(
        rating_chart(place_monthly, place_bayes),
        alt="Monthly average rating and the 3-month Bayesian rating with its 95% interval",
    )

st.space("medium")

"""
## Activity and distribution

Each bar counts the reviews written that month, by the date they were posted.
"""

cols = st.columns(2)
with cols[0].container(border=True):
    st.markdown("**Reviews per month**")
    st.altair_chart(volume_chart(place_monthly), alt="Number of reviews per month")
with cols[1].container(border=True):
    st.markdown("**Rating distribution**")
    st.altair_chart(distribution_chart(place_reviews), alt="Reviews by star rating")

st.space("medium")

"""
## Raw data
"""

stars = st.pills(
    "Stars",
    options=[5, 4, 3, 2, 1],
    default=[5, 4, 3, 2, 1],
    selection_mode="multi",
    format_func=lambda n: f"{n} ★",
)
st.dataframe(
    place_reviews[place_reviews["rating"].isin(stars)].fillna({"comment": ""}),
    column_order=["created_at", "rating", "comment"],
    column_config={
        "created_at": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD"),
        "rating": st.column_config.NumberColumn("Stars", format="%d ★"),
        "comment": st.column_config.TextColumn("Comment"),
    },
    hide_index=True,
    alt="Reviews of the selected place",
)
