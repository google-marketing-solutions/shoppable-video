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
import {of} from 'rxjs';
import {
  PaginatedVideoAnalysisSummary,
  VideoAnalysisSummary,
} from '../../models';
import {DataService} from '../../services/data.service';
import {AllResults} from './all-results';
import {PageEvent} from '@angular/material/paginator';

describe('AllResults', () => {
  let component: AllResults;
  let fixture: ComponentFixture<AllResults>;
  let mockDataService: jasmine.SpyObj<DataService>;

  beforeEach(async () => {
    mockDataService = jasmine.createSpyObj('DataService', [
      'getVideoAnalysisSummaries',
    ]);
    mockDataService.getVideoAnalysisSummaries.and.returnValue(
      of({
        items: [],
        totalCount: 0,
        limit: 10,
        offset: 0,
      } as PaginatedVideoAnalysisSummary)
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
    }).compileComponents();

    fixture = TestBed.createComponent(AllResults);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should call getVideoAnalysisSummaries on init', () => {
    expect(mockDataService.getVideoAnalysisSummaries).toHaveBeenCalledWith(
      10,
      0
    );
  });

  it('should call getVideoAnalysisSummaries on page change', () => {
    const pageEvent: PageEvent = {
      pageIndex: 1,
      pageSize: 20,
      length: 100,
    };
    component.onPageChange(pageEvent);
    expect(mockDataService.getVideoAnalysisSummaries).toHaveBeenCalledWith(
      20,
      20
    );
  });

  it('should display summary data in table', () => {
    const mockData: VideoAnalysisSummary[] = [
      {
        video: {
          uuid: 'uuid1',
          source: 'test',
          videoId: 'v1',
          gcsUri: '',
          md5Hash: '',
        },
        identifiedProductsCount: 5,
        matchedProductsCount: 3,
        approvedProductsCount: 1,
        disapprovedProductsCount: 1,
        unreviewedProductsCount: 1,
      },
    ];

    mockDataService.getVideoAnalysisSummaries.and.returnValue(
      of({
        items: mockData,
        totalCount: 1,
        limit: 10,
        offset: 0,
      } as PaginatedVideoAnalysisSummary)
    );

    // Trigger page load again or re-create component
    component.onPageChange({
      pageIndex: 0,
      pageSize: 10,
      length: 1,
    } as PageEvent);
    fixture.detectChanges();

    expect(component.matDataSource.data.length).toBe(1);
    expect(component.matDataSource.data[0].video.uuid).toBe('uuid1');
  });
});
