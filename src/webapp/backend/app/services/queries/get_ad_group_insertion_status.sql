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
  t1.request_uuid,
  t2.video_uuid AS video_analysis_uuid,
  t1.status,
  t1.ads_entities,
  t1.timestamp
FROM
  `{project_id}.{dataset_id}.{ad_group_insertion_status_table_id}` AS t1
INNER JOIN `{project_id}.{dataset_id}.{google_ads_insertion_requests_table_id}` AS t2
  ON t1.request_uuid = t2.request_uuid
WHERE request_uuid = @request_uuid
ORDER BY timestamp DESC
