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
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  TemplateRef,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {MatButtonModule} from '@angular/material/button';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatDialog, MatDialogModule} from '@angular/material/dialog';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatSlideToggleModule} from '@angular/material/slide-toggle';
import {MatSnackBar, MatSnackBarModule} from '@angular/material/snack-bar';
import {MatTableModule} from '@angular/material/table';
import {MatTooltipModule} from '@angular/material/tooltip';
import {DomSanitizer} from '@angular/platform-browser';
import {ActivatedRoute} from '@angular/router';
import {BehaviorSubject, combineLatest, of} from 'rxjs';
import {catchError, map, startWith, switchMap} from 'rxjs/operators';

import {
  IdentifiedProduct,
  MatchedProduct,
  Status,
  SubmissionMetadata,
  VideoAnalysis,
} from '../../models';
import {
  BrandPipe,
  IsBrandAtStartPipe,
  TitleRestPipe,
} from '../../pipes/product-display.pipe';
import {StatusClassPipe, StatusIconPipe} from '../../pipes/status-ui.pipe';
import {VideoTitlePipe} from '../../pipes/video-display.pipe';
import {DataService} from '../../services/data.service';
import {ProductSelectionService} from '../../services/product-selection.service';
import {processIdentifiedProduct} from '../../utils/product.utils';
import {StatusFooterComponent} from '../status-footer/status-footer';
import {
  SubmissionDialogComponent,
  SubmissionDialogData,
} from '../submission-dialog/submission-dialog';

/**
 * Component for displaying the details of a single video analysis.
 * It shows the video player, a table of identified products, and their matching status.
 * Users can interact with the product selections.
 */
@Component({
  selector: 'app-video-details',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatSlideToggleModule,
    MatButtonModule,
    MatDialogModule,
    MatCheckboxModule,
    MatIconModule,
    MatSnackBarModule,
    MatDialogModule,
    MatTooltipModule,
    StatusFooterComponent,
    StatusIconPipe,
    StatusClassPipe,
    BrandPipe,
    TitleRestPipe,
    IsBrandAtStartPipe,
    VideoTitlePipe,
  ],
  templateUrl: './video-details.html',
  styleUrls: ['./video-details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [ProductSelectionService],
})
export class VideoDetails {
  private route = inject(ActivatedRoute);
  private dataService = inject(DataService);
  private cdr = inject(ChangeDetectorRef);
  private sanitizer = inject(DomSanitizer);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);
  selectionService = inject(ProductSelectionService);

  displayedColumns: string[] = [
    'select',
    'status',
    'image',
    'offerId',
    'matchTitle',
    'availability',
  ];

  hideNoMatches = signal(true);
  selectedImageUrl = signal<string | null>(null);
  refreshMatches = signal(0);

  private videoState$ = this.route.paramMap.pipe(
    switchMap((params) => {
      const id = params.get('videoAnalysisUuid');

      if (!id || id === 'undefined') {
        return of({
          data: undefined,
          loading: false,
          error: 'Invalid or missing Video ID',
        });
      }

      const request$ = this.dataService.getVideoAnalysis(id);

      return request$.pipe(
        map((response) => {
          const video = Array.isArray(response) ? response[0] : response;

          if (video && video.identifiedProducts) {
            video.identifiedProducts = video.identifiedProducts.map(
              processIdentifiedProduct
            );
          }

          return {data: video, loading: false, error: null};
        }),
        startWith({
          data: undefined as VideoAnalysis | undefined,
          loading: true,
          error: null,
        }),
        catchError(() => {
          return of({
            data: undefined,
            loading: false,
            error: 'Failed to load video data',
          });
        })
      );
    })
  );

  state = toSignal(this.videoState$, {
    initialValue: {data: undefined, loading: true, error: null},
  });

  refreshInsertionStatuses$ = new BehaviorSubject<void>(void 0);

  private insertionStatusesState = toSignal(
    combineLatest([this.route.paramMap, this.refreshInsertionStatuses$]).pipe(
      switchMap(([params]) => {
        const id = params.get('videoAnalysisUuid');
        if (!id || id === 'undefined') {
          return of({data: [], loading: false, error: null});
        }
        return this.dataService.getAdGroupInsertionStatusesForVideo(id).pipe(
          map((data) => ({data, loading: false, error: null})),
          startWith({data: [], loading: true, error: null}),
          catchError((err) => {
            console.error('Error loading insertion statuses', err);
            return of({
              data: [],
              loading: false,
              error: 'Failed to load statuses',
            });
          })
        );
      })
    ),
    {initialValue: {data: [], loading: true, error: null}}
  );

  insertionStatuses = computed(() => this.insertionStatusesState().data ?? []);
  isRefreshingInsertionStatuses = computed(
    () => this.insertionStatusesState().loading
  );

  successfulOfferIds = computed(() => {
    const statuses = this.insertionStatuses();
    const ids = new Set<string>();
    if (!statuses) return ids;

    for (const status of statuses) {
      for (const entity of status.adsEntities) {
        for (const product of entity.products) {
          if (product.status === 'success') {
            ids.add(product.offerId);
          }
        }
      }
    }
    return ids;
  });

  private adGroupsState = toSignal(
    this.videoState$.pipe(
      switchMap((state) => {
        const video = state.data;
        if (
          state.loading ||
          !video ||
          !video.video ||
          video.video.source !== 'google_ads'
        ) {
          return of({data: [], loading: false, error: null});
        }

        const id = video.video.uuid;
        return this.dataService.getAdGroupsForVideo(id).pipe(
          map((data) => ({data, loading: false, error: null})),
          startWith({data: [], loading: true, error: null}),
          catchError((err) => {
            console.error('Error loading ad groups', err);
            return of({
              data: [],
              loading: false,
              error: 'Failed to load ad groups',
            });
          })
        );
      })
    ),
    {initialValue: {data: [], loading: false, error: null}}
  );

  adGroups = computed(() => this.adGroupsState().data ?? []);
  isLoadingAdGroups = computed(() => this.adGroupsState().loading);

  isButtonBusy = computed(
    () => this.isRefreshingInsertionStatuses() || this.isLoadingAdGroups()
  );

  hasProcessableOffers = computed(() => {
    const matches = this.approvedMatches();
    const adGroups = this.adGroups();
    const video = this.video();

    if (matches.length === 0) return false;

    if (video?.video?.source === 'google_ads' && adGroups.length === 0) {
      return false;
    }

    return true;
  });

  video = computed(() => this.state().data);
  loading = computed(() => this.state().loading);
  error = computed(() => this.state().error);

  @ViewChild('youtubeIframe') youtubeIframe:
    | ElementRef<HTMLIFrameElement>
    | undefined;

  @ViewChild('gcsVideo') gcsVideo: ElementRef<HTMLVideoElement> | undefined;

  dataSource = computed(() => {
    const video = this.video();
    const hideNoMatches = this.hideNoMatches();

    if (!video || !video.identifiedProducts) return [];

    let products = video.identifiedProducts;

    if (hideNoMatches) {
      products = products.filter(
        (p: IdentifiedProduct) =>
          p.matchedProducts && p.matchedProducts.length > 0
      );
    }

    return products;
  });

  youtubeUrl = computed(() => {
    const video = this.video();
    if (video?.video?.videoId) {
      const url = `https://www.youtube.com/embed/${video.video.videoId}?enablejsapi=1`;
      return this.sanitizer.bypassSecurityTrustResourceUrl(url);
    }
    return null;
  });

  gcsVideoUrl = computed(() => {
    const video = this.video();
    if (video?.video?.gcsUri) {
      let url = video.video.gcsUri;
      if (url.startsWith('gs://')) {
        url = url.replace('gs://', 'https://storage.cloud.google.com/');
      }
      return this.sanitizer.bypassSecurityTrustResourceUrl(url);
    }
    return null;
  });

  approvedMatches = computed(() => {
    this.refreshMatches();
    const video = this.video();
    if (!video || !video.identifiedProducts) return [];

    // Flatten all matches that are APPROVED
    return video.identifiedProducts.flatMap((product: IdentifiedProduct) =>
      (product.matchedProducts || [])
        .filter((match) => match.status === Status.APPROVED)
        .map((match) => ({product, match}))
    );
  });

  constructor() {
    this.selectionService.statusUpdated$.subscribe(() => {
      this.refreshMatches.update((count) => count + 1);
      this.cdr.markForCheck();
    });
  }

  isOfferInserted(offerId: string): boolean {
    return this.successfulOfferIds().has(offerId);
  }

  isAllSelected(product: IdentifiedProduct): boolean {
    const video = this.video();
    if (!video || !product.matchedProducts?.length) return false;
    return product.matchedProducts.every((match) =>
      this.selectionService.isSelected(video, match)
    );
  }

  isSomeSelected(product: IdentifiedProduct): boolean {
    const video = this.video();
    if (!video || !product.matchedProducts?.length) return false;
    return product.matchedProducts.some((match) =>
      this.selectionService.isSelected(video, match)
    );
  }

  toggleAll(product: IdentifiedProduct): void {
    const video = this.video();
    if (!video || !product.matchedProducts?.length) return;

    const allSelected = this.isAllSelected(product);
    product.matchedProducts.forEach((match) => {
      const isSelected = this.selectionService.isSelected(video, match);
      if (allSelected && isSelected) {
        this.selectionService.toggleSelection(
          video,
          product.productUuid,
          match
        );
      } else if (!allSelected && !isSelected) {
        this.selectionService.toggleSelection(
          video,
          product.productUuid,
          match
        );
      }
    });
  }

  formatTimestamp(ms: number): string {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }

  jumpToTimestamp(ms: number) {
    const seconds = ms / 1000;
    if (this.youtubeIframe?.nativeElement?.contentWindow) {
      this.youtubeIframe.nativeElement.contentWindow.postMessage(
        JSON.stringify({
          event: 'command',
          func: 'seekTo',
          args: [seconds, true],
        }),
        '*'
      );
    } else if (this.gcsVideo?.nativeElement) {
      this.gcsVideo.nativeElement.currentTime = seconds;
      this.gcsVideo.nativeElement.play(); // TODO: decide whether we want vid to play on seek
    }
  }

  copyToClipboard(text: string) {
    navigator.clipboard.writeText(text).then(
      () => {
        this.snackBar.open(`Copied ${text} to clipboard`, 'Close', {
          duration: 3000,
          horizontalPosition: 'center',
          verticalPosition: 'bottom',
        });
      },
      (err) => {
        console.error('Could not copy text: ', err);
        this.snackBar.open('Failed to copy to clipboard', 'Close', {
          duration: 3000,
        });
      }
    );
  }

  onUpdateStatus(event: Status | {status: Status; data: SubmissionDialogData}) {
    let status: Status;
    let extraData: SubmissionDialogData | undefined;

    if (typeof event === 'string') {
      status = event;
    } else {
      status = event.status;
      extraData = event.data;
    }

    this.selectionService
      .updateStatus(status, extraData)
      .subscribe((success) => {
        if (success) {
          this.snackBar.open('Status updated successfully', 'Close', {
            duration: 3000,
          });
        } else {
          this.snackBar.open('Failed to update status', 'Close', {
            duration: 3000,
          });
        }
      });
  }

  openImageDialog(imageUrl: string, templateRef: TemplateRef<unknown>) {
    this.selectedImageUrl.set(imageUrl);
    this.dialog.open(templateRef, {
      maxWidth: '90vw',
      maxHeight: '90vh',
      panelClass: 'image-modal-panel',
    });
  }

  openSubmissionDialog() {
    const videoId = this.video()?.video?.uuid;
    const matches = this.approvedMatches();

    if (!videoId || matches.length === 0) return;

    const dialogRef = this.dialog.open(SubmissionDialogComponent, {
      width: '500px',
      data: {
        videoUuid: videoId,
        offerIds: matches
          .map(
            (m: {product: IdentifiedProduct; match: MatchedProduct}) =>
              m.match.matchedProductOfferId
          )
          .join(', '),
        insertionStatuses: this.insertionStatuses(),
        videoSource: this.video()?.video?.source,
      },
    });

    dialogRef
      .afterClosed()
      .subscribe((result: SubmissionMetadata[] | undefined) => {
        if (result && Array.isArray(result) && result.length > 0) {
          this.pushToGoogleAds(result);
        }
      });
  }

  private pushToGoogleAds(submissionRequests: SubmissionMetadata[]) {
    this.dataService.insertSubmissionRequests(submissionRequests).subscribe({
      next: () => {
        this.snackBar.open(
          'Push to Google Ads initiated successfully',
          'Close',
          {duration: 3000}
        );
        this.refreshInsertionStatuses$.next();
      },
      error: () => {
        this.snackBar.open('Failed to push to Google Ads', 'Close', {
          duration: 3000,
        });
      },
    });
  }
}
