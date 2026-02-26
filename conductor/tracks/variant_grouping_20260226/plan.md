# Implementation Plan: Group Product Variants

## Phase 1: BigQuery and Backend Data Models

- [~] Task: Update the `MatchedProduct` Backend Model
  - [ ] Action: Edit `src/webapp/backend/app/models/product.py`. Create a new `Variant` Pydantic model containing `variant_offer_id`, `variant_title`, and `variant_brand`. Add an optional `variants` list of this type to `MatchedProduct`.
  - [ ] Action: Run `pytest` to ensure no existing tests are broken by the model extension.

- [ ] Task: Modify BigQuery Retrieval Query
  - [ ] Action: Edit `src/webapp/backend/app/services/queries/get_video_analysis.sql`. Introduce a new subquery/CTE before `AggregatedMatches` that groups matched products by `matched_product_image_link`.
  - [ ] Action: Within this grouping, use BigQuery array and struct functions to select the "hero" offer (e.g., ordering by `distance ASC LIMIT 1`) to represent the top-level `MatchedProduct` fields.
  - [ ] Action: Aggregate all variants within the group (including the hero itself, or optionally excluding it, but standard is including all) into an `ARRAY<STRUCT>` named `variants` containing `variant_offer_id`, `variant_title`, and `variant_brand`.
  - [ ] Action: Verify that the final `AggregatedMatches` array correctly maps the newly nested `variants` structure into the final JSON output.

- [ ] Task: Conductor - User Manual Verification 'Phase 1: BigQuery and Backend Data Models' (Protocol in workflow.md)

## Phase 2: Frontend Data Models and Dashboard UI

- [ ] Task: Update Frontend Data Models
  - [ ] Action: Modify the TypeScript interfaces (e.g., `src/webapp/frontend/src/app/models/product.model.ts` or similar) to match the updated backend model, adding the `variants` array of objects to `MatchedProduct`.

- [ ] Task: Implement Variants UI Display
  - [ ] Action: Modify the Angular template responsible for rendering matched products (e.g., `MatchedProductCardComponent` or `MatchListComponent`).
  - [ ] Action: Render the "hero" product details as the primary visual.
  - [ ] Action: Add a visual indicator (like a badge or secondary text) if `variants.length > 1`, displaying the text "+X variants".
  - [ ] Action: Implement a click handler for this indicator that opens a modal or expansion panel showing the list of `variant_title` and `variant_offer_id` from the `variants` array.

- [ ] Task: Conductor - User Manual Verification 'Phase 2: Frontend Data Models and Dashboard UI' (Protocol in workflow.md)

## Phase 3: Export Logic Verification

- [ ] Task: Verify/Update Google Ads Export Logic
  - [ ] Action: Trace the logic for "selecting a product to push to Ads" in the frontend. Ensure that when a user selects a product row, only the `matched_product_offer_id` of the *selected* item (the hero offer, unless the modal allows selecting individual variants) is passed to the export action.
  - [ ] Action: Confirm the backend export handler only processes the single `offer_id` provided and does not automatically iterate over the `variants` array. Add backend unit tests to verify this specific isolation if necessary.

- [ ] Task: Conductor - User Manual Verification 'Phase 3: Export Logic Verification' (Protocol in workflow.md)
