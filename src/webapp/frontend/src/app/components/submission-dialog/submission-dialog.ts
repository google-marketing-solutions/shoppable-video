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

import {Component, Inject, OnInit, Optional} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MAT_DIALOG_DATA, MatDialogModule} from '@angular/material/dialog';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {AuthService} from '../../services/auth.service';

/**
 * Interface defining the shape of the data injected into the SubmissionDialogComponent.
 * It contains all the necessary information to display and process a submission request,
 * such as the video and offer identifiers, destinations, and the submitting user.
 */
export interface SubmissionDialogData {
  videoUuid: string;
  offerIds: string;
  destinations: string;
  submittingUser: string;
}

/**
 * Component for displaying a dialog to approve or reject a video request.
 * It shows details about the request, including video UUID, offer IDs,
 * destinations, and the submitting user, and allows for user interaction
 * to finalize the submission process.
 */
@Component({
  selector: 'app-submission-dialog',
  standalone: true,
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatChipsModule,
    FormsModule,
  ],
  templateUrl: './submission-dialog.html',
  styleUrls: ['./submission-dialog.scss'],
})
export class SubmissionDialogComponent implements OnInit {
  data: SubmissionDialogData;
  constructor(
    @Optional()
    @Inject(MAT_DIALOG_DATA)
    public dialogData: Partial<SubmissionDialogData>,
    private authService: AuthService
  ) {
    this.data = {
      videoUuid: '',
      offerIds: '',
      destinations: '',
      submittingUser: '',
      ...dialogData,
    };
  }

  get offerIdList(): string[] {
    if (!this.data.offerIds) return [];
    return this.data.offerIds
      .split(',')
      .map((id) => id.trim())
      .filter((id) => id.length > 0);
  }

  ngOnInit() {
    if (!this.data.submittingUser) {
      this.data.submittingUser = this.authService.user()?.email || '';
    }
  }
}
