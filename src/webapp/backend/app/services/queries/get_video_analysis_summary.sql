-- Copyright 2025 Google LLC
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     https://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

-- Retrieves video analysis summaries, supporting pagination.
-- Retrieves video analysis summaries, supporting pagination.
WITH
  FilteredVideos AS (
    -- First, we get the total count and the ordered list before applying the LIMIT
    SELECT
      uuid,
      source,
      video_id,
      gcs_uri,
      md5_hash,
      timestamp,
      identified_products,
      COUNT(*) OVER() AS total_count
    FROM `{project_id}.{dataset_id}.{video_analysis_table_id}`
  ),
  PaginatedVideos AS (
    SELECT *
    FROM FilteredVideos
    ORDER BY timestamp DESC, uuid ASC
    LIMIT @limit OFFSET @offset
  ),
  BaseData AS (
    SELECT
      PV.uuid AS video_uuid,
      PV.source,
      PV.video_id,
      PV.gcs_uri,
      PV.md5_hash,
      PV.timestamp,
      PV.total_count,
      IP.uuid AS ip_uuid,
      MP.matched_product_offer_id,
      COALESCE(CS.status, 'UNREVIEWED') AS status
    FROM PaginatedVideos AS PV
    LEFT JOIN UNNEST(PV.identified_products) AS IP
    LEFT JOIN `{project_id}.{dataset_id}.{matched_products_view_id}` AS MP
      ON IP.uuid = MP.uuid
    LEFT JOIN `{project_id}.{dataset_id}.{candidate_status_view_id}` AS CS
      ON PV.uuid = CS.video_analysis_uuid
      AND IP.uuid = CS.identified_product_uuid
      AND MP.matched_product_offer_id = CS.candidate_offer_id
  )
SELECT
  STRUCT(
    video_uuid AS uuid,
    source,
    video_id,
    gcs_uri,
    md5_hash
  ) AS video,
  COUNT(DISTINCT ip_uuid) AS identified_products_count,
  -- Replaced FILTER with COUNT(DISTINCT IF(...))
  COUNT(DISTINCT IF(matched_product_offer_id IS NOT NULL, CONCAT(ip_uuid, '|', matched_product_offer_id), NULL)) AS matched_products_count,
  COUNT(DISTINCT IF(status = 'APPROVED', CONCAT(ip_uuid, '|', matched_product_offer_id), NULL)) AS approved_products_count,
  COUNT(DISTINCT IF(status = 'DISAPPROVED', CONCAT(ip_uuid, '|', matched_product_offer_id), NULL)) AS disapproved_products_count,
  COUNT(DISTINCT IF(status = 'UNREVIEWED', CONCAT(ip_uuid, '|', matched_product_offer_id), NULL)) AS unreviewed_products_count,
  MAX(timestamp) AS sort_key,
  ANY_VALUE(total_count) AS total_count,
FROM BaseData
GROUP BY video_uuid, source, video_id, gcs_uri, md5_hash
ORDER BY sort_key DESC, video_uuid ASC;
