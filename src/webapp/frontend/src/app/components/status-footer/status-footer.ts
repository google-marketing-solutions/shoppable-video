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

import {CommonModule} from '@angular/common';
import {Component, EventEmitter, Input, Output} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatSelectModule} from '@angular/material/select';
import {Status} from '../../models';

/**
 * The StatusFooterComponent provides a footer with controls to update the status
 * of selected items. It displays the number of selected items and allows the user
 * to choose a new status from a dropdown and apply the update.
 */
@Component({
  selector: 'app-status-footer',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatSelectModule,
    MatFormFieldModule,
    FormsModule,
  ],
  templateUrl: './status-footer.html',
  styleUrls: ['./status-footer.scss'],
})
export class StatusFooterComponent {
  @Input() selectionCount = 0;
  @Output() readonly update = new EventEmitter<Status>();

  statusOptions = Object.values(Status);
  selectedStatus: Status | '' = '';

  onUpdate() {
    if (this.selectedStatus) {
      this.update.emit(this.selectedStatus);
    }
  }
}
