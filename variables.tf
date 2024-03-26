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

# Jump Start Solution variables.
variable "project_id" {
  description = "The Google Cloud project ID to deploy to"
  type        = string
  validation {
    condition     = var.project_id != ""
    error_message = "Error: project_id is required."
  }
}

variable "region" {
  description = "The Google Cloud region to deploy to"
  type        = string
  default     = "us-central1"
}

# Optional variables
variable "documentai_location" {
  description = "Document AI location, see https://cloud.google.com/document-ai/docs/regions"
  type        = string
  default     = "us"
}

variable "firestore_location" {
  description = "Firestore location, see https://firebase.google.com/docs/firestore/locations"
  type        = string
  default     = "nam5" # US
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

variable "unique_names" {
  description = "Whether to use unique names for resources"
  type        = bool
  default     = true
}
