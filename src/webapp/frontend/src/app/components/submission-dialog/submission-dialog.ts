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
import {
  ChangeDetectorRef,
  Component,
  Inject,
  OnInit,
  Optional,
  inject,
} from '@angular/core';
import {FormsModule, NgForm} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatChipsModule} from '@angular/material/chips';
import {MatOptionSelectionChange} from '@angular/material/core';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatSelectModule} from '@angular/material/select';
import {MatSnackBar, MatSnackBarModule} from '@angular/material/snack-bar';
import {
  AdGroupInsertionStatus,
  Destination,
  Customer,
  LinkedVideoDestination,
  Campaign,
} from '../../models';
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
  videoSource?: string;
  videoId?: string;
}

interface SubmissionRequest {
  videoUuid: string;
  offerIds: string;
  destinations: Destination[];
  submittingUser: string;
  cpc?: number;
}

interface CampaignOption {
  id: number;
  name: string;
}

interface AdGroupOption {
  id: number;
  name: string;
  status: string;
  campaignId: number;
  customerId: number;
}

interface ManualDestination {
  customerId: number | null;
  customerSearch: string;
  campaignId: number | null;
  campaignSearch: string;
  adGroupId: number | null;
  adGroupSearch: string;
  campaignOptions: CampaignOption[];
  adGroupOptions: AdGroupOption[];
  isLoadingCampaigns: boolean;
  isLoadingAdGroups: boolean;
  isLoadingLinkedVideos?: boolean;
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
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatChipsModule,
    MatSelectModule,
    MatCheckboxModule,
    MatIconModule,
    MatAutocompleteModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  templateUrl: './submission-dialog.html',
  styleUrls: ['./submission-dialog.scss'],
})
export class SubmissionDialogComponent implements OnInit {
  // Data and State
  data: SubmissionDialogData;
  selectedDestinations: Destination[] = [];
  manualDestinations: ManualDestination[] = [this.createEmptyDestination()];
  accessibleCustomers: Customer[] = [];
  queriedCustomerIds = new Set<number>();

  // UI State
  isLoadingAccounts = false;
  useDefaultCpc = true;

  // Services
  private dataService = inject(DataService);
  private authService = inject(AuthService);
  private snackBar = inject(MatSnackBar);
  private dialogRef = inject(MatDialogRef<SubmissionDialogComponent>);
  cdr = inject(ChangeDetectorRef);

  constructor(
    @Optional()
    @Inject(MAT_DIALOG_DATA)
    public dialogData: Partial<SubmissionDialogData>
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

    if (this.data.cpc !== undefined) {
      this.useDefaultCpc = false;
    }
  }

  ngOnInit() {
    this.initializeSubmittingUser();
    this.loadAccessibleAccounts();
  }

  /**
   * Returns a list of unique destinations where this video has already been pushed.
   */
  get previousPushes(): Array<{account: string; adGroup: string}> {
    const pushes: Array<{account: string; adGroup: string}> = [];
    const seen = new Set<string>();

    if (this.data.insertionStatuses) {
      for (const status of this.data.insertionStatuses) {
        for (const entity of status.adsEntities) {
          const key = `${entity.customerId}-${entity.adGroupId}`;
          if (!seen.has(key)) {
            seen.add(key);
            pushes.push({
              account: String(entity.customerId),
              adGroup: String(entity.adGroupId),
            });
          }
        }
      }
    }
    return pushes;
  }

  /**
   * Returns a list of unique offer IDs from the input comma-separated string.
   */
  get offerIdList(): string[] {
    if (!this.data.offerIds) return [];
    return this.data.offerIds
      .split(',')
      .map((id) => id.trim())
      .filter((id) => id.length > 0);
  }

  /**
   * Finalizes the submission process and closes the dialog with the collected data.
   */
  submit() {
    const validManualDestinations = this.manualDestinations.filter(
      (d) =>
        d.campaignId !== null && d.adGroupId !== null && d.customerId !== null
    );

    if (!validManualDestinations.length) return;

    const destinations: Destination[] = validManualDestinations.map((d) => {
      const selectedAdGroup = d.adGroupOptions?.find(
        (ag) => ag.id === d.adGroupId
      );
      return {
        campaignId: d.campaignId!,
        adGroupId: d.adGroupId!,
        customerId: selectedAdGroup?.customerId || d.customerId!,
        adGroupName: selectedAdGroup?.name || `Manual AdGroup ${d.adGroupId}`,
      };
    });

    const offerIds = this.offerIdList;
    if (!offerIds.length) return;

    const sortedOfferIds = offerIds.sort().join(',');

    const submissionRequests: SubmissionRequest[] = [
      {
        videoUuid: this.data.videoUuid,
        offerIds: sortedOfferIds,
        destinations,
        submittingUser: this.data.submittingUser,
        cpc: this.useDefaultCpc ? undefined : this.data.cpc,
      },
    ];

    this.dialogRef.close(submissionRequests);
  }

  /**
   * Checks if the submit button should be disabled based on form validity and destination selection.
   * @param form The NgForm instance.
   * @return True if submission is disabled.
   */
  isSubmitDisabled(form: NgForm): boolean {
    if (form && !form.valid) return true;
    if (this.manualDestinations.length === 0) return true;
    return this.manualDestinations.some(
      (d) =>
        d.campaignId === null || d.adGroupId === null || d.customerId === null
    );
  }

  // --- Event Handlers (Customer) ---

  /**
   * Handles changes to the selected customer account, triggering auto-discovery of linked videos.
   * @param dest The manual destination row being updated.
   */
  onCustomerIdChange(dest: ManualDestination) {
    this.resetDependentFields(dest);

    if (!dest.customerId) return;

    if (this.data.videoId && !this.queriedCustomerIds.has(dest.customerId)) {
      this.performAutoDiscovery(dest);
    } else {
      this.fetchCampaignsForCustomer(dest);
    }
  }

  /**
   * Handles customer selection from the autocomplete dropdown.
   */
  onCustomerSelected(
    dest: ManualDestination,
    customer: Customer,
    event: MatOptionSelectionChange
  ) {
    if (!event.isUserInput) return;
    dest.customerId = customer.customer_id;
    dest.customerSearch = `${customer.descriptive_name} (${customer.customer_id})`;
    this.onCustomerIdChange(dest);
    this.cdr.markForCheck();
  }

  /**
   * Clears the selected customer and its dependent fields.
   * @param dest The manual destination row.
   */
  clearCustomer(dest: ManualDestination) {
    dest.customerId = null;
    dest.customerSearch = '';
    this.onCustomerIdChange(dest);
    this.cdr.markForCheck();
  }

  // --- Event Handlers (Campaign) ---

  /**
   * Handles campaign selection from the autocomplete dropdown.
   */
  onCampaignSelected(
    dest: ManualDestination,
    campaign: CampaignOption,
    event: MatOptionSelectionChange
  ) {
    if (!event.isUserInput) return;
    dest.campaignId = campaign.id;
    dest.campaignSearch = `${campaign.name} (${campaign.id})`;
    // Clear previous ad groups when a new campaign is picked
    this.clearAdGroup(dest, true);
    this.fetchAdGroups(dest);
    this.cdr.markForCheck();
  }

  /**
   * Clears the selected campaign and its dependent fields.
   * @param dest The manual destination row.
   */
  clearCampaign(dest: ManualDestination) {
    dest.campaignId = null;
    dest.campaignSearch = '';
    // Clear ad groups since they are tied to a specific campaign
    this.clearAdGroup(dest, true);
    this.cdr.markForCheck();
  }

  // --- Event Handlers (Ad Group) ---

  /**
   * Handles ad group selection from the autocomplete dropdown.
   */
  onAdGroupSelected(
    dest: ManualDestination,
    adGroup: AdGroupOption,
    event: MatOptionSelectionChange
  ) {
    if (!event.isUserInput) return;
    dest.adGroupId = adGroup.id;
    dest.adGroupSearch = `${adGroup.name} (${adGroup.id})`;
    this.cdr.markForCheck();
  }

  /**
   * Clears the selected ad group.
   * @param dest The manual destination row.
   * @param clearOptions Whether to also clear the list of available ad groups.
   */
  clearAdGroup(dest: ManualDestination, clearOptions = false) {
    dest.adGroupId = null;
    dest.adGroupSearch = '';
    if (clearOptions) {
      dest.adGroupOptions = [];
    }
    this.cdr.markForCheck();
  }

  // --- Data Fetching ---

  private loadAccessibleAccounts() {
    this.isLoadingAccounts = true;
    this.dataService.getSubAccounts(undefined, true).subscribe({
      next: (response) => {
        this.accessibleCustomers = response.data;
        this.handleAccountFallback();
        this.autoTriggerDiscoveryIfActiveAccountSet();
        this.isLoadingAccounts = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to fetch sub-accounts', err);
        this.isLoadingAccounts = false;
        this.cdr.markForCheck();
      },
    });
  }

  /**
   * Fetches available campaigns for the selected customer.
   * @param dest The manual destination row.
   */
  fetchCampaignsForCustomer(dest: ManualDestination) {
    dest.isLoadingCampaigns = true;
    this.dataService.getCampaigns(dest.customerId!).subscribe({
      next: (response) => {
        dest.campaignOptions = response.data.map((c: Campaign) => ({
          id: c.id,
          name: c.name,
        }));
        dest.isLoadingCampaigns = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to fetch campaigns', err);
        dest.isLoadingCampaigns = false;
        this.cdr.markForCheck();
      },
    });
  }

  /**
   * Fetches available ad groups for the selected campaign.
   * @param dest The manual destination row.
   */
  fetchAdGroups(dest: ManualDestination) {
    if (!dest.campaignId) return;

    dest.isLoadingAdGroups = true;
    this.dataService
      .getAdGroupsForCampaign(dest.campaignId, dest.customerId || undefined)
      .subscribe({
        next: (adGroups) => {
          dest.adGroupOptions = adGroups.map((ag) => ({
            id: ag.id,
            name: ag.name,
            status: ag.status,
            campaignId: ag.campaign_id,
            customerId: ag.customer_id,
          }));
          dest.isLoadingAdGroups = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          console.error('Failed to fetch ad groups for campaign', err);
          dest.isLoadingAdGroups = false;
          this.cdr.markForCheck();
        },
      });
  }

  private performAutoDiscovery(dest: ManualDestination) {
    this.queriedCustomerIds.add(dest.customerId!);
    dest.isLoadingLinkedVideos = true;
    this.dataService
      .getAdgroupsWithVideo(this.data.videoId!, dest.customerId!)
      .subscribe({
        next: (response) => {
          dest.isLoadingLinkedVideos = false;
          if (response.data && response.data.length > 0) {
            this.handleDiscoveryResults(dest, response.data);
          }
          this.fetchCampaignsForCustomer(dest);
        },
        error: (err) => {
          console.error('Failed to search for existing video links', err);
          dest.isLoadingLinkedVideos = false;
          this.fetchCampaignsForCustomer(dest);
        },
      });
  }

  // --- Filtering ---

  /**
   * Filters the list of accessible customers based on user search input.
   */
  getFilteredCustomers(dest: ManualDestination): Customer[] {
    if (!dest.customerSearch) return this.accessibleCustomers;
    const filterValue = dest.customerSearch.toLowerCase();
    return this.accessibleCustomers.filter(
      (option) =>
        option.descriptive_name.toLowerCase().includes(filterValue) ||
        String(option.customer_id).includes(filterValue)
    );
  }

  /**
   * Filters the list of available campaigns based on user search input.
   */
  getFilteredCampaigns(dest: ManualDestination): CampaignOption[] {
    if (!dest.campaignSearch) return dest.campaignOptions;
    const filterValue = dest.campaignSearch.toLowerCase();
    return dest.campaignOptions.filter(
      (option) =>
        option.name.toLowerCase().includes(filterValue) ||
        String(option.id).includes(filterValue)
    );
  }

  /**
   * Filters the list of available ad groups based on user search input.
   */
  getFilteredAdGroups(dest: ManualDestination): AdGroupOption[] {
    if (!dest.adGroupSearch) return dest.adGroupOptions;
    const filterValue = dest.adGroupSearch.toLowerCase();
    return dest.adGroupOptions.filter(
      (option) =>
        option.name.toLowerCase().includes(filterValue) ||
        String(option.id).includes(filterValue)
    );
  }

  // --- Row Management ---

  /**
   * Adds a new empty destination row to the form.
   */
  addManualRow() {
    this.manualDestinations.push(this.createEmptyDestination());
  }

  /**
   * Removes a destination row from the form at the specified index.
   */
  removeManualRow(index: number) {
    if (this.manualDestinations.length > 1) {
      this.manualDestinations.splice(index, 1);
    }
  }

  // --- Helpers ---

  private createEmptyDestination(): ManualDestination {
    return {
      customerId: null,
      customerSearch: '',
      campaignId: null,
      campaignSearch: '',
      adGroupId: null,
      adGroupSearch: '',
      campaignOptions: [],
      adGroupOptions: [],
      isLoadingCampaigns: false,
      isLoadingAdGroups: false,
    };
  }

  private resetDependentFields(dest: ManualDestination) {
    dest.campaignId = null;
    dest.campaignSearch = '';
    dest.adGroupId = null;
    dest.adGroupSearch = '';
    dest.campaignOptions = [];
    dest.adGroupOptions = [];
  }

  private initializeSubmittingUser() {
    if (!this.data.submittingUser) {
      this.data.submittingUser = this.authService.user()?.email || '';
    }
  }

  private handleAccountFallback() {
    // Fallback to active account itself if no sub-accounts are found (e.g. Standard account)
    const activeAccId = this.dataService.activeAccount();
    if (this.accessibleCustomers.length === 0 && activeAccId) {
      this.accessibleCustomers = [
        {
          customer_id: activeAccId,
          descriptive_name: `Active Account (${activeAccId})`,
          is_manager: false,
          is_platform_customer_id: false,
        },
      ];
    }
  }

  private autoTriggerDiscoveryIfActiveAccountSet() {
    const activeAccId = this.dataService.activeAccount();
    if (activeAccId && this.manualDestinations.length === 1) {
      const dest = this.manualDestinations[0];
      const match = this.accessibleCustomers.find(
        (c) => c.customer_id === activeAccId
      );
      if (match) {
        dest.customerId = match.customer_id;
        dest.customerSearch = `${match.descriptive_name} (${match.customer_id})`;
        this.onCustomerIdChange(dest);
      }
    }
  }

  private handleDiscoveryResults(
    dest: ManualDestination,
    results: LinkedVideoDestination[]
  ) {
    const first = results[0];
    dest.campaignId = first.campaign_id;
    dest.campaignSearch = `${first.campaign_name} (${first.campaign_id})`;
    dest.adGroupId = first.ad_group_id;
    dest.adGroupSearch = `${first.ad_group_name} (${first.ad_group_id})`;
    dest.campaignOptions = [{id: dest.campaignId, name: first.campaign_name}];
    dest.adGroupOptions = [
      {
        id: dest.adGroupId,
        name: first.ad_group_name,
        status: 'ENABLED',
        campaignId: dest.campaignId,
        customerId: dest.customerId!,
      },
    ];

    for (let i = 1; i < results.length; i++) {
      const match = results[i];
      this.manualDestinations.push({
        customerId: dest.customerId,
        customerSearch: dest.customerSearch,
        campaignId: match.campaign_id,
        campaignSearch: `${match.campaign_name} (${match.campaign_id})`,
        adGroupId: match.ad_group_id,
        adGroupSearch: `${match.ad_group_name} (${match.ad_group_id})`,
        campaignOptions: [{id: match.campaign_id, name: match.campaign_name}],
        adGroupOptions: [
          {
            id: match.ad_group_id,
            name: match.ad_group_name,
            status: 'ENABLED',
            campaignId: match.campaign_id,
            customerId: dest.customerId!,
          },
        ],
        isLoadingCampaigns: false,
        isLoadingAdGroups: false,
        isLoadingLinkedVideos: false,
      });
    }

    this.snackBar.open(
      `Pre-populated ${results.length} destination(s) based on existing video links.`,
      'Close',
      {duration: 5000}
    );
  }

  /**
   * Compares two destination objects for equality in mat-select.
   */
  compareDestinations(
    destination1: Destination,
    destination2: Destination
  ): boolean {
    return (
      destination1.adGroupId === destination2.adGroupId &&
      destination1.campaignId === destination2.campaignId
    );
  }
}
