WITH stats AS (
    SELECT place_id, count(*) AS n, avg(rating) AS avg_rating, sum(rating) AS total
    FROM reviews
    GROUP BY place_id
),
prior AS (
    SELECT avg(rating) AS global_mean, 20 AS m
    FROM reviews
)
SELECT p.name AS place,
       s.n,
       round(s.avg_rating, 2) AS avg_rating,
       round((prior.m * prior.global_mean + s.total) / (prior.m + s.n), 2) AS bayesian_rating
FROM stats s
JOIN places p USING (place_id)
CROSS JOIN prior
ORDER BY bayesian_rating DESC;
