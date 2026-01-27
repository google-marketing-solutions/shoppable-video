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

WITH
  FlatData AS (
    SELECT
      VA.uuid AS video_uuid,
      VA.source,
      VA.video_id,
      VA.gcs_uri,
      VA.md5_hash,
      IP.uuid AS ip_uuid,
      IP.title AS ip_title,
      IP.description AS ip_description,
      IP.relevance_reasoning AS ip_relevance_reasoning,
      IP.video_timestamp AS ip_video_timestamp,
      MP.matched_product_offer_id,
      MP.matched_product_title,
      MP.matched_product_brand,
      MP.timestamp,
      MP.distance,
      COALESCE(CS.status, 'UNREVIEWED') AS status,
      CS.is_added_by_user,
      CS.user,
      CS.modified_timestamp,
    FROM `{project_id}.{dataset_id}.{video_analysis_table_id}` AS VA
    CROSS JOIN UNNEST(VA.identified_products) AS IP
    LEFT JOIN
      `{project_id}.{dataset_id}.{matched_products_view_id}` AS MP
      ON IP.uuid = MP.uuid
    LEFT JOIN
      `{project_id}.{dataset_id}.{candidate_status_view_id}` AS CS
      ON
        VA.uuid = CS.video_analysis_uuid
        AND IP.uuid = CS.identified_product_uuid
        AND MP.matched_product_offer_id = CS.candidate_offer_id
    WHERE VA.uuid = @uuid
  ),
  AggregatedMatches AS (
    SELECT
      video_uuid,
      source,
      video_id,
      gcs_uri,
      md5_hash,
      ip_uuid,
      ip_title,
      ip_description,
      ip_relevance_reasoning,
      ip_video_timestamp,
      ARRAY_AGG(
        STRUCT(
          matched_product_offer_id,
          matched_product_title,
          matched_product_brand,
          timestamp AS matched_timestamp,
          distance,
          STRUCT(
            status,
            user,
            is_added_by_user,
            modified_timestamp
          ) AS candidate_status
        )
        IGNORE NULLS) AS matched_products
    FROM FlatData
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
  ),
  FinalAggregation AS (
    SELECT
      video_uuid,
      source,
      video_id,
      gcs_uri,
      md5_hash,
      ARRAY_AGG(
        STRUCT(
          ip_uuid AS uuid,
          ip_title AS title,
          ip_description AS description,
          ip_relevance_reasoning AS relevance_reasoning,
          ip_video_timestamp AS video_timestamp,
          matched_products
        )
        ORDER BY ip_video_timestamp ASC
      ) AS identified_products
    FROM AggregatedMatches
    GROUP BY 1, 2, 3, 4, 5
  )

SELECT
  STRUCT(
    video_uuid AS uuid,
    source,
    video_id,
    gcs_uri,
    md5_hash) AS video,
  identified_products
FROM FinalAggregation;
