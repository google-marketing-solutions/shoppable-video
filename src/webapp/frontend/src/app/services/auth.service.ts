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

import {HttpClient} from '@angular/common/http';
import {Injectable, inject, signal} from '@angular/core';
import {Router} from '@angular/router';
import {firstValueFrom} from 'rxjs';
import {environment} from '../../environments/environment';

/**
 * Interface representing the structure of a user profile.
 * It contains basic information about the authenticated user.
 */
export interface UserProfile {
  email: string;
  picture: string;
  name: string;
}

/**
 * Service for handling user authentication.
 * Manages user login state, provides methods for logging in and out,
 * and checks the current session status with the backend.
 */
@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);

  user = signal<UserProfile | null>(null);
  loading = signal<boolean>(true);

  constructor() {
    this.checkSession();
  }

  async checkSession(): Promise<void> {
    try {
      this.loading.set(true);
      const res = await firstValueFrom(
        this.http.get<{status: string; user: UserProfile}>(
          `${environment.apiUrl}/auth/me`
        )
      );
      this.user.set(res.user);
    } catch (error) {
      this.user.set(null);
    } finally {
      this.loading.set(false);
    }
  }

  async login(): Promise<void> {
    window.location.href = `${environment.apiUrl}/auth/login`;
  }

  async logout(): Promise<void> {
    try {
      await firstValueFrom(this.http.get(`${environment.apiUrl}/auth/logout`));
    } catch (error) {
      console.error('Logout failed', error);
    } finally {
      this.user.set(null);
      this.router.navigate(['/login']);
    }
  }

  /**
   * Returns a promise that resolves to true if the user is authenticated.
   * Waits for the initial session check to complete.
   */
  async isAuthenticated(): Promise<boolean> {
    if (!this.loading()) {
      return !!this.user();
    }

    // Wait for loading to stay false
    return new Promise((resolve) => {
      const interval = setInterval(() => {
        if (!this.loading()) {
          clearInterval(interval);
          resolve(!!this.user());
        }
      }, 50);
    });
  }
}
