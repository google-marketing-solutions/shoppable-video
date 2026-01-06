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
import {Injectable} from '@angular/core';
import {Observable, Subject} from 'rxjs';

/**
 * Service for handling data operations, including fetching data from a
 * backend API and sharing data between different parts of the application.
 */
@Injectable({
  providedIn: 'root',
})
export class DataService {
  private apiUrl = 'http://localhost:3000/api';
  constructor(private http: HttpClient) {}

  getData<T>(): Observable<T> {
    return this.http.get<T>(`${this.apiUrl}/data`);
  }

  private dataSubject = new Subject<unknown>();
  data$ = this.dataSubject.asObservable();
  sendData(data: unknown) {
    this.dataSubject.next(data);
  }
}
