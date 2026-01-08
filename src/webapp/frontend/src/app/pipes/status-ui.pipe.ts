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
import {MatchedProduct, Status} from '../models';
import {getStatusClass, getStatusIcon} from '../utils/product.utils';

/**
 * A pipe that transforms a product or status into a Material Icon name
 * representing the status. Useful for displaying status icons in templates.
 */
@Pipe({
  name: 'statusIcon',
  standalone: true,
})
export class StatusIconPipe implements PipeTransform {
  transform(value: MatchedProduct | Status | string): string {
    if (typeof value === 'string') {
      return getStatusIcon(value);
    }
    return getStatusIcon(value.status);
  }
}

/**
 * A pipe that transforms a product or status into a CSS class name
 * suitable for styling elements based on the status.
 */
@Pipe({
  name: 'statusClass',
  standalone: true,
})
export class StatusClassPipe implements PipeTransform {
  transform(value: MatchedProduct | Status | string): string {
    if (typeof value === 'string') {
      return getStatusClass(value);
    }
    return getStatusClass(value.status);
  }
}
