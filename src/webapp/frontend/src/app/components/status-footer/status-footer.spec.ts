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
import {Status} from '../../models';
import {StatusFooterComponent} from './status-footer';

describe('StatusFooterComponent', () => {
  let component: StatusFooterComponent;
  let fixture: ComponentFixture<StatusFooterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StatusFooterComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(StatusFooterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should include valid statuses in options', () => {
    expect(component.statusOptions).toContain(Status.APPROVED);
    expect(component.statusOptions).toContain(Status.UNREVIEWED);
    expect(component.statusOptions).toContain(Status.DISAPPROVED);
  });

  it('should emit update event when onUpdate is called with APPROVED status', () => {
    const spy = spyOn(component.update, 'emit');
    component.selectedStatus = Status.APPROVED;
    component.onUpdate();
    expect(spy).toHaveBeenCalledWith(Status.APPROVED);
  });

  it('should emit update event when onUpdate is called with non-APPROVED status', () => {
    const spy = spyOn(component.update, 'emit');
    component.selectedStatus = Status.DISAPPROVED;
    component.onUpdate();
    expect(spy).toHaveBeenCalledWith(Status.DISAPPROVED);
  });

  it('should not emit update event when onUpdate is called without a selected status', () => {
    const spy = spyOn(component.update, 'emit');
    component.selectedStatus = '';
    component.onUpdate();
    expect(spy).not.toHaveBeenCalled();
  });

  it('should display the correct selection count placeholder', () => {
    component.selectionCount = 5;
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('5 items selected');
  });
});
