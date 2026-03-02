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
--
-- Retrieves and structures product matches for a specific video analysis run.
--
-- This query fetches an analysis record, unnests identified products, joins in matched product
-- offers and their current status, and structures the results hierarchically by video,
-- identified product, and candidate matches, including variants.

WITH
  TargetVideo AS (
    -- Selects the specific video analysis record to process based on the @uuid parameter.
    SELECT uuid, source, video_id, gcs_uri, md5_hash, metadata, identified_products
    FROM `{project_id}.{dataset_id}.{video_analysis_table_id}`
    WHERE uuid = @uuid
  ),
  BaseMatches AS (
    -- 1. Flattens identified products and joins with matched offers and their statuses.
    SELECT
      TV.uuid AS video_uuid,
      IP.uuid AS ip_uuid,  -- Identified Product UUID
      IP.title AS ip_title,
      IP.description AS ip_description,
      IP.relevance_reasoning,
      IP.video_timestamp,
      MP.matched_product_offer_id AS offer_id,
      COALESCE(RP.title, MP.matched_product_title) AS title,
      COALESCE(RP.brand, MP.matched_product_brand) AS brand,
      RP.link,
      RP.image_link,
      COALESCE(RP.availability, 'unknown') AS availability,
      MP.timestamp AS matched_timestamp,
      MP.distance,
      COALESCE(CS.status, 'UNREVIEWED') AS status,
      CS.is_added_by_user,
      CS.user,
      CS.modified_timestamp,
      COALESCE(RP.image_link, MP.matched_product_offer_id) AS variant_group_id
    FROM TargetVideo AS TV
    CROSS JOIN UNNEST(TV.identified_products) AS IP
    INNER JOIN
      `{project_id}.{dataset_id}.{matched_products_view_id}` AS MP
      ON MP.uuid = IP.uuid
    LEFT JOIN
      (
        -- Retrieves the most relevant product information, prioritizing 'online' channel.
        SELECT *
        FROM `{project_id}.{dataset_id}.{latest_products_table_id}`
        QUALIFY
          ROW_NUMBER() OVER (PARTITION BY offer_id ORDER BY IF(channel = 'online', 1, 0) DESC) = 1
      ) AS RP  -- RP for Relevant Product
      ON RP.offer_id = MP.matched_product_offer_id
    LEFT JOIN
      `{project_id}.{dataset_id}.{candidate_status_view_id}` AS CS
      ON
        CS.video_analysis_uuid = TV.uuid
        AND CS.identified_product_uuid = IP.uuid
        AND CS.candidate_offer_id = MP.matched_product_offer_id
  ),
  GroupedCandidates AS (
    -- 2. Groups matched products by image_url (variant_group_id) to elect a 'hero' offer.
    SELECT
      video_uuid,
      ip_uuid,
      ip_title,
      ip_description,
      relevance_reasoning,
      video_timestamp,
      STRUCT(
        hero.offer_id AS matched_product_offer_id,
        hero.title AS matched_product_title,
        hero.brand AS matched_product_brand,
        hero.link AS matched_product_link,
        hero.image_link AS matched_product_image_link,
        hero.availability AS matched_product_availability,
        hero.matched_timestamp,
        hero.distance,
        STRUCT(hero.status, hero.user, hero.is_added_by_user, hero.modified_timestamp)
          AS candidate_status,
        ARRAY(
          SELECT AS STRUCT variant_offer_id, variant_title, variant_brand
          FROM UNNEST(all_variants)
          WHERE variant_offer_id != hero.offer_id
        ) AS variants) AS candidate
    FROM
      (
        SELECT
          video_uuid,
          ip_uuid,
          ip_title,
          ip_description,
          relevance_reasoning,
          video_timestamp,
          -- Selects the best offer as 'hero': APPROVED status first, then by smallest distance.
          ARRAY_AGG(
            STRUCT(
              offer_id,
              title,
              brand,
              link,
              image_link,
              availability,
              matched_timestamp,
              distance,
              status,
              is_added_by_user,
              user,
              modified_timestamp)
            ORDER BY(status = 'APPROVED') DESC, distance ASC
            LIMIT 1)[OFFSET(0)] AS hero,
          -- Aggregates all offers within the same variant group.
          ARRAY_AGG(
            STRUCT(offer_id AS variant_offer_id, title AS variant_title, brand AS variant_brand))
            AS all_variants
        FROM BaseMatches
        GROUP BY
          video_uuid, ip_uuid, ip_title, ip_description, relevance_reasoning, video_timestamp,
          variant_group_id
      )
  ),
  AggregatedIPs AS (
    -- 3. Aggregates all product candidates for each Identified Product (IP).
    SELECT
      video_uuid,
      STRUCT(
        ip_uuid AS uuid,
        ip_title AS title,
        ip_description AS description,
        relevance_reasoning,
        video_timestamp,
        ARRAY_AGG(candidate IGNORE NULLS) AS matched_products) AS ip_struct
    FROM GroupedCandidates
    GROUP BY video_uuid, ip_uuid, ip_title, ip_description, relevance_reasoning, video_timestamp
  ),
  FinalVideoProducts AS (
    -- 4. Aggregates all Identified Products for the video, ordered by timestamp.
    SELECT
      video_uuid,
      ARRAY_AGG(ip_struct ORDER BY ip_struct.video_timestamp ASC) AS identified_products
    FROM AggregatedIPs
    GROUP BY video_uuid
  )
-- 5. Constructs the final result, joining video metadata with the aggregated product structure.
SELECT
  STRUCT(
    TV.uuid,
    TV.source,
    TV.video_id,
    TV.gcs_uri,
    TV.md5_hash,
    TV.metadata) AS video,
  COALESCE(FVP.identified_products, []) AS identified_products
FROM TargetVideo AS TV
LEFT JOIN FinalVideoProducts AS FVP
  ON TV.uuid = FVP.video_uuid;
