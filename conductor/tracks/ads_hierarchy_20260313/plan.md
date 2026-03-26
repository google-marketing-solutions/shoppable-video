# Implementation Plan: Ads Customer ID Hierarchy Handling

## Phase 1: Infrastructure & Configuration Cleanup

- [x] Task: Rename Terraform variable `ads_customer_id` to `google_ads_customer_id` globally (root and modules) to clarify it as the "Platform Context" ID. 4fb9c75
- [x] Task: Update root `terraform/main.tf` to pass `google_ads_customer_id` to the webapp module. 4fb9c75
- [x] Task: Update `terraform/modules/webapp/variables.tf` and `main.tf` to inject the ID as the `GOOGLE_ADS_CUSTOMER_ID` environment variable. 4fb9c75
- [x] Task: Verify environment variable propagation in `src/webapp/backend/app/core/config.py`. 4fb9c75
- [x] Task: Conductor - User Manual Verification 'Phase 1: Infrastructure & Configuration Cleanup' (Protocol in workflow.md) 4fb9c75

## Phase 2: Backend Service Refactoring (Explicit Context)

- [x] Task: Write tests for `GoogleAdsClient` initialization with `login-customer-id` logic. 10b627d
- [x] Task: Write tests for `GoogleAdsService` supporting dynamic `login_customer_id` for user actions. 10b627d
- [x] Task: Refactor `app/services/google_ads.py` methods to accept `login_customer_id` context and `customer_id` filters. 10b627d
- [x] Task: Write tests for `list_accessible_subaccounts` method. 10b627d
- [x] Task: Implement `list_accessible_subaccounts` in `GoogleAdsService` to find all nested accounts under an explicit MCC. 10b627d
- [x] Task: Conductor - User Manual Verification 'Phase 2: Backend Service Refactoring' (Protocol in workflow.md) 10b627d

## Phase 3: Cloud Run Worker Updates

- [ ] Task: Write tests for the Cloud Run worker handling multi-destination payloads.
- [ ] Task: Update `src/webapp/cloud_run/ads_service.py` and `main.py` to iterate over destinations and use `customer_id` for each push.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Cloud Run Worker Updates' (Protocol in workflow.md)

## Phase 4: API & Account Discovery

- [x] Task: Update `app/api/dependencies.py` to provide `get_google_ads_service` with explicit `login_customer_id` routing and `get_discovery_service` for contextless discovery. 1e764a6
- [x] Task: Implement `GET /api/reports/accessible-customers` endpoint in `app/api/routes/reports.py` using discovery service. 1e764a6
- [x] Task: Update `accessible-customers` logic to fetch global entry points and map them to descriptive names. 1e764a6
- [ ] Task: Write tests for updated `POST /api/candidates/submission-requests` using the `destinations` schema with explicit `customer_id`.
- [ ] Task: Refactor submission endpoint and `BigQueryService` to handle granular, multi-destination status tracking.
- [x] Task: Conductor - User Manual Verification 'Phase 4: API & Account Discovery' (Protocol in workflow.md) 1e764a6

## Phase 5: Frontend Enhancements (Multi-Push UI)

- [ ] Task: Update Angular models and `DataService` to support the `login_customer_id` distinction and manage the "Active Account" state.
- [ ] Task: Implement "Active Account" dropdown in the top-right corner of the UI.
- [ ] Task: Refactor `SubmissionDialogComponent` to use `list_accessible_subaccounts(login_customer_id)` to populate the destination multi-select if the active account is an MCC.
- [ ] Task: Update "Push Status" dashboard to display granular, per-destination status rows.
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Frontend Enhancements' (Protocol in workflow.md)

## Phase 6: Documentation & Final Validation

- [ ] Task: Update `README.md` (or create `ADS_HIERARCHY.md`) to explain the explicit User Context, the variable naming convention, and the frontend state management.
- [ ] Task: Verify end-to-end flow: User selects an MCC as the Active Account and pushes to multiple CIDs.
- [ ] Task: Verify end-to-end flow: User selects a Direct CID as the Active Account and pushes.
- [ ] Task: Conductor - User Manual Verification 'Phase 6: Documentation & Final Validation' (Protocol in workflow.md)
