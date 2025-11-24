-- Copyright 2025 Google LLC

-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at

--    https://www.apache.org/licenses/LICENSE-2.0

-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

-- Retrieves the set of products that do not yet have embeddings.

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
