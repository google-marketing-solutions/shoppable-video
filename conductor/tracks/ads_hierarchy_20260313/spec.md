# Track Specification: Ads Customer ID Hierarchy Handling

## Overview
This track addresses the complexity of the Google Ads hierarchy (MCC vs. CID) by decoupling the **Platform Context** (used for system-level data ingestion) from the **User Context** (used for OAuth-based real-time actions). It enables the application to operate under a single company MCC while allowing users to discover and push content to specific sub-accounts (CIDs) they have access to.

## Functional Requirements
1.  **Configuration Wiring:**
    *   Ensure `GOOGLE_ADS_CUSTOMER_ID` (the platform's MCC/Umbrella ID) is correctly passed from Terraform through the webapp module to the backend environment.
2.  **Account Discovery:**
    *   Implement `GET /api/reports/accessible-customers` to list all CIDs the authenticated user has access to under the platform's MCC.
    *   Response must include `descriptive_name`, `customer_id`, `is_manager`, and `parent_mcc_id`.
3.  **Hierarchy-Aware Authentication (Smart Fallback):**
    *   The `GoogleAdsClient` will attempt calls using the platform's MCC as the `login-customer-id`.
    *   If a `NOT_ADS_USER` or `USER_PERMISSION_DENIED` error occurs, the system must automatically retry the call without the header (Direct CID access).
4.  **Multi-Account Push to Ads:**
    *   Refactor the submission API to support an array of `destinations`, each requiring an explicit `target_customer_id`.
    *   Update the "Push to Ads" dialog to allow selecting multiple CIDs from the discovered list.
    *   Prioritize suggesting CIDs already associated with the video in BigQuery.
5.  **Granular Status Tracking:**
    *   Update BigQuery schemas and UI views to track the status of each target account independently within a single submission request.
6.  **MCC Strict Enforcement:**
    *   Filter all accessible accounts to only those that fall under the platform's configured MCC umbrella.
7.  **Cloud Run Worker Compatibility:**
    *   Update the background worker (`src/webapp/cloud_run`) to handle the multi-destination payload and use the `target_customer_id` correctly for each push operation.

## Non-Functional Requirements
1.  **Efficiency:** Cache the user's accessible account list in the session to minimize redundant Ads API calls.
2.  **Robustness:** Implement retry logic for the "Smart Fallback" at the service layer to encapsulate complexity.

## Acceptance Criteria
1.  [ ] Backend successfully receives `GOOGLE_ADS_CUSTOMER_ID` from environment variables.
2.  [ ] Users can see a list of their accessible CIDs in the submission dialog.
3.  [ ] A single video can be pushed to multiple CIDs simultaneously.
4.  [ ] The system logs separate status entries for each CID in the "Push Status" dashboard.
5.  [ ] Users with only CID-level access can still perform pushes (verified via fallback logic).
6.  [ ] Cloud Run worker successfully processes submissions with multiple destinations.
