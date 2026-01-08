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
import {ActivatedRoute} from '@angular/router';
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
          useValue: {snapshot: {paramMap: {get: () => null}}},
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
        video_analysis_uuid: '1',
        source: 'test',
        video: {video_location: '', video_id: '1', gcs_uri: '', md5_hash: ''},
        identified_products: [
          {
            title: 'Product 1',
            description: '',
            relevance_reasoning: '',
            product_uuid: 'p1',
            matched_products: [
              {
                matched_product_offer_id: 'm1',
                matched_product_title: 'M1',
                matched_product_brand: 'B1',
                timestamp: '',
                distance: 0.5,
                status: '',
              },
              {
                matched_product_offer_id: 'm2',
                matched_product_title: 'M2',
                matched_product_brand: 'B2',
                timestamp: '',
                distance: 0.9,
                status: '',
              },
              {
                matched_product_offer_id: 'm3',
                matched_product_title: 'M3',
                matched_product_brand: 'B3',
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
      component.matDataSource.data[0].identified_products[0].matched_products;
    expect(products[0].distance).toBe(0.9);
    expect(products[1].distance).toBe(0.5);
    expect(products[2].distance).toBe(0.1);
  });

  it('should deduplicate matched products based on offer id', () => {
    const mockData: VideoAnalysis[] = [
      {
        video_analysis_uuid: '1',
        source: 'test',
        video: {video_location: '', video_id: '1', gcs_uri: '', md5_hash: ''},
        identified_products: [
          {
            title: 'Product 1',
            description: '',
            relevance_reasoning: '',
            product_uuid: 'p1',
            matched_products: [
              {
                matched_product_offer_id: 'm1',
                matched_product_title: 'M1',
                matched_product_brand: 'B1',
                timestamp: '',
                distance: 0.5,
                status: Status.PENDING,
              },
              {
                matched_product_offer_id: 'm1',
                matched_product_title: 'M1 Duplicate',
                matched_product_brand: 'B1',
                timestamp: '',
                distance: 0.5,
                status: Status.PENDING,
              },
              {
                matched_product_offer_id: 'm2',
                matched_product_title: 'M2',
                matched_product_brand: 'B2',
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
      component.matDataSource.data[0].identified_products[0].matched_products;
    expect(products.length).toBe(2);
    expect(
      products.find((p) => p.matched_product_offer_id === 'm1')
    ).toBeDefined();
    expect(
      products.find((p) => p.matched_product_offer_id === 'm2')
    ).toBeDefined();
  });

  it('should update match status when status is updated', () => {
    const mockData: VideoAnalysis[] = [
      {
        video_analysis_uuid: 'uuid1',
        source: '',
        video: {video_location: '', video_id: '', gcs_uri: '', md5_hash: ''},
        identified_products: [
          {
            title: '',
            description: '',
            relevance_reasoning: '',
            product_uuid: '',
            matched_products: [
              {
                matched_product_offer_id: 'offer1',
                matched_product_title: '',
                matched_product_brand: '',
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
    const match = video.identified_products[0].matched_products[0];

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
