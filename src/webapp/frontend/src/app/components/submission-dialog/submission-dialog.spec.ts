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
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {AuthService} from '../../services/auth.service';
import {SubmissionDialogComponent} from './submission-dialog';

describe('SubmissionDialogComponent', () => {
  let component: SubmissionDialogComponent;
  let fixture: ComponentFixture<SubmissionDialogComponent>;
  let mockAuthService: jasmine.SpyObj<AuthService>;

  const defaultDialogData = {
    videoUuid: 'test-video-uuid',
  };

  beforeEach(async () => {
    mockAuthService = jasmine.createSpyObj('AuthService', [], {
      user: signal({email: 'test@example.com', name: 'Test User', picture: ''}),
    });
    await TestBed.configureTestingModule({
      imports: [SubmissionDialogComponent],
      providers: [
        {provide: MatDialogRef, useValue: {}},
        {provide: MAT_DIALOG_DATA, useValue: defaultDialogData},
        {provide: AuthService, useValue: mockAuthService},
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(SubmissionDialogComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('should initialize videoUuid from dialogData', () => {
    fixture.detectChanges();
    expect(component.data.videoUuid).toBe('test-video-uuid');
  });

  it('should populate submittingUser from authService', () => {
    fixture.detectChanges();
    expect(component.data.submittingUser).toBe('test@example.com');
  });

  it('should not overwrite existing submittingUser', () => {
    const existingUser = 'existing@example.com';
    component.data.submittingUser = existingUser;
    fixture.detectChanges();
    expect(component.data.submittingUser).toBe(existingUser);
  });
});
