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

SELECT
  R.request_uuid,
  R.video_uuid AS video_analysis_uuid,
  IFNULL(S.status, 'PENDING') AS status,
IF
  ( S.request_uuid IS NULL, ARRAY(
    SELECT
      STRUCT(
        CAST(dest.ads_customer_id AS INT64) AS customer_id,
        CAST(dest.campaign_id AS INT64) AS campaign_id,
        CAST(dest.adgroup_id AS INT64) AS ad_group_id,
        ARRAY(
        SELECT
          STRUCT(offer_id AS offer_id,
            'PENDING' AS status)
        FROM
          UNNEST(R.offer_ids) AS offer_id ) AS products,
        CAST(NULL AS STRING) AS error_message,
        CAST(NULL AS INT64) AS cpc_bid_micros)
    FROM
      UNNEST(R.destinations) AS dest ), S.ads_entities) AS ads_entities,
  R.timestamp,
FROM
  `{project_id}.{dataset_id}.{google_ads_insertion_requests_table_id}` AS R
LEFT JOIN `{project_id}.{dataset_id}.{ad_group_insertion_status_table_id}` AS S
  ON R.request_uuid = S.request_uuid
WHERE R.request_uuid = @request_uuid
ORDER BY timestamp DESC
