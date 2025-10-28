DECLARE max_partition_date DATE;
SET max_partition_date = (
    SELECT MAX(_PARTITIONDATE) AS `date`
    FROM `{project_id}.{dataset_id}.Products_{merchant_id}`
);
WITH
  Products AS (
    SELECT
      offer_id,
      title,
      brand,
      description,
      product_type,
      google_product_category_path AS google_product_category,
      age_group,
      color,
      gender,
      material,
      `pattern`,
      -- When SKU is associated with multiple listings, only pick one
      ROW_NUMBER()
        OVER (
          PARTITION BY offer_id
          ORDER BY
            IF(channel = 'ONLINE', 1, 0) DESC,
            IF(content_language = 'en', 1, 0) DESC
        ) AS rn
    FROM `{project_id}.{dataset_id}.Products_{merchant_id}` AS P
    WHERE
      P._PARTITIONDATE = max_partition_date
      AND NOT EXISTS(
        SELECT 1
        FROM `{project_id}.{dataset_id}.product_embeddings` AS PE
        WHERE PE.id = P.offer_id
      )
  )
SELECT * EXCEPT (rn) FROM Products WHERE rn = 1
LIMIT {product_limit};
