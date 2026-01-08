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

import {Pipe, PipeTransform} from '@angular/core';
import {MatchedProduct} from '../models';
import {
  getBrandPart,
  getTitleRest,
  isBrandAtStart,
} from '../utils/product.utils';

/**
 * A pipe that extracts the brand part from a `MatchedProduct`.
 * Useful for displaying the brand separately in templates.
 */
@Pipe({
  name: 'brandPart',
  standalone: true,
})
export class BrandPipe implements PipeTransform {
  transform(value: MatchedProduct): string {
    return getBrandPart(value);
  }
}

/**
 * A pipe that extracts the rest of the title after the brand from a `MatchedProduct`.
 * Useful for displaying the product title without the leading brand in templates.
 */
@Pipe({
  name: 'titleRest',
  standalone: true,
})
export class TitleRestPipe implements PipeTransform {
  transform(value: MatchedProduct): string {
    return getTitleRest(value);
  }
}

/**
 * A pipe that checks if the brand is at the start of the title in a `MatchedProduct`.
 * Useful for conditionally styling or displaying product information based on brand placement.
 */
@Pipe({
  name: 'isBrandAtStart',
  standalone: true,
})
export class IsBrandAtStartPipe implements PipeTransform {
  transform(value: MatchedProduct): boolean {
    return isBrandAtStart(value);
  }
}
