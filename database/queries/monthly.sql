WITH monthly AS (
    SELECT p.name AS place,
           date_trunc('month', r.created_at) AS month,
           count(*) AS n_reviews,
           sum(r.rating) AS rating_sum
    FROM reviews r
    JOIN places p USING (place_id)
    GROUP BY ALL
)
SELECT place,
       month,
       n_reviews,
       rating_sum / n_reviews AS avg_rating,
       sum(rating_sum) OVER w / sum(n_reviews) OVER w AS rolling_3m
FROM monthly
WINDOW w AS (
    PARTITION BY place
    ORDER BY month
    RANGE BETWEEN INTERVAL 2 MONTH PRECEDING AND CURRENT ROW
)
ORDER BY place, month;
