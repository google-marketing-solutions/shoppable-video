# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

output "generate_embedding_function_url" {
  value = module.functions_generate_embedding.function_url
}

output "analyze_video_function_url" {
  value = module.functions_analyze_video.function_url
}

output "product_embeddings_queue_name" {
  value = module.tasks_product_embeddings_queue.queue_name
}

output "video_analysis_queue_name" {
  value = module.tasks_video_analysis_queue.queue_name
}
