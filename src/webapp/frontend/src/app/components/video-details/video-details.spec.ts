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

import {ElementRef} from '@angular/core';
import {ComponentFixture, TestBed} from '@angular/core/testing';
import {MatDialog} from '@angular/material/dialog';
import {ActivatedRoute, convertToParamMap} from '@angular/router';
import {BehaviorSubject, of, Subject, throwError} from 'rxjs';
import {AdGroupInsertionStatus, VideoAnalysis} from '../../models';
import {AuthService} from '../../services/auth.service';
import {DataService} from '../../services/data.service';
import {ProductSelectionService} from '../../services/product-selection.service';
import {SubmissionDialogComponent} from '../submission-dialog/submission-dialog';
import {VideoDetails} from './video-details';

interface MockUser {
  email: string;
}

describe('VideoDetails', () => {
  let component: VideoDetails;
  let fixture: ComponentFixture<VideoDetails>;
  let mockDataService: jasmine.SpyObj<DataService>;
  let mockSelectionService: jasmine.SpyObj<ProductSelectionService>;
  let mockDialog: jasmine.SpyObj<MatDialog>;
  let mockAuthService: jasmine.SpyObj<AuthService>;
  let mockActivatedRoute: Partial<ActivatedRoute>;

  const mockVideo: VideoAnalysis = {
    video: {
      uuid: 'uuid',
      source: 'manual',
      videoId: '123',
      gcsUri: 'gs://test',
      md5Hash: null,
    },
    identifiedProducts: [
      {
        title: 'Test Product',
        description: 'Desc',
        relevanceReasoning: 'Reason',
        productUuid: 'p_uuid',
        videoTimestamp: 1000,
        matchedProducts: [
          {
            matchedProductOfferId: 'offer1',
            distance: 0.5,
            matchedProductTitle: 'Match',
            matchedProductBrand: 'Brand',
            timestamp: '',
            status: 'APPROVED',
          },
        ],
      },
    ],
  };

  beforeEach(async () => {
    mockDataService = jasmine.createSpyObj('DataService', [
      'getVideoAnalysis',
      'updateCandidates',
      'insertSubmissionRequests',
      'getAdGroupsForVideo',
      'getAdGroupInsertionStatusesForVideo',
    ]);
    mockSelectionService = jasmine.createSpyObj(
      'ProductSelectionService',
      ['toggleSelection', 'isSelected', 'updateStatus', 'getSelectedItems'],
      {
        statusUpdated$: new Subject<void>(),
        matchedProductSelection: {
          selected: [],
          hasValue: () => false,
        },
      }
    );
    mockDialog = jasmine.createSpyObj('MatDialog', ['open']);
    mockAuthService = jasmine.createSpyObj('AuthService', ['user'], {
      user: signal({email: 'test@example.com'} as MockUser),
    });

    const paramMapSubject = new BehaviorSubject(
      convertToParamMap({
        videoAnalysisUuid: 'uuid',
      })
    );
    mockActivatedRoute = {paramMap: paramMapSubject.asObservable()};

    await TestBed.configureTestingModule({
      imports: [VideoDetails],
      providers: [
        {provide: DataService, useValue: mockDataService},
        {provide: ActivatedRoute, useValue: mockActivatedRoute},
        {provide: MatDialog, useValue: mockDialog},
        {provide: AuthService, useValue: mockAuthService},
      ],
    })
      .overrideComponent(VideoDetails, {
        set: {
          providers: [
            {provide: ProductSelectionService, useValue: mockSelectionService},
          ],
        },
      })
      .overrideProvider(MatDialog, {useValue: mockDialog})
      .compileComponents();

    mockDataService.getVideoAnalysis.and.returnValue(of(mockVideo));
    mockDataService.getAdGroupsForVideo.and.returnValue(of([]));
    mockDataService.getAdGroupInsertionStatusesForVideo.and.returnValue(of([]));
    mockDataService.updateCandidates.and.returnValue(of({}));
    mockDataService.insertSubmissionRequests.and.returnValue(of({}));
  });

  function createComponent() {
    fixture = TestBed.createComponent(VideoDetails);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it('should create', () => {
    createComponent();
    expect(component).toBeTruthy();
  });

  it('should load video data on init', () => {
    mockDataService.getVideoAnalysis.and.returnValue(of(mockVideo));
    createComponent();

    expect(component.video()).toEqual(mockVideo);
    expect(component.dataSource().length).toBe(1);
    expect(
      component.dataSource()[0].matchedProducts![0].matchedProductOfferId
    ).toBe('offer1');
    expect(component.loading()).toBeFalse();
  });

  it('should handle error when loading fails', () => {
    mockDataService.getVideoAnalysis.and.returnValue(
      throwError(() => new Error('Network error'))
    );
    mockDataService.getAdGroupsForVideo.and.returnValue(of([]));
    mockDataService.getAdGroupInsertionStatusesForVideo.and.returnValue(of([]));
    createComponent();

    expect(component.error()).toBe('Failed to load video data');
    expect(component.loading()).toBeFalse();
  });

  it('should transform gs:// GCS URI to storage.cloud.google.com URL', () => {
    const videoWithGcs = {
      ...mockVideo,
      video: {...mockVideo.video, gcsUri: 'gs://my-bucket/my-video.mp4'},
    };
    mockDataService.getVideoAnalysis.and.returnValue(of(videoWithGcs));
    createComponent();
    const safeUrl = component.gcsVideoUrl();
    expect(safeUrl).toBeTruthy();
    expect(safeUrl?.toString()).toContain('SafeValue');
  });

  it('should not transform non-gs:// GCS URI', () => {
    const videoWithHttps = {
      ...mockVideo,
      video: {
        ...mockVideo.video,
        gcsUri: 'https://storage.googleapis.com/b/v.mp4',
      },
    };
    mockDataService.getVideoAnalysis.and.returnValue(of(videoWithHttps));
    mockDataService.getAdGroupsForVideo.and.returnValue(of([]));
    mockDataService.getAdGroupInsertionStatusesForVideo.and.returnValue(of([]));
    createComponent();

    const safeUrl = component.gcsVideoUrl();
    expect(safeUrl).toBeTruthy();
  });

  it('should seek GCS video when jumpToTimestamp called', () => {
    const videoWithGcs = {
      ...mockVideo,
      video: {...mockVideo.video, videoId: null, gcsUri: 'gs://test'},
    };
    mockDataService.getVideoAnalysis.and.returnValue(of(videoWithGcs));
    createComponent();

    // Mock gcsVideo ElementRef
    const mockNativeElement = jasmine.createSpyObj('HTMLVideoElement', [
      'play',
    ]);
    mockNativeElement.currentTime = 0;
    component.gcsVideo = {nativeElement: mockNativeElement} as ElementRef;

    component.jumpToTimestamp(10000); // 10 seconds

    expect(mockNativeElement.currentTime).toBe(10);
    expect(mockNativeElement.play).toHaveBeenCalled();
  });

  it('should toggle selection via service', () => {
    mockDataService.getVideoAnalysis.and.returnValue(of(mockVideo));
    mockDataService.getAdGroupsForVideo.and.returnValue(of([]));
    mockDataService.getAdGroupInsertionStatusesForVideo.and.returnValue(of([]));
    createComponent();

    const match = mockVideo.identifiedProducts[0].matchedProducts![0];
    const productUuid = mockVideo.identifiedProducts[0].productUuid;
    component.selectionService.toggleSelection(mockVideo, productUuid, match);
    expect(mockSelectionService.toggleSelection).toHaveBeenCalledWith(
      mockVideo,
      productUuid,
      match
    );
  });

  it('should open submission dialog and push to google ads on success', () => {
    mockDataService.getVideoAnalysis.and.returnValue(of(mockVideo));
    mockDataService.insertSubmissionRequests.and.returnValue(of({}));
    mockDataService.getAdGroupsForVideo.and.returnValue(of([]));
    mockDataService.getAdGroupInsertionStatusesForVideo.and.returnValue(of([]));
    const dialogRefSpy = jasmine.createSpyObj({
      afterClosed: of([
        {
          videoUuid: 'uuid',
          offerIds: 'offer1',
          destinations: [],
          submittingUser: 'test@example.com',
          cpc: 1.52,
        },
      ]),
    });
    mockDialog.open.and.returnValue(dialogRefSpy);

    createComponent();

    component.openSubmissionDialog();

    expect(mockDialog.open).toHaveBeenCalledWith(SubmissionDialogComponent, {
      width: '500px',
      data: {
        videoUuid: 'uuid',
        offerIds: 'offer1',
        insertionStatuses: [],
        videoSource: 'manual',
      },
    });
    expect(mockDataService.insertSubmissionRequests).toHaveBeenCalled();
  });

  it('should reload insertion statuses and show spinner after successful submission', async () => {
    mockDataService.getVideoAnalysis.and.returnValue(of(mockVideo));
    mockDataService.insertSubmissionRequests.and.returnValue(of({}));
    mockDataService.getAdGroupsForVideo.and.returnValue(of([]));
    mockDataService.getAdGroupInsertionStatusesForVideo.and.returnValue(of([]));

    const dialogRefSpy = jasmine.createSpyObj({
      afterClosed: of([
        {
          videoUuid: 'uuid',
          offerIds: 'offer1',
        },
      ]),
    });

    mockDialog.open.and.returnValue(dialogRefSpy);
    createComponent();
    expect(component.isRefreshingInsertionStatuses()).toBeFalse();
    component.openSubmissionDialog();
    fixture.detectChanges();
    expect(
      mockDataService.getAdGroupInsertionStatusesForVideo
    ).toHaveBeenCalledTimes(2);
  });

  it('should allow re-submission even if offers are already pushed', () => {
    mockDataService.getVideoAnalysis.and.returnValue(of(mockVideo));

    const mockAdGroups = [
      {
        id: '1',
        name: 'Ad Group 1',
        status: 'ENABLED',
        campaign_id: 'c1',
        customer_id: 'cust1',
      },
    ];
    mockDataService.getAdGroupsForVideo.and.returnValue(of(mockAdGroups));

    const mockStatuses: AdGroupInsertionStatus[] = [
      {
        requestUuid: 'req-uuid',
        videoAnalysisUuid: 'video-uuid',
        status: 'SUCCESS',
        timestamp: new Date().toISOString(),
        adsEntities: [
          {
            customerId: 1,
            campaignId: 1,
            adGroupId: 1,
            products: [{offerId: 'offer1', status: 'success'}],
          },
        ],
      },
    ];

    mockDataService.getAdGroupInsertionStatusesForVideo.and.returnValue(
      of(mockStatuses)
    );

    createComponent();
    expect(component.hasProcessableOffers()).toBeTrue();
  });

  it('should not fetch ad groups for non-Google Ads videos', () => {
    const manualVideo = {
      ...mockVideo,
      video: {...mockVideo.video, source: 'manual'},
    };
    mockDataService.getVideoAnalysis.and.returnValue(of(manualVideo));
    createComponent();
    expect(mockDataService.getAdGroupsForVideo).not.toHaveBeenCalled();
  });

  it('should fetch ad groups for Google Ads videos', () => {
    const googleAdsVideo = {
      ...mockVideo,
      video: {...mockVideo.video, source: 'google_ads'},
    };
    mockDataService.getVideoAnalysis.and.returnValue(of(googleAdsVideo));
    mockDataService.getAdGroupsForVideo.and.returnValue(of([]));
    mockDataService.getAdGroupInsertionStatusesForVideo.and.returnValue(of([]));

    createComponent();
    expect(mockDataService.getAdGroupsForVideo).toHaveBeenCalledWith(
      googleAdsVideo.video.uuid
    );
  });
});

function signal<T>(arg0: T): () => T {
  return () => arg0;
}
