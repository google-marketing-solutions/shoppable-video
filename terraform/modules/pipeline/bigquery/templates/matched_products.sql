-- Copyright 2025 Google LLC

-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at

--     https://www.apache.org/licenses/LICENSE-2.0

-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

WITH
  IdentifiedProducts AS (
    SELECT
      IP.uuid,
      IP.title,
      IP.description,
      IP.embedding
    FROM
      `${PROJECT_ID}.${DATASET_ID}.${VIDEO_ANALYSIS_TABLE_NAME}`,
      UNNEST(identified_products) AS IP
    WHERE
      `status` = 'SUCCESS'
      AND uuid NOT IN (
        SELECT DISTINCT
          uuid
        FROM
          `${PROJECT_ID}.${DATASET_ID}.${MATCHED_PRODUCTS_TABLE_NAME}`
        WHERE
          `timestamp` < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL ${REFRESH_WINDOW_DAYS} DAY)
      )
  )
SELECT
  CURRENT_TIMESTAMP() AS `timestamp`,
  query.uuid,
  query.title AS identified_product_title,
  query.description AS identified_product_description,
  base.id AS matched_product_offer_id,
  base.embedding_metadata.title AS matched_product_title,
  base.embedding_metadata.brand AS matched_product_brand,
  distance
FROM
  VECTOR_SEARCH(
    TABLE `${PROJECT_ID}.${DATASET_ID}.${PRODUCT_EMBEDDINGS_TABLE_NAME}`,
    'embedding',
    (SELECT uuid, title, embedding, `description` FROM IdentifiedProducts),
    'embedding',
    top_k => ${NUM_OF_MATCHED_PRODUCTS});
