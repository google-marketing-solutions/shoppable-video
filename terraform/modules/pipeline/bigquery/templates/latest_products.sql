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

DECLARE max_partition_date DATE;
DECLARE table_count INT64;
DECLARE materialize BOOL;

-- Get latest data partition
SET max_partition_date = (
  SELECT MAX(_PARTITIONDATE) AS `date`
  FROM `${PROJECT_ID}.${DATASET_ID}.Products_${MERCHANT_ID}`
);

-- Check if latest table exists (for first execution)
SET table_count = (
  SELECT COUNT(*) AS table_exists
  FROM `${PROJECT_ID}.${DATASET_ID}.INFORMATION_SCHEMA.TABLES`
  WHERE table_name = "Products_${MERCHANT_ID}_Latest"
);

-- If table doesn't exist, materialize it.
IF(table_count = 0)
  THEN
CREATE OR REPLACE TABLE `${PROJECT_ID}.${DATASET_ID}.Products_${MERCHANT_ID}_Latest`
AS (
  SELECT _PARTITIONDATE AS data_date, *
  FROM `${PROJECT_ID}.${DATASET_ID}.Products_${MERCHANT_ID}`
  WHERE _PARTITIONDATE = max_partition_date
);

END IF;

-- If table exists and the data isn't the latest available, rematerialize it.
SET materialize = (
  SELECT ANY_VALUE(data_date)
  FROM `${PROJECT_ID}.${DATASET_ID}.Products_${MERCHANT_ID}_Latest`
) != max_partition_date;

IF(materialize)
  THEN
CREATE OR REPLACE TABLE `${PROJECT_ID}.${DATASET_ID}.Products_${MERCHANT_ID}_Latest`
AS (
  SELECT *
  FROM `${PROJECT_ID}.${DATASET_ID}.Products_${MERCHANT_ID}`
  WHERE _PARTITIONDATE = max_partition_date
);
END IF;
