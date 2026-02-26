# Track: Handle and group product variants

## Objective

Update the Shoppable Video Accelerator to consolidate product variants directly in the BigQuery backend. Variants are defined as matched products that share the same `product_image_link` (e.g., shirts of the same color but different sizes). Consolidating these variants simplifies the web app UI, as Google Ads considers multiple offers with the same image URL as one valid offer.

## Core Requirements

1. **Backend SQL Aggregation:**
    - Modify the BigQuery SQL query (`src/webapp/backend/app/services/queries/get_video_analysis.sql`).
    - If variants (products with the same `matched_product_image_link`) are identified for a given Identified Product, group them.
    - Pick a "hero" offer (the variant with the shortest distance/highest similarity) to represent the group.
    - Store the variant details in a new repeated object field in the `MatchedProduct` model called `variants`. This array should contain `variant_offer_id`, `variant_title`, and `variant_brand` for all matched variants in that group.

2. **Backend Data Model Update:**
    - Update the `MatchedProduct` Pydantic model (`src/webapp/backend/app/models/product.py`) to include the new `variants` list.

3. **Frontend Data Model and UI:**
    - Update the Angular data models to expect the new `variants` array on matched products.
    - Instead of presenting all variants as separate rows/cards, show only the "hero" variant.
    - Add a visual indicator (e.g., a badge saying "+X variants") to show that the offer has other matched variants.
    - Add an interaction (e.g., a clickable link or button) that opens a modal displaying the list of identified variants.

4. **Google Ads Export Logic:**
    - Ensure that when a product is selected and pushed to Google Ads, **only the specific selected product** (e.g., the hero offer) is included in the export. It should **not** automatically include all of its variants.

## Out of Scope

- Grouping by attributes other than the `product_image_link` (e.g., grouping by title or brand alone is out of scope).
- Modifying the underlying Vector Search or Gemini identification logic. The grouping happens strictly during the BigQuery retrieval phase.

## Context & Dependencies

- **Backend:** `src/webapp/backend/app/services/queries/get_video_analysis.sql`, `src/webapp/backend/app/models/product.py`.
- **Frontend:** Angular components responsible for displaying the list of matched products and handling the Ads export selection.
