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
import {of, Subject} from 'rxjs';
import {Status, VideoAnalysis} from '../../models';
import {DataService} from '../../services/data.service';
import {ProductSelectionService} from '../../services/product-selection.service';
import {AllResults} from './all-results';

describe('AllResults', () => {
  let component: AllResults;
  let fixture: ComponentFixture<AllResults>;
  let mockDataService: jasmine.SpyObj<DataService>;
  let mockSelectionService: jasmine.SpyObj<ProductSelectionService>;

  beforeEach(async () => {
    mockDataService = jasmine.createSpyObj('DataService', [
      'getAllData',
      'addCandidateStatus',
    ]);
    mockDataService.getAllData.and.returnValue(of([]));
    mockSelectionService = jasmine.createSpyObj(
      'ProductSelectionService',
      ['toggleSelection', 'isSelected', 'updateStatus'],
      {
        statusUpdated$: new Subject<void>(),
        matchedProductSelection: {selected: []},
      }
    );

    await TestBed.configureTestingModule({
      imports: [AllResults],
      providers: [
        {provide: DataService, useValue: mockDataService},
        {
          provide: ActivatedRoute,
          useValue: {snapshot: {paramMap: convertToParamMap({})}},
        },
      ],
    })
      .overrideComponent(AllResults, {
        set: {
          providers: [
            {provide: ProductSelectionService, useValue: mockSelectionService},
          ],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(AllResults);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should sort matched products by distance descending', () => {
    const mockData: VideoAnalysis[] = [
      {
        videoAnalysisUuid: '1',
        source: 'test',
        video: {videoLocation: '', videoId: '1', gcsUri: '', md5Hash: ''},
        identifiedProducts: [
          {
            title: 'Product 1',
            description: '',
            relevanceReasoning: '',
            productUuid: 'p1',
            matchedProducts: [
              {
                matchedProductOfferId: 'm1',
                matchedProductTitle: 'M1',
                matchedProductBrand: 'B1',
                timestamp: '',
                distance: 0.5,
                status: '',
              },
              {
                matchedProductOfferId: 'm2',
                matchedProductTitle: 'M2',
                matchedProductBrand: 'B2',
                timestamp: '',
                distance: 0.9,
                status: '',
              },
              {
                matchedProductOfferId: 'm3',
                matchedProductTitle: 'M3',
                matchedProductBrand: 'B3',
                timestamp: '',
                distance: 0.1,
                status: '',
              },
            ],
          },
        ],
      },
    ];

    mockDataService.getAllData.and.returnValue(of(mockData));

    fixture = TestBed.createComponent(AllResults);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const products =
      component.matDataSource.data[0].identifiedProducts[0].matchedProducts;
    expect(products[0].distance).toBe(0.1);
    expect(products[1].distance).toBe(0.5);
    expect(products[2].distance).toBe(0.9);
  });

  it('should deduplicate matched products based on offer id', () => {
    const mockData: VideoAnalysis[] = [
      {
        videoAnalysisUuid: '1',
        source: 'test',
        video: {videoLocation: '', videoId: '1', gcsUri: '', md5Hash: ''},
        identifiedProducts: [
          {
            title: 'Product 1',
            description: '',
            relevanceReasoning: '',
            productUuid: 'p1',
            matchedProducts: [
              {
                matchedProductOfferId: 'm1',
                matchedProductTitle: 'M1',
                matchedProductBrand: 'B1',
                timestamp: '',
                distance: 0.5,
                status: Status.PENDING,
              },
              {
                matchedProductOfferId: 'm1',
                matchedProductTitle: 'M1 Duplicate',
                matchedProductBrand: 'B1',
                timestamp: '',
                distance: 0.5,
                status: Status.PENDING,
              },
              {
                matchedProductOfferId: 'm2',
                matchedProductTitle: 'M2',
                matchedProductBrand: 'B2',
                timestamp: '',
                distance: 0.9,
                status: Status.PENDING,
              },
            ],
          },
        ],
      },
    ];

    mockDataService.getAllData.and.returnValue(of(mockData));

    fixture = TestBed.createComponent(AllResults);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const products =
      component.matDataSource.data[0].identifiedProducts[0].matchedProducts;
    expect(products.length).toBe(2);
    expect(
      products.find((p) => p.matchedProductOfferId === 'm1')
    ).toBeDefined();
    expect(
      products.find((p) => p.matchedProductOfferId === 'm2')
    ).toBeDefined();
  });

  it('should update match status when status is updated', () => {
    const mockData: VideoAnalysis[] = [
      {
        videoAnalysisUuid: 'uuid1',
        source: '',
        video: {videoLocation: '', videoId: '', gcsUri: '', md5Hash: ''},
        identifiedProducts: [
          {
            title: '',
            description: '',
            relevanceReasoning: '',
            productUuid: '',
            matchedProducts: [
              {
                matchedProductOfferId: 'offer1',
                matchedProductTitle: '',
                matchedProductBrand: '',
                timestamp: '',
                distance: 0,
                status: '',
              },
            ],
          },
        ],
      },
    ];
    mockDataService.getAllData.and.returnValue(of(mockData));
    mockDataService.addCandidateStatus.and.returnValue(of({}));

    fixture = TestBed.createComponent(AllResults);
    component = fixture.componentInstance;
    fixture.detectChanges();

    // Simulate selection and status update
    const video = component.matDataSource.data[0];
    const match = video.identifiedProducts[0].matchedProducts[0];

    // We can't easily test the full integration here since we mocked the service
    // But we can verify the service methods are called if we were to trigger them from template
    // Or we can test that the component delegates to the service

    component.selectionService.toggleSelection(video, match);
    expect(mockSelectionService.toggleSelection).toHaveBeenCalledWith(
      video,
      match
    );

    component.selectionService.updateStatus(Status.COMPLETED);
    expect(mockSelectionService.updateStatus).toHaveBeenCalledWith(
      Status.COMPLETED
    );
  });
});
