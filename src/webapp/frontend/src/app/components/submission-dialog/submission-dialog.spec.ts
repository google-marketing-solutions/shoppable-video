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

import {signal} from '@angular/core';
import {ComponentFixture, TestBed} from '@angular/core/testing';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {of} from 'rxjs';
import {AuthService} from '../../services/auth.service';
import {DataService} from '../../services/data.service';
import {
  SubmissionDialogComponent,
  SubmissionDialogData,
} from './submission-dialog';

describe('SubmissionDialogComponent', () => {
  let component: SubmissionDialogComponent;
  let fixture: ComponentFixture<SubmissionDialogComponent>;
  let mockAuthService: jasmine.SpyObj<AuthService>;
  let mockDataService: jasmine.SpyObj<DataService>;
  let mockDialogRef: jasmine.SpyObj<MatDialogRef<SubmissionDialogComponent>>;

  const defaultDialogData = {
    videoUuid: 'test-video-uuid',
    destinations: [],
    cpc: 1.52,
    videoSource: 'google_ads',
  };

  async function configureTestModule(
    dialogData: Partial<SubmissionDialogData>
  ) {
    mockAuthService = jasmine.createSpyObj('AuthService', [], {
      user: signal({email: 'test@example.com', name: 'Test User', picture: ''}),
    });
    mockDataService = jasmine.createSpyObj('DataService', [
      'getAdGroupsForVideo',
    ]);
    mockDataService.getAdGroupsForVideo.and.returnValue(of([]));
    mockDialogRef = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [SubmissionDialogComponent, MatCheckboxModule],
      providers: [
        {provide: MatDialogRef, useValue: mockDialogRef},
        {provide: MAT_DIALOG_DATA, useValue: dialogData},
        {provide: AuthService, useValue: mockAuthService},
        {provide: DataService, useValue: mockDataService},
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SubmissionDialogComponent);
    component = fixture.componentInstance;
    spyOn(component.cdr, 'markForCheck'); // Spy on change detector
  }

  describe('with CPC provided', () => {
    beforeEach(async () => {
      await configureTestModule(defaultDialogData);
      fixture.detectChanges();
    });

    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should initialize useDefaultCpc to false', () => {
      expect(component.useDefaultCpc).toBeFalse();
    });

    it('should initialize cpc from dialogData', () => {
      expect(component.data.cpc).toBe(1.52);
    });

    it('should submit with provided CPC if useDefaultCpc is false', () => {
      component.useDefaultCpc = false;
      component.data.cpc = 2.5;
      component.selectedDestinations = [
        {
          adGroupId: '1',
          campaignId: '1',
          customerId: '1',
          adGroupName: 'Test',
        },
      ];
      component.data.offerIds = '123';

      component.submit();

      expect(mockDialogRef.close).toHaveBeenCalled();
      const result = mockDialogRef.close.calls.mostRecent().args[0];
      expect(result[0].cpc).toBe(2.5);
    });

    it('should submit with undefined CPC if useDefaultCpc is switched to true', () => {
      component.useDefaultCpc = true;
      component.data.cpc = 2.5; // value exists but ignored
      component.selectedDestinations = [
        {
          adGroupId: '1',
          campaignId: '1',
          customerId: '1',
          adGroupName: 'Test',
        },
      ];
      component.data.offerIds = '123';

      component.submit();

      expect(mockDialogRef.close).toHaveBeenCalled();
      const result = mockDialogRef.close.calls.mostRecent().args[0];
      expect(result[0].cpc).toBeUndefined();
    });
  });

  describe('without CPC provided', () => {
    beforeEach(async () => {
      await configureTestModule({
        ...defaultDialogData,
        cpc: undefined,
      });
      fixture.detectChanges();
    });

    it('should initialize useDefaultCpc to true', () => {
      expect(component.useDefaultCpc).toBeTrue();
    });

    it('should submit undefined CPC by default', () => {
      component.selectedDestinations = [
        {
          adGroupId: '1',
          campaignId: '1',
          customerId: '1',
          adGroupName: 'Test',
        },
      ];
      component.data.offerIds = '123';

      component.submit();

      expect(mockDialogRef.close).toHaveBeenCalled();
      const result = mockDialogRef.close.calls.mostRecent().args[0];
      expect(result[0].cpc).toBeUndefined();
    });

    it('should submit manually entered CPC if useDefaultCpc is unchecked', () => {
      component.useDefaultCpc = false;
      component.data.cpc = 0.99;
      component.selectedDestinations = [
        {
          adGroupId: '1',
          campaignId: '1',
          customerId: '1',
          adGroupName: 'Test',
        },
      ];
      component.data.offerIds = '123';

      component.submit();

      expect(mockDialogRef.close).toHaveBeenCalled();
      const result = mockDialogRef.close.calls.mostRecent().args[0];
      expect(result[0].cpc).toBe(0.99);
    });
  });

  it('should trigger change detection after ad groups are loaded', async () => {
    await configureTestModule({
      ...defaultDialogData,
      videoSource: 'google_ads',
    });
    fixture.detectChanges();
    expect(mockDataService.getAdGroupsForVideo).toHaveBeenCalledWith(
      'test-video-uuid'
    );
    expect(component.cdr.markForCheck).toHaveBeenCalled();
  });

  it('should NOT load ad groups if videoSource is not google_ads', async () => {
    await configureTestModule({
      ...defaultDialogData,
      videoSource: 'manual',
    });
    fixture.detectChanges();
    expect(mockDataService.getAdGroupsForVideo).not.toHaveBeenCalled();
  });
});
