/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import {Video} from '../models';

/**
 * Gets the display title for a video.
 * Priorities:
 * 1. Metadata title
 * 2. Filename from GCS URI
 * 3. Video ID
 * 4. UUID
 */
export function getVideoTitle(video: Video | null | undefined): string {
  if (!video) {
    return '';
  }

  if (video.metadata?.title) {
    return video.metadata.title;
  }

  if (video.gcsUri) {
    const parts = video.gcsUri.split('/');
    return parts[parts.length - 1];
  }

  return video.videoId || video.uuid;
}
