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

import {inject} from '@angular/core';
import {CanActivateFn, Router, Routes} from '@angular/router';
import {AuthService} from './services/auth.service';

/**
 * Checks user is auth'd
 */
const AuthGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  return authService.isAuthenticated().then((isAuth) => {
    if (isAuth) {
      return true;
    } else {
      router.navigate(['/login']);
      return false;
    }
  });
};

/**
 * The application routes.
 */
export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./components/login/login').then((m) => m.LoginComponent),
  },
  {
    path: 'product-suggestions',
    loadComponent: () =>
      import('./components/all-results/all-results').then((m) => m.AllResults),
    canActivate: [AuthGuard],
  },
  {
    path: 'video/:video_location/:video_analysis_uuid',
    loadComponent: () =>
      import('./components/video-details/video-details').then(
        (m) => m.VideoDetails
      ),
    canActivate: [AuthGuard],
  },
  {
    path: 'status/:status',
    loadComponent: () =>
      import('./components/status/status').then((m) => m.StatusComponent),
    canActivate: [AuthGuard],
  },
  {
    path: 'status',
    loadComponent: () =>
      import('./components/status/status').then((m) => m.StatusComponent),
    canActivate: [AuthGuard],
  },
  {path: '', redirectTo: '/product-suggestions', pathMatch: 'full'},
];
