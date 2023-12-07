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

# Required variables
variable "project_id" {
  description = "The Google Cloud project ID to deploy to"
  type        = string
  validation {
    condition     = var.project_id != ""
    error_message = "Error: project_id is required"
  }
}

# Optional variables
variable "bucket_docs" {
  description = "Google Cloud Storage bucket for documents"
  type        = string
  default     = ""
}

variable "bucket_main" {
  description = "Google Cloud Storage bucket for staging and dataset files"
  type        = string
  default     = ""
}

variable "storage_location" {
  description = "Cloud Storage buckets location"
  type        = string
  default     = "us-central1"
}

variable "webhook_name" {
  description = "Name of the Cloud Function webhook"
  type        = string
  default     = "webhook"
}

variable "webhook_location" {
  description = "Cloud Function location"
  type        = string
  default     = "us-central1"
}

variable "trigger_name" {
  description = "Name of the Cloud Function trigger"
  type        = string
  default     = "docs-trigger"
}

variable "vertexai_location" {
  description = "Vertex AI location"
  type        = string
  default     = "us-central1"
}

variable "documentai_processor_name" {
  description = "Document AI processor name"
  type        = string
  default     = "docs-processor"
}

variable "documentai_location" {
  description = "Document AI location"
  type        = string
  default     = "us"
}

variable "firestore_database_name" {
  description = "Firestore database name"
  type        = string
  default     = "docs-questions"
}

variable "firestore_location" {
  description = "Firestore location"
  type        = string
  default     = "nam5" # US
}

variable "enable_apis" {
  description = "Whether to enable APIs for the project."
  type        = bool
  default     = true
}

variable "disable_services_on_destroy" {
  description = "Whether project services will be disabled when the resources are destroyed."
  type        = bool
  default     = false
}

# Used for testing.
variable "webhook_path" {
  description = "Path to the webhook source directory"
  type        = string
  default     = "webhook"
}

