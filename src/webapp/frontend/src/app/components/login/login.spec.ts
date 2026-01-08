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
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router} from '@angular/router';
import {AuthService} from '../../services/auth.service';
import {LoginComponent} from './login';

describe('LoginComponent', () => {
  interface MockUser {
    uid: string;
    email: string;
  }
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;
  let mockAuthService: jasmine.SpyObj<AuthService>;
  let mockRouter: jasmine.SpyObj<Router>;
  let userSignal: ReturnType<typeof signal>;

  beforeEach(async () => {
    userSignal = signal(null);
    mockAuthService = jasmine.createSpyObj(
      'AuthService',
      ['login', 'loginWithGoogle'],
      {
        user: userSignal,
      }
    );
    mockRouter = jasmine.createSpyObj('Router', ['navigate']);

    await TestBed.configureTestingModule({
      imports: [LoginComponent, NoopAnimationsModule],
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
      // Create a new component to trigger constructor logic with logged in user
      userSignal.set({uid: '123', email: 'test@example.com'} as MockUser);

      // Re-create component to trigger constructor
      const newFixture = TestBed.createComponent(LoginComponent);
      newFixture.detectChanges();

      expect(mockRouter.navigate).toHaveBeenCalledWith([
        '/product-suggestions',
      ]);
    });

    it('should not redirect if user is not logged in', () => {
      expect(mockRouter.navigate).not.toHaveBeenCalled();
    });
  });

  describe('login', () => {
    it('should login successfully and navigate', async () => {
      component.email = 'test@example.com';
      component.password = 'password';
      mockAuthService.login.and.resolveTo();

      await component.login();

      expect(mockAuthService.login).toHaveBeenCalledWith(
        'test@example.com',
        'password'
      );
      expect(mockRouter.navigate).toHaveBeenCalledWith([
        '/product-suggestions',
      ]);
      expect(component.authError()).toBeNull();
    });

    it('should handle login error', async () => {
      const errorMsg = 'Invalid credentials';
      mockAuthService.login.and.rejectWith(new Error(errorMsg));

      await component.login();

      expect(component.authError()).toBe(errorMsg);
      expect(mockRouter.navigate).not.toHaveBeenCalled();
    });

    it('should handle unknown login error', async () => {
      mockAuthService.login.and.rejectWith('Unknown error');

      await component.login();

      expect(component.authError()).toBe('An unknown error occurred');
      expect(mockRouter.navigate).not.toHaveBeenCalled();
    });
  });

  describe('loginWithGoogle', () => {
    it('should login with google successfully and navigate', async () => {
      mockAuthService.loginWithGoogle.and.resolveTo();

      await component.loginWithGoogle();

      expect(mockAuthService.loginWithGoogle).toHaveBeenCalled();
      expect(mockRouter.navigate).toHaveBeenCalledWith([
        '/product-suggestions',
      ]);
      expect(component.authError()).toBeNull();
    });

    it('should handle google login error', async () => {
      const errorMsg = 'Google auth failed';
      mockAuthService.loginWithGoogle.and.rejectWith(new Error(errorMsg));

      await component.loginWithGoogle();

      expect(component.authError()).toBe(errorMsg);
      expect(mockRouter.navigate).not.toHaveBeenCalled();
    });
  });

  describe('UI interactions', () => {
    it('should toggle password visibility', () => {
      expect(component.hidePassword).toBeTrue();

      component.hidePassword = !component.hidePassword;
      expect(component.hidePassword).toBeFalse();

      component.hidePassword = !component.hidePassword;
      expect(component.hidePassword).toBeTrue();
    });
  });
});
