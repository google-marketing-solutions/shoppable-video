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

import {inject, Injectable, signal} from '@angular/core';
import {Router} from '@angular/router';

/** Minimal interface for Firebase user. */
interface FirebaseUser {
  getIdToken(): Promise<string>;
}

/** Minimal type for Firebase auth provider. */
type FirebaseAuthProvider = object;

/** Minimal interface for Firebase auth service. */
interface FirebaseAuth {
  onAuthStateChanged(callback: (user: FirebaseUser | null) => void): () => void;
  signInWithEmailAndPassword(email: string, password: string): Promise<void>;
  signInWithPopup(provider: FirebaseAuthProvider): Promise<void>;
  signOut(): Promise<void>;
  currentUser: FirebaseUser | null;
}

/** Minimal interface for Firebase namespace. */
interface FirebaseNamespace {
  auth: {
    (): FirebaseAuth;
    GoogleAuthProvider: new () => FirebaseAuthProvider;
  };
}

declare const firebase: FirebaseNamespace;

/**
 * Service for handling user authentication.
 * This service provides methods for logging in with email/password or Google,
 * logging out, checking authentication status, and getting the user's ID token.
 * It uses Firebase Authentication under the hood.
 */
@Injectable({
  providedIn: 'root',
})
export class AuthService {
  user = signal<FirebaseUser | null>(null);
  loading = signal<boolean>(true);

  router = inject(Router);

  constructor() {
    this.initAuthListener();
  }

  private initAuthListener() {
    firebase.auth().onAuthStateChanged((user: FirebaseUser | null) => {
      this.user.set(user);
      this.loading.set(false);
    });
  }

  async login(email: string, password: string): Promise<void> {
    await firebase.auth().signInWithEmailAndPassword(email, password);
  }

  async loginWithGoogle(): Promise<void> {
    const provider = new firebase.auth.GoogleAuthProvider();
    await firebase.auth().signInWithPopup(provider);
  }

  async logout(): Promise<void> {
    await firebase.auth().signOut();
    this.router.navigate(['/login']);
  }

  isAuthenticated(): Promise<boolean> {
    return new Promise((resolve) => {
      if (!this.loading()) {
        resolve(!!this.user());
      } else {
        const unsubscribe = firebase
          .auth()
          .onAuthStateChanged((user: FirebaseUser | null) => {
            unsubscribe();
            resolve(!!user);
          });
      }
    });
  }

  async getIdToken(): Promise<string | null> {
    const user = this.user();
    if (user) {
      return user.getIdToken();
    }
    const currentUser = firebase.auth().currentUser;
    if (currentUser) {
      return currentUser.getIdToken();
    }
    return null;
  }
}
