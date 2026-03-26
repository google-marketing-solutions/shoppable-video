# Track Specification: Ads Customer ID Hierarchy Handling

## Overview

This track addresses the complexity of the Google Ads hierarchy (MCC vs. CID) by decoupling the **Platform Context** (used for system-level data ingestion) from the **User Context** (managed explicitly by the frontend). It enables the application to seamlessly support both top-level Platform MCC Administrators and nested Sub-Account Users through a dual-path discovery and authentication strategy.

## Functional Requirements

1. **Configuration Wiring:**
    * Ensure `GOOGLE_ADS_CUSTOMER_ID` (the platform's MCC/Umbrella ID) is correctly passed from Terraform through the webapp module to the backend environment and sanitized.

2. **Dual-Path Account Discovery & Context Selection:**
    * Implement `GET /api/reports/accessible-customers` to facilitate the frontend context decision.
    * **Discovery Logic:** Retrieve all CIDs the user has direct access to globally via `CustomerService.list_accessible_customers()`.
    * **Default Path (Platform MCC Admin):** If the configured Platform MCC (`GOOGLE_ADS_CUSTOMER_ID`) is found in the user's accessible list, the frontend will automatically use it as the active account and hide the target selection dropdown.
    * **Fallback Path (Sub-Account User):** If the Platform MCC is NOT in the accessible list, the backend fetches basic metadata (`descriptive_name`) for each accessible CID. The frontend will display a dropdown requiring the user to select their "Active Account", along with a visual disclaimer to select a platform-relevant account.
    * The selected account ID (whether auto-assigned Platform MCC or user-selected CID) is saved to the frontend state and passed explicitly as `login_customer_id` for all subsequent Ads API calls.

3. **Explicit Authentication:**
    * When the backend receives an explicit `login_customer_id`, the `GoogleAdsClient` uses it directly for all API interactions.

4. **Multi-Account Push to Ads:**
    * Refactor the submission API to support an array of `destinations`, each requiring an explicit `customer_id`, `campaign_id`, and `adgroup_id`.
    * If the user's "Active Account" is an MCC, the "Push to Ads" dialog uses `list_accessible_subaccounts(login_customer_id)` (performing a deep crawl, `level > 0`) to let the user select multiple specific target CIDs under their active MCC.

5. **Granular Status Tracking:**
    * Utilize the existing BigQuery schemas (`ad_group_insertion_status`) and UI views which already support tracking the status of each target account independently within a single submission request.

6. **Cloud Run Worker Compatibility:**
    * Update the background worker (`src/webapp/cloud_run`) to handle the multi-destination payload.
    * The worker must loop through the `destinations` array, applying the exact `customer_id` provided by the frontend for each individual push operation.

## Non-Functional Requirements

1. **Stateless Backend:** The backend relies entirely on the explicit `login_customer_id` passed by the client for all operations following discovery.
2. **Efficiency:** Cache the initial discovery list (with descriptive names) in the frontend state to avoid redundant Ads API calls during navigation.

## Acceptance Criteria

1. [ ] Backend successfully receives and sanitizes `GOOGLE_ADS_CUSTOMER_ID`.
2. [ ] Platform MCC Admins are not prompted to select a target account.
3. [ ] Sub-Account Users see a dropdown of accessible CIDs (with names and a disclaimer) and must select an active account.
4. [ ] The backend executes queries strictly using the frontend-provided `login_customer_id`.
5. [ ] A single video can be pushed to multiple CIDs simultaneously if the active context is an MCC.
6. [ ] Cloud Run worker successfully processes submissions with multiple explicit destinations.
