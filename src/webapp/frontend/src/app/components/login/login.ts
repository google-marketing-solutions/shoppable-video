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

import {CommonModule} from '@angular/common';
import {Component, inject, signal} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {Router} from '@angular/router';
import {AuthService} from '../../services/auth.service';

const PRODUCT_SUGGESTIONS_ROUTE = '/product-suggestions';

/**
 * Component for user login. Allows users to log in with email/password
 * or using their Google account. Redirects to product suggestions on successful login.
 */
@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
  ],
  templateUrl: './login.html',
  styleUrls: ['./login.scss'],
})
export class LoginComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  hidePassword = true;
  email = '';
  password = '';
  authError = signal<string | null>(null);

  constructor() {
    // Redirect if already logged in
    if (this.authService.user()) {
      this.router.navigate([PRODUCT_SUGGESTIONS_ROUTE]);
    }
  }

  async login() {
    this.authError.set(null);
    try {
      await this.authService.login(this.email, this.password);
      this.router.navigate([PRODUCT_SUGGESTIONS_ROUTE]);
    } catch (error: unknown) {
      if (error instanceof Error) {
        this.authError.set(error.message);
      } else {
        this.authError.set('An unknown error occurred');
      }
    }
  }

  async loginWithGoogle() {
    this.authError.set(null);
    try {
      await this.authService.loginWithGoogle();
      this.router.navigate([PRODUCT_SUGGESTIONS_ROUTE]);
    } catch (error: unknown) {
      if (error instanceof Error) {
        this.authError.set(error.message);
      } else {
        this.authError.set('An unknown error occurred');
      }
    }
  }
}
