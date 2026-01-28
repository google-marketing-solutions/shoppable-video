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
import {MatDialog} from '@angular/material/dialog';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatSelectModule} from '@angular/material/select';
import {Status} from '../../models';
import {MatchedProductSelection} from '../../services/product-selection.service';
import {
  SubmissionDialogComponent,
  SubmissionDialogData,
} from '../submission-dialog/submission-dialog';

/**
 * Component for displaying a status footer with options to update the status
 * of selected items. When the "APPROVED" status is selected, it opens an
 * submission dialog.
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
  @Input() videoUuid: string | undefined;
  @Input() selectionCount = 0;
  @Input() selectedMatches: MatchedProductSelection[] = [];
  @Output() readonly update = new EventEmitter<
    Status | {status: Status; data: SubmissionDialogData}
  >();

  statusOptions = Object.values(Status);
  selectedStatus: Status | '' = '';

  constructor(private dialog: MatDialog) {}

  onUpdate() {
    if (this.selectedStatus) {
      if (this.selectedStatus === Status.APPROVED) {
        const dialogRef = this.dialog.open(SubmissionDialogComponent, {
          width: '500px',
          data: {
            videoUuid: this.videoUuid,
            offerIds: this.selectedMatches
              .map((m) => m.match.matchedProductOfferId)
              .join(', '),
          },
        });

        dialogRef
          .afterClosed()
          .subscribe((result: SubmissionDialogData | undefined) => {
            if (result) {
              this.update.emit({
                status: Status.APPROVED,
                data: result,
              });
            }
          });
      } else {
        this.update.emit(this.selectedStatus);
      }
    }
  }
}
