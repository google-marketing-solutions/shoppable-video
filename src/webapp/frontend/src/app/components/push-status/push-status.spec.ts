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

import {provideRouter} from '@angular/router';
import {ComponentFixture, TestBed} from '@angular/core/testing';
import {PageEvent} from '@angular/material/paginator';
import {of} from 'rxjs';
import {
  AdGroupInsertionStatus,
  PaginatedAdGroupInsertionStatus,
} from '../../models';
import {DataService} from '../../services/data.service';
import {PushStatusComponents} from './push-status';

describe('PushStatusComponents', () => {
  let component: PushStatusComponents;
  let fixture: ComponentFixture<PushStatusComponents>;
  let mockDataService: jasmine.SpyObj<DataService>;

  beforeEach(async () => {
    mockDataService = jasmine.createSpyObj('DataService', [
      'getAdGroupInsertionStatuses',
    ]);
    mockDataService.getAdGroupInsertionStatuses.and.returnValue(
      of({
        items: [],
        totalCount: 0,
        limit: 10,
        offset: 0,
      } as PaginatedAdGroupInsertionStatus)
    );

    await TestBed.configureTestingModule({
      imports: [PushStatusComponents],
      providers: [
        {provide: DataService, useValue: mockDataService},
        provideRouter([]),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PushStatusComponents);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should call getAdGroupInsertionStatuses on init', () => {
    expect(mockDataService.getAdGroupInsertionStatuses).toHaveBeenCalledWith(
      10,
      0
    );
  });

  it('should call getAdGroupInsertionStatuses on page change', () => {
    const pageEvent: PageEvent = {
      pageIndex: 1,
      pageSize: 20,
      length: 100,
    };
    component.onPageChange(pageEvent);
    expect(mockDataService.getAdGroupInsertionStatuses).toHaveBeenCalledWith(
      20,
      20
    );
  });

  it('should display status data in table', () => {
    const mockData: AdGroupInsertionStatus[] = [
      {
        requestUuid: 'req-1',
        videoAnalysisUuid: 'video-1',
        timestamp: '2025-01-01T00:00:00Z',
        status: 'SUCCESS',
        adsEntities: [],
      },
    ];

    mockDataService.getAdGroupInsertionStatuses.and.returnValue(
      of({
        items: mockData,
        totalCount: 1,
        limit: 10,
        offset: 0,
      } as PaginatedAdGroupInsertionStatus)
    );

    // Trigger page load again via page change to force new emission
    component.onPageChange({
      pageIndex: 0,
      pageSize: 10,
      length: 1,
    } as PageEvent);
    fixture.detectChanges();

    expect(component.matDataSource.data.length).toBe(1);
    expect(component.matDataSource.data[0].requestUuid).toBe('req-1');
    expect(component.matDataSource.data[0].videoAnalysisUuid).toBe('video-1');

    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const link = compiled.querySelector('a');
    expect(link).toBeTruthy();
    expect(link?.getAttribute('href')).toContain('/video/video-1');
    expect(link?.textContent?.trim()).toBe('video-1');
  });
});
