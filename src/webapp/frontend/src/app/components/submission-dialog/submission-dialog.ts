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

import {
  ChangeDetectorRef,
  Component,
  Inject,
  OnInit,
  Optional,
  inject,
} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {MatSelectModule} from '@angular/material/select';
import {AdGroupInsertionStatus, Destination} from '../../models';
import {AuthService} from '../../services/auth.service';
import {DataService} from '../../services/data.service';

/**
 * Interface defining the shape of the data injected into the SubmissionDialogComponent.
 * It contains all the necessary information to display and process a submission request,
 * such as the video and offer identifiers, destinations, and the submitting user.
 */
export interface SubmissionDialogData {
  videoUuid: string;
  offerIds: string;
  destinations: Destination[];
  submittingUser: string;
  cpc?: number;
  insertionStatuses?: AdGroupInsertionStatus[];
}

interface SubmissionRequest {
  videoUuid: string;
  offerIds: string;
  destinations: Destination[];
  submittingUser: string;
  cpc?: number;
}

interface AdGroupOption {
  id: string;
  name: string;
  status: string;
  campaignId: string;
  customerId: string;
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
    MatSelectModule,
    FormsModule,
  ],
  templateUrl: './submission-dialog.html',
  styleUrls: ['./submission-dialog.scss'],
})
export class SubmissionDialogComponent implements OnInit {
  data: SubmissionDialogData;
  adGroupOptions: AdGroupOption[] = [];
  selectedDestinations: Destination[] = [];
  isLoadingAdGroups = false;

  private dataService = inject(DataService);
  cdr = inject(ChangeDetectorRef);

  constructor(
    @Optional()
    @Inject(MAT_DIALOG_DATA)
    public dialogData: Partial<SubmissionDialogData>,
    private authService: AuthService,
    private dialogRef: MatDialogRef<SubmissionDialogComponent>
  ) {
    this.data = {
      videoUuid: '',
      offerIds: '',
      destinations: [],
      submittingUser: '',
      cpc: undefined,
      ...dialogData,
    };

    if (this.data.destinations && Array.isArray(this.data.destinations)) {
      this.selectedDestinations = [...this.data.destinations];
    }
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

    if (this.data.videoUuid) {
      this.isLoadingAdGroups = true;
      this.dataService.getAdGroupsForVideo(this.data.videoUuid).subscribe({
        next: (adGroups) => {
          this.adGroupOptions = adGroups.map((ag) => ({
            id: ag.id,
            name: ag.name,
            status: ag.status,
            campaignId: ag.campaign_id,
            customerId: ag.customer_id,
          }));
          this.isLoadingAdGroups = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          console.error('Failed to fetch ad groups', err);
          this.isLoadingAdGroups = false;
          this.cdr.markForCheck();
        },
      });
    }
  }

  onAdGroupSelectionChange() {
    this.data.destinations = this.selectedDestinations;
  }

  compareDestinations(o1: Destination, o2: Destination): boolean {
    return o1.adGroupId === o2.adGroupId && o1.campaignId === o2.campaignId;
  }

  submit() {
    if (!this.selectedDestinations.length) return;

    const offerIds = this.offerIdList;
    if (!offerIds.length) return;

    const sortedOfferIds = offerIds.sort().join(',');

    const submissionRequests: SubmissionRequest[] = [
      {
        videoUuid: this.data.videoUuid,
        offerIds: sortedOfferIds,
        destinations: this.selectedDestinations,
        submittingUser: this.data.submittingUser,
        cpc: this.data.cpc,
      },
    ];

    this.dialogRef.close(submissionRequests);
  }
}
