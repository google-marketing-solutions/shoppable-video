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
  TargetVideo AS (
    SELECT
      uuid AS video_uuid,
      source,
      video_id,
      gcs_uri,
      md5_hash,
      metadata,
      identified_products
    FROM `{project_id}.{dataset_id}.{video_analysis_table_id}`
    WHERE uuid = @uuid
  ),
  -- Extract Identified Products (IPs).
  TargetIPs AS (
    SELECT
      TV.video_uuid,
      IP.uuid AS ip_uuid,
      IP.title AS ip_title,
      IP.description AS ip_description,
      IP.relevance_reasoning AS ip_relevance_reasoning,
      IP.video_timestamp AS ip_video_timestamp
    FROM TargetVideo AS TV
    LEFT JOIN UNNEST(TV.identified_products) AS IP
  ),
  -- Get matches ONLY for these IPs.
  TargetMatches AS (
    SELECT MP.*
    FROM `{project_id}.{dataset_id}.{matched_products_view_id}` AS MP
    INNER JOIN TargetIPs AS IP ON MP.uuid = IP.ip_uuid
  ),
  -- Get relevant Offer IDs to prune the Products table.
  TargetOffers AS (
    SELECT DISTINCT matched_product_offer_id
    FROM TargetMatches
    WHERE matched_product_offer_id IS NOT NULL
  ),
  -- Filter and Rank Products.
  RelevantProducts AS (
    SELECT * EXCEPT(row_num)
    FROM (
      SELECT
        P.offer_id,
        P.title,
        P.brand,
        P.link,
        P.image_link,
        P.availability,
        ROW_NUMBER() OVER (
          PARTITION BY P.offer_id ORDER BY IF(P.channel = "online", 1, 0) DESC
        ) AS row_num
      FROM `{project_id}.{dataset_id}.{latest_products_table_id}` AS P
      INNER JOIN TargetOffers AS T ON P.offer_id = T.matched_product_offer_id
    )
    WHERE row_num = 1
  ),
  -- Filter Status early.
  TargetStatus AS (
    SELECT *
    FROM `{project_id}.{dataset_id}.{candidate_status_view_id}`
    WHERE video_analysis_uuid = @uuid
  ),
  -- Join Data.
  FlatData AS (
    SELECT
      TV.video_uuid,
      IP.ip_uuid,
      IP.ip_title,
      IP.ip_description,
      IP.ip_relevance_reasoning,
      IP.ip_video_timestamp,
      MP.matched_product_offer_id,
      IFNULL(RP.title, MP.matched_product_title) AS matched_product_title,
      IFNULL(RP.brand, MP.matched_product_brand) AS matched_product_brand,
      RP.link AS matched_product_link,
      RP.image_link AS matched_product_image_link,
      IFNULL(RP.availability, "unknown") AS matched_product_availability,
      MP.timestamp AS matched_timestamp,
      MP.distance,
      COALESCE(CS.status, 'UNREVIEWED') AS status,
      CS.is_added_by_user,
      CS.user,
      CS.modified_timestamp,
    FROM TargetVideo AS TV
    INNER JOIN TargetIPs AS IP ON TV.video_uuid = IP.video_uuid
    LEFT JOIN TargetMatches AS MP ON IP.ip_uuid = MP.uuid
    LEFT JOIN RelevantProducts AS RP ON MP.matched_product_offer_id = RP.offer_id
    LEFT JOIN TargetStatus AS CS
      ON TV.video_uuid = CS.video_analysis_uuid
      AND IP.ip_uuid = CS.identified_product_uuid
      AND MP.matched_product_offer_id = CS.candidate_offer_id
  ),

  -- First Level Aggregation: Group Matches per Identified Product
  AggregatedMatches AS (
    SELECT
      video_uuid,
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
          matched_product_link,
          matched_product_image_link,
          matched_product_availability,
          matched_timestamp,
          distance,
          STRUCT(
            status,
            user,
            is_added_by_user,
            modified_timestamp
          ) AS candidate_status
        ) IGNORE NULLS
      ) AS matched_products
    FROM FlatData
    GROUP BY 1, 2, 3, 4, 5, 6
  )

-- Final Aggregation: Re-join Video info (including STRUCT) using ANY_VALUE
SELECT
  STRUCT(
    TV.video_uuid AS uuid,
    ANY_VALUE(TV.source) AS source,
    ANY_VALUE(TV.video_id) AS video_id,
    ANY_VALUE(TV.gcs_uri) AS gcs_uri,
    ANY_VALUE(TV.md5_hash) AS md5_hash,
    ANY_VALUE(TV.metadata) AS metadata
  ) AS video,
  COALESCE(ARRAY_AGG(
    IF(AM.ip_uuid IS NULL, NULL, STRUCT(
      AM.ip_uuid AS uuid,
      AM.ip_title AS title,
      AM.ip_description AS description,
      AM.ip_relevance_reasoning AS relevance_reasoning,
      AM.ip_video_timestamp AS video_timestamp,
      AM.matched_products
    )) IGNORE NULLS
    ORDER BY AM.ip_video_timestamp ASC
  ), []) AS identified_products
FROM TargetVideo TV
LEFT JOIN AggregatedMatches AM ON TV.video_uuid = AM.video_uuid
GROUP BY TV.video_uuid;
