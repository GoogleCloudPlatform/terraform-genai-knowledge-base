/**
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

output "neos_tutorial_url" {
  value       = "https://console.cloud.google.com/products/solutions/deployments?walkthrough_id=panels--sic--generative-ai-knowledge-base_toc"
  description = "The URL to launch the in-console tutorial for the Generative AI Knowledge Base solution"
}

output "predictions_notebook_url" {
  value       = "https://colab.research.google.com/github/GoogleCloudPlatform/terraform-genai-knowledge-base/blob/main/notebooks/model-predictions.ipynb"
  description = "The URL to open the notebook for model predictions in Colab"
}

output "unique_id" {
  value       = random_id.unique_id.hex
  description = "The unique ID for this deployment"
}

output "bucket_main_name" {
  value       = google_storage_bucket.main.name
  description = "The name of the main bucket created"
}

output "bucket_docs_name" {
  value       = google_storage_bucket.docs.name
  description = "The name of the docs bucket created"
}

output "documentai_processor_id" {
  value       = google_document_ai_processor.ocr.id
  description = "The full Document AI processor path ID"
}

output "firestore_database_name" {
  value       = google_firestore_database.main.name
  description = "The name of the Firestore database created"
}

output "docs_index_id" {
  value       = google_vertex_ai_index.docs.id
  description = "The ID of the docs index"
}

output "docs_index_endpoint_id" {
  value       = google_vertex_ai_index_endpoint.docs.id
  description = "The ID of the docs index endpoint"
}
