SELECT p.name AS place,
       r.rating,
       r.comment,
       r.created_at,
       r.updated_at
FROM reviews r
JOIN places p USING (place_id)
ORDER BY r.created_at DESC;
