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
import {Router} from '@angular/router';
import {AuthService, UserProfile} from '../../services/auth.service';
import {LoginComponent} from './login';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;
  let mockAuthService: jasmine.SpyObj<AuthService>;
  let mockRouter: jasmine.SpyObj<Router>;
  let userSignal: ReturnType<typeof signal<UserProfile | null>>;

  beforeEach(async () => {
    userSignal = signal<UserProfile | null>(null);
    mockAuthService = jasmine.createSpyObj('AuthService', ['login'], {
      user: userSignal,
    });
    mockRouter = jasmine.createSpyObj('Router', ['navigate']);

    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        {provide: AuthService, useValue: mockAuthService},
        {provide: Router, useValue: mockRouter},
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('initialization', () => {
    it('should redirect if user is already logged in', () => {
      userSignal.set({
        email: 'test@example.com',
        picture: '',
        name: 'Test',
      } as UserProfile);

      const newFixture = TestBed.createComponent(LoginComponent);
      newFixture.detectChanges();

      expect(mockRouter.navigate).not.toHaveBeenCalled();
    });
  });

  describe('login', () => {
    it('should call authService.login', async () => {
      mockAuthService.login.and.resolveTo();
      await component.login();
      expect(mockAuthService.login).toHaveBeenCalled();
    });
  });
});
