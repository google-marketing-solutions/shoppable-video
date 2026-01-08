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
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {
  ActivatedRoute,
  convertToParamMap,
  ParamMap,
  Router,
} from '@angular/router';
import {of, Subject} from 'rxjs';
import {ROUTES} from '../../core/routing/routes';
import {PARAMS} from '../../core/routing/params';
import {CandidateStatus, Status} from '../../models';
import {DataService} from '../../services/data.service';
import {StatusComponent} from './status';

describe('StatusComponent', () => {
  let component: StatusComponent;
  let fixture: ComponentFixture<StatusComponent>;
  let mockDataService: jasmine.SpyObj<DataService>;
  let mockRouter: jasmine.SpyObj<Router>;
  let routeParams: Subject<ParamMap>;

  const mockCandidateData: CandidateStatus[] = [
    {
      videoAnalysisUuid: 'uuid1',
      candidateOfferId: 'offer1',
      status: Status.PENDING,
      timestamp: '2025-01-01T00:00:00Z',
    },
    {
      videoAnalysisUuid: 'uuid2',
      candidateOfferId: 'offer2',
      status: Status.COMPLETED,
      timestamp: '2025-01-01T00:00:00Z',
    },
  ];

  beforeEach(async () => {
    mockDataService = jasmine.createSpyObj('DataService', [
      'getCandidateStatus',
      'getCandidateStatusByStatus',
      'addCandidateStatus',
    ]);
    mockRouter = jasmine.createSpyObj('Router', ['navigate']);
    routeParams = new Subject();

    mockDataService.getCandidateStatus.and.returnValue(of(mockCandidateData));
    mockDataService.getCandidateStatusByStatus.and.returnValue(
      of([mockCandidateData[0]])
    );
    mockDataService.addCandidateStatus.and.returnValue(
      of({} as CandidateStatus)
    );

    await TestBed.configureTestingModule({
      imports: [StatusComponent, NoopAnimationsModule],
      providers: [
        {provide: DataService, useValue: mockDataService},
        {provide: Router, useValue: mockRouter},
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: routeParams,
            snapshot: {
              paramMap: {
                get: (key: string) => (key === PARAMS.STATUS ? null : null),
              },
            },
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StatusComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('initialization', () => {
    it('should load all data when no status param is provided', () => {
      routeParams.next(convertToParamMap({}));
      expect(mockDataService.getCandidateStatus).toHaveBeenCalled();
      expect(component.dataSource()).toEqual(mockCandidateData);
    });

    it('should load filtered data when valid status param is provided', () => {
      routeParams.next(convertToParamMap({[PARAMS.STATUS]: 'pending'}));
      expect(mockDataService.getCandidateStatusByStatus).toHaveBeenCalledWith(
        'pending'
      );
      expect(component.dataSource()).toEqual([mockCandidateData[0]]);
    });

    it('should redirect if invalid status param is provided', () => {
      routeParams.next(convertToParamMap({[PARAMS.STATUS]: 'invalid_status'}));
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/' + ROUTES.STATUS]);
    });
  });

  describe('selection logic', () => {
    it('should correctly report isAllSelected', () => {
      expect(component.isAllSelected()).toBeFalse();
      component.dataSource().forEach((row) => component.selection.select(row));
      expect(component.isAllSelected()).toBeTrue();
    });

    it('should toggle all rows with masterToggle', () => {
      component.masterToggle();
      expect(component.selection.selected.length).toBe(
        mockCandidateData.length
      );

      component.masterToggle();
      expect(component.selection.selected.length).toBe(0);
    });

    it('should return correct checkbox labels', () => {
      expect(component.checkboxLabel()).toBe('select all');
      expect(component.checkboxLabel(mockCandidateData[0])).toBe(
        'select row offer1'
      );

      component.selection.select(mockCandidateData[0]);
      expect(component.checkboxLabel(mockCandidateData[0])).toBe(
        'deselect row offer1'
      );
    });
  });

  describe('status class mapping', () => {
    it('should return correct CSS classes for statuses', () => {
      expect(component.getStatusClass(Status.COMPLETED)).toBe('status-success');
      expect(component.getStatusClass(Status.PENDING)).toBe('status-pending');
      expect(component.getStatusClass(Status.FAILED)).toBe('status-error');
      expect(component.getStatusClass(Status.DISAPPROVED)).toBe('status-error');
      expect(component.getStatusClass('' as Status)).toBe('status-neutral');
    });
  });

  describe('handleStatusUpdate', () => {
    it('should call dataService.addCandidateStatus for each selected item', () => {
      component.selection.select(mockCandidateData[0]);
      component.selection.select(mockCandidateData[1]);

      component.handleStatusUpdate(Status.COMPLETED);

      expect(mockDataService.addCandidateStatus).toHaveBeenCalledTimes(2);
      expect(component.loading()).toBeFalse(); // After forkJoin completes
    });

    it('should not call dataService if no items are selected', () => {
      component.selection.clear();
      component.handleStatusUpdate(Status.COMPLETED);
      expect(mockDataService.addCandidateStatus).not.toHaveBeenCalled();
    });
  });
});
