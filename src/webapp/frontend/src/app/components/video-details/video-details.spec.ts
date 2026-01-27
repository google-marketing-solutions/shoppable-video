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

import {ComponentFixture, TestBed} from '@angular/core/testing';
import {ActivatedRoute, convertToParamMap} from '@angular/router';
import {BehaviorSubject, of, Subject, throwError} from 'rxjs';
import {VideoAnalysis} from '../../models';
import {DataService} from '../../services/data.service';
import {ProductSelectionService} from '../../services/product-selection.service';
import {VideoDetails} from './video-details';

describe('VideoDetails', () => {
  let component: VideoDetails;
  let fixture: ComponentFixture<VideoDetails>;
  let mockDataService: jasmine.SpyObj<DataService>;
  let mockSelectionService: jasmine.SpyObj<ProductSelectionService>;
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
            status: 'Approved',
          },
        ],
      },
    ],
  };

  beforeEach(async () => {
    mockDataService = jasmine.createSpyObj('DataService', [
      'getVideoAnalysis',
      'updateCandidates',
    ]);
    mockSelectionService = jasmine.createSpyObj(
      'ProductSelectionService',
      ['toggleSelection', 'isSelected', 'updateStatus'],
      {
        statusUpdated$: new Subject<void>(),
        matchedProductSelection: {
          selected: [],
          hasValue: () => false,
        },
      }
    );
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
      ],
    })
      .overrideComponent(VideoDetails, {
        set: {
          providers: [
            {provide: ProductSelectionService, useValue: mockSelectionService},
          ],
        },
      })
      .compileComponents();
  });

  function createComponent() {
    fixture = TestBed.createComponent(VideoDetails);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it('should create', () => {
    mockDataService.getVideoAnalysis.and.returnValue(of(mockVideo));
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
    createComponent();

    expect(component.error()).toBe('Failed to load video data');
    expect(component.loading()).toBeFalse();
  });

  it('should toggle selection via service', () => {
    mockDataService.getVideoAnalysis.and.returnValue(of(mockVideo));
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
});
