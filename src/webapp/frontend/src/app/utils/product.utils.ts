// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import {IdentifiedProduct, MatchedProduct} from '../models';

/**
 * Checks if the product brand is at the beginning of the product title.
 * @param match The MatchedProduct to check.
 * @return True if the brand is at the start of the title, false otherwise.
 */
export function isBrandAtStart(match: MatchedProduct): boolean {
  if (!match.matchedProductBrand || !match.matchedProductTitle) {
    return false;
  }
  return match.matchedProductTitle
    .toLowerCase()
    .startsWith(match.matchedProductBrand.toLowerCase());
}

/**
 * Extracts the brand part from the product title if the brand is at the start.
 * @param match The MatchedProduct to extract from.
 * @return The brand part of the title, or an empty string if the brand is not at the start.
 */
export function getBrandPart(match: MatchedProduct): string {
  if (!isBrandAtStart(match)) {
    return '';
  }
  return match.matchedProductTitle.slice(0, match.matchedProductBrand.length);
}

/**
 * Gets the rest of the product title after the brand, if the brand is at the start.
 * @param match The MatchedProduct to process.
 * @return The part of the title after the brand, or the full title if the brand is not at the start.
 */
export function getTitleRest(match: MatchedProduct): string {
  if (!isBrandAtStart(match)) {
    return match.matchedProductTitle;
  }
  return match.matchedProductTitle.slice(match.matchedProductBrand.length);
}

/**
 * Processes an IdentifiedProduct to remove duplicate matched products
 * and sort the remaining unique matches by distance in descending order.
 * @param product The IdentifiedProduct to process.
 * @return A new IdentifiedProduct with unique and sorted matched products.
 */
export function processIdentifiedProduct(
  product: IdentifiedProduct
): IdentifiedProduct {
  const uniqueMatches = new Map<string, MatchedProduct>();

  if (product.matchedProducts) {
    product.matchedProducts.forEach((match) => {
      if (!uniqueMatches.has(match.matchedProductOfferId)) {
        uniqueMatches.set(match.matchedProductOfferId, match);
      }
    });
  }

  return {
    ...product,
    matchedProducts: Array.from(uniqueMatches.values()).sort(
      (a, b) => a.distance - b.distance
    ),
  };
}

/**
 * Returns the Material Icon name based on the product status.
 * @param status The status string (e.g., 'Pending', 'Completed').
 * @return The Material Icon name, or an empty string if no matching icon is found.
 */
export function getStatusIcon(status: string | undefined | null): string {
  if (!status) {
    return '';
  }
  const s = status.toLowerCase();

  if (s === 'pending') {
    return 'hourglass_empty';
  }
  if (s === 'completed') {
    return 'check_circle';
  }
  if (s === 'failed') {
    return 'error';
  }
  if (s === 'disapproved') {
    return 'cancel';
  }
  if (s === 'unreviewed') {
    return 'help';
  }

  return '';
}

/**
 * Returns a CSS class name based on the product status.
 * This is used to style elements based on the status of a product.
 * @param status The status string of the product.
 * @return A CSS class name.
 */
export function getStatusClass(status: string | undefined | null): string {
  if (!status) {
    return '';
  }
  const s = status.toLowerCase();

  if (s === 'pending') {
    return 'status-pending';
  }
  if (s === 'completed') {
    return 'status-success';
  }
  if (s === 'failed') {
    return 'status-error';
  }
  if (s === 'disapproved') {
    return 'status-error';
  }

  return 'status-neutral';
}
