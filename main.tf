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

module "project_services" {
  source                      = "terraform-google-modules/project-factory/google//modules/project_services"
  version                     = "~> 14.4"
  disable_services_on_destroy = var.disable_services_on_destroy

  project_id = var.project_id

  activate_apis = [
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "documentai.googleapis.com",
    "eventarc.googleapis.com",
    "firestore.googleapis.com",
    "run.googleapis.com",
    "storage.googleapis.com",
  ]
}

locals {
  bucket_docs    = var.bucket_docs == "" ? "${var.project_id}-docs" : var.bucket_docs
  bucket_main    = var.bucket_main == "" ? "${var.project_id}-main" : var.bucket_main
  firestore_name = var.firestore_name == "" ? "docs-questions-${random_id.unique_id.hex}" : var.firestore_name
}

resource "random_id" "unique_id" {
  byte_length = 3
}

#-- Cloud Storage buckets --#
resource "google_storage_bucket" "docs" {
  project                     = module.project_services.project_id
  name                        = local.bucket_docs
  location                    = var.storage_location
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "main" {
  project                     = module.project_services.project_id
  name                        = local.bucket_main
  location                    = var.storage_location
  force_destroy               = true
  uniform_bucket_level_access = true
}

#-- Cloud Function webhook --#
resource "google_cloudfunctions2_function" "webhook" {
  project  = module.project_services.project_id
  name     = var.webhook_name
  location = var.webhook_location

  build_config {
    runtime     = "python312"
    entry_point = "on_cloud_event"
    source {
      storage_source {
        bucket = google_storage_bucket.main.name
        object = google_storage_bucket_object.webhook_staging.name
      }
    }
  }

  service_config {
    available_memory      = "1G"
    service_account_email = google_service_account.webhook.email
    environment_variables = {
      PROJECT_ID        = module.project_services.project_id
      VERTEXAI_LOCATION = var.vertexai_location
      OUTPUT_BUCKET     = google_storage_bucket.main.name
      DOCAI_PROCESSOR   = google_document_ai_processor.ocr.id
      DOCAI_LOCATION    = google_document_ai_processor.ocr.location
      DATABASE          = google_firestore_database.database.name
    }
  }
}

resource "google_project_iam_member" "webhook" {
  project = module.project_services.project_id
  member  = google_service_account.webhook.member
  for_each = toset([
    "roles/aiplatform.serviceAgent", # https://cloud.google.com/iam/docs/service-agents
    "roles/datastore.user",          # https://cloud.google.com/datastore/docs/access/iam
    "roles/documentai.apiUser",      # https://cloud.google.com/document-ai/docs/access-control/iam-roles
  ])
  role = each.key
}
resource "google_service_account" "webhook" {
  project      = module.project_services.project_id
  account_id   = "webhook-service-account"
  display_name = "Cloud Functions webhook service account"
}

data "archive_file" "webhook_staging" {
  type        = "zip"
  source_dir  = var.webhook_path
  output_path = abspath("./.tmp/webhook.zip")
}

resource "google_storage_bucket_object" "webhook_staging" {
  name   = "staging/webhook.${data.archive_file.webhook_staging.output_base64sha256}.zip"
  bucket = google_storage_bucket.main.name
  source = data.archive_file.webhook_staging.output_path
}

#-- Eventarc trigger --#
resource "google_eventarc_trigger" "trigger" {
  project         = module.project_services.project_id
  location        = var.webhook_location
  name            = var.trigger_name
  service_account = google_service_account.trigger.email

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.docs.name
  }

  destination {
    cloud_run_service {
      service = google_cloudfunctions2_function.webhook.name
      region  = var.webhook_location
    }
  }
}

resource "google_project_iam_member" "trigger" {
  project = module.project_services.project_id
  member  = google_service_account.trigger.member
  for_each = toset([
    "roles/eventarc.eventReceiver", # https://cloud.google.com/eventarc/docs/access-control
    "roles/run.invoker",            # https://cloud.google.com/run/docs/reference/iam/roles
  ])
  role = each.key
}
resource "google_service_account" "trigger" {
  project      = module.project_services.project_id
  account_id   = "trigger-service-account"
  display_name = "Eventarc trigger service account"
}

#-- Cloud Storage Eventarc agent --#
resource "google_project_iam_member" "gcs_account" {
  project = module.project_services.project_id
  member  = "serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"
  role    = "roles/pubsub.publisher" # https://cloud.google.com/pubsub/docs/access-control
}
data "google_storage_project_service_account" "gcs_account" {
  project = module.project_services.project_id
}

resource "google_project_iam_member" "eventarc_agent" {
  project = module.project_services.project_id
  member  = "serviceAccount:${google_project_service_identity.eventarc_agent.email}"
  role    = "roles/eventarc.serviceAgent" # https://cloud.google.com/iam/docs/service-agents
}
resource "google_project_service_identity" "eventarc_agent" {
  provider = google-beta
  project  = module.project_services.project_id
  service  = "eventarc.googleapis.com"
}

#-- Document AI --#
resource "google_document_ai_processor" "ocr" {
  project      = module.project_services.project_id
  location     = var.documentai_location
  display_name = var.documentai_processor_name
  type         = "OCR_PROCESSOR"
}

#-- Firestore --#
resource "google_firestore_database" "database" {
  project         = module.project_services.project_id
  name            = local.firestore_name
  location_id     = var.firestore_location
  type            = "FIRESTORE_NATIVE"
  deletion_policy = "DELETE"
}
