WITH monthly AS (
    SELECT place_id,
           date_trunc('month', created_at) AS month,
           count(*) AS n_reviews,
           avg(rating) AS avg_rating
    FROM reviews
    GROUP BY ALL
)
SELECT *,
       avg(avg_rating) OVER (
           PARTITION BY place_id
           ORDER BY month
           ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
       ) AS rolling_3m
FROM monthly
ORDER BY place_id, month;
