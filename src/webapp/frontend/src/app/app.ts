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

import {Component, computed, effect, inject, signal} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatListModule} from '@angular/material/list';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatSelectModule} from '@angular/material/select';
import {RouterLink, RouterOutlet} from '@angular/router';
import {AuthService} from './services/auth.service';
import {DataService} from './services/data.service';
import {Customer} from './models';

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
    MatSidenavModule,
    MatToolbarModule,
    MatIconModule,
    MatButtonModule,
    MatListModule,
    RouterLink,
    MatFormFieldModule,
    MatSelectModule,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private authService = inject(AuthService);
  private dataService = inject(DataService);

  protected readonly title = signal('shoppable-video');
  isLoggedIn = this.authService.user;
  accessibleCustomers = signal<Customer[]>([]);
  hasPlatformAccount = computed(() =>
    this.accessibleCustomers().some((c) => c.is_platform_customer_id)
  );
  // Retrieves the active account ID from local storage to be used as
  // login-customer-id for API calls
  activeAccount = this.dataService.activeAccount;

  constructor() {
    effect(() => {
      if (this.isLoggedIn()) {
        // When logged in, retrieve user's directly accessible Ads accounts.
        this.dataService.getAccessibleCustomers().subscribe({
          next: (response) => {
            this.accessibleCustomers.set(response.data);
            console.log(
              'Accessible customers loaded. Has platform account:',
              this.hasPlatformAccount()
            );

            // Set default active account if none selected.
            if (!this.activeAccount()) {
              const platformAcc = response.data.find(
                (c) => c.is_platform_customer_id
              );
              // If user has access to the platform MCC ID used in the project
              // (i.e. the account the project is configured to use), use that.
              if (platformAcc) {
                this.dataService.setActiveAccount(
                  String(platformAcc.customer_id)
                );
              } else if (response.data.length > 0) {
                this.dataService.setActiveAccount(
                  String(response.data[0].customer_id)
                );
              }
            }
            console.log(
              `[Auth] Selected login-customer-id context: ${
                this.activeAccount() || 'Unset (Default MCC)'
              }`
            );
          },
          error: (err) =>
            console.error('Failed to load accessible customers', err),
        });
      }
    });
  }

  onAccountChange(customerId: string) {
    this.dataService.setActiveAccount(customerId);
  }

  logout() {
    this.authService.logout().catch((err) => console.error(err));
  }
}
