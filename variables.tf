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

variable "project_id" {
  description = "The Google Cloud project ID to deploy to"
  type        = string
  validation {
    condition     = var.project_id != ""
    error_message = "Error: project_id is required"
  }
}

variable "bucket_name" {
  description = "The name of the bucket to create"
  type        = string
  default     = "genai-doc-summary-webhook"
}

variable "region" {
  description = "Google Cloud region"
  type        = string
  default     = "us-central1"
}

variable "webhook_name" {
  description = "Name of the webhook"
  type        = string
  default     = "webhook"
}

variable "webhook_path" {
  description = "Path to the webhook directory"
  type        = string
  default     = "webhook"
}

variable "gcf_timeout_seconds" {
  description = "GCF execution timeout"
  type        = number
  default     = 900
}

variable "time_to_enable_apis" {
  description = "Wait time to enable APIs in new projects"
  type        = string
  default     = "180s"
}

variable "init" {
  type        = bool
  description = "Initialize resource or not"
}

variable "collection_fields" {
  description = "collection id with respect to its fields"
  type        = map(any)
}