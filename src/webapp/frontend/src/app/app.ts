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
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatListModule} from '@angular/material/list';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatToolbarModule} from '@angular/material/toolbar';
import {RouterLink, RouterOutlet} from '@angular/router';
import {AuthService} from './services/auth.service';

/**
 * The root component of the Shoppable Video Frontend application.
 * This component serves as the main entry point for the application,
 * managing the overall layout and routing.
 */
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    RouterOutlet,
    CommonModule,
    MatSidenavModule,
    MatToolbarModule,
    MatIconModule,
    MatButtonModule,
    MatListModule,
    RouterLink,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private authService = inject(AuthService);

  protected readonly title = signal('shoppable-video');
  isLoggedIn = this.authService.user;

  logout() {
    this.authService.logout();
  }
}
