# Implementation Plan: Ads Customer ID Hierarchy Handling

## Phase 1: Infrastructure & Configuration Cleanup
- [ ] Task: Rename Terraform variable `ads_customer_id` to `google_ads_customer_id` globally (root and modules) to clarify it as the "Platform Context" ID.
- [ ] Task: Update root `terraform/main.tf` to pass `google_ads_customer_id` to the webapp module.
- [ ] Task: Update `terraform/modules/webapp/variables.tf` and `main.tf` to inject the ID as the `GOOGLE_ADS_CUSTOMER_ID` environment variable.
- [ ] Task: Verify environment variable propagation in `src/webapp/backend/app/core/config.py`.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Infrastructure & Configuration Cleanup' (Protocol in workflow.md)

## Phase 2: Backend Service Refactoring (Hierarchy & Fallback)
- [ ] Task: Write tests for `GoogleAdsClient` initialization with `login-customer-id` logic.
- [ ] Task: Implement "Smart Fallback" logic in `app/api/dependencies.py` to handle hierarchy errors (MCC vs. Direct CID).
- [ ] Task: Write tests for `GoogleAdsService` supporting dynamic `target_customer_id` for user actions.
- [ ] Task: Refactor `app/services/google_ads.py` methods to accept `target_customer_id` as an explicit argument.
- [ ] Task: Write tests for `list_accessible_subaccounts` method.
- [ ] Task: Implement `list_accessible_subaccounts` in `GoogleAdsService` with MCC filtering and descriptive metadata.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Backend Service Refactoring' (Protocol in workflow.md)

## Phase 3: Cloud Run Worker Updates
- [ ] Task: Write tests for the Cloud Run worker handling multi-destination payloads.
- [ ] Task: Update `src/webapp/cloud_run/ads_service.py` and `main.py` to iterate over destinations and use `target_customer_id` for each push.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Cloud Run Worker Updates' (Protocol in workflow.md)

## Phase 4: API & Account Discovery
- [ ] Task: Write tests for `GET /api/reports/accessible-customers`.
- [ ] Task: Implement `accessible-customers` endpoint in `app/api/routes/reports.py`.
- [ ] Task: Write tests for updated `POST /api/candidates/submission-requests` using the `target_customer_id` schema.
- [ ] Task: Refactor submission endpoint and `BigQueryService` to handle granular, multi-destination status tracking.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: API & Account Discovery' (Protocol in workflow.md)

## Phase 5: Frontend Enhancements (Multi-Push UI)
- [ ] Task: Update Angular models and `DataService` to support the `target_customer_id` distinction.
- [ ] Task: Refactor `SubmissionDialogComponent` to use the account discovery endpoint and implement multi-select logic.
- [ ] Task: Update "Push Status" dashboard to display granular, per-destination status rows.
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Frontend Enhancements' (Protocol in workflow.md)

## Phase 6: Documentation & Final Validation
- [ ] Task: Update `README.md` (or create `ADS_HIERARCHY.md`) to explain the Platform vs. User context, the variable naming convention, and the Smart Fallback mechanism.
- [ ] Task: Verify end-to-end flow: MCC user pushing to multiple CIDs.
- [ ] Task: Verify end-to-end flow: Direct CID user pushing to their accessible account.
- [ ] Task: Conductor - User Manual Verification 'Phase 6: Documentation & Final Validation' (Protocol in workflow.md)
