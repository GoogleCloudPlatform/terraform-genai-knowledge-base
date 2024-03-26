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
    "compute.googleapis.com",
    "cloudfunctions.googleapis.com",
    "config.googleapis.com",
    "iam.googleapis.com",
    "documentai.googleapis.com",
    "eventarc.googleapis.com",
    "firestore.googleapis.com",
    "run.googleapis.com",
    "serviceusage.googleapis.com",
    "storage-api.googleapis.com",
    "storage.googleapis.com",
  ]
}

resource "random_id" "unique_id" {
  byte_length = 3
}

locals {
  bucket_main_name   = var.unique_names ? "${var.project_id}-main-${random_id.unique_id.hex}" : "${var.project_id}-main"
  bucket_docs_name   = var.unique_names ? "${var.project_id}-docs-${random_id.unique_id.hex}" : "${var.project_id}-docs"
  webhook_name       = var.unique_names ? "webhook-${random_id.unique_id.hex}" : "webhook"
  webhook_sa_name    = var.unique_names ? "webhook-service-account-${random_id.unique_id.hex}" : "webhook-service-account"
  trigger_name       = var.unique_names ? "trigger-${random_id.unique_id.hex}" : "trigger"
  trigger_sa_name    = var.unique_names ? "trigger-service-account-${random_id.unique_id.hex}" : "trigger-service-account"
  ocr_processor_name = var.unique_names ? "ocr-processor-${random_id.unique_id.hex}" : "ocr-processor"
  docs_index_name    = var.unique_names ? "docs-index-${random_id.unique_id.hex}" : "docs-index"
  firestore_name     = var.unique_names ? "knowledge-base-${random_id.unique_id.hex}" : "knowledge-base"
}

#-- Cloud Storage buckets --#
resource "google_storage_bucket" "main" {
  project                     = module.project_services.project_id
  name                        = local.bucket_main_name
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "docs" {
  project                     = module.project_services.project_id
  name                        = local.bucket_docs_name
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
}

#-- Cloud Function webhook --#
resource "google_cloudfunctions2_function" "webhook" {
  project  = module.project_services.project_id
  name     = local.webhook_name
  location = var.region

  build_config {
    runtime           = "python312"
    entry_point       = "on_cloud_event"
    docker_repository = google_artifact_registry_repository.webhook_images.id
    source {
      storage_source {
        bucket = google_storage_bucket.main.name
        object = google_storage_bucket_object.webhook_staging.name
      }
    }
  }

  service_config {
    available_memory      = "4G"
    timeout_seconds       = 300 # 5 minutes
    service_account_email = google_service_account.webhook.email
    environment_variables = {
      PROJECT_ID        = module.project_services.project_id
      VERTEXAI_LOCATION = var.region
      OUTPUT_BUCKET     = google_storage_bucket.main.name
      DOCAI_PROCESSOR   = google_document_ai_processor.ocr.id
      DOCAI_LOCATION    = google_document_ai_processor.ocr.location
      DATABASE          = google_firestore_database.main.name
      INDEX_ID          = google_vertex_ai_index.docs.id
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
  account_id   = local.webhook_sa_name
  display_name = "Cloud Functions webhook service account"
}

resource "google_artifact_registry_repository" "webhook_images" {
  project       = module.project_services.project_id
  location      = var.region
  repository_id = "webhook-images"
  format        = "DOCKER"
}

data "archive_file" "webhook_staging" {
  type       = "zip"
  source_dir = var.webhook_path
  excludes = [
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "env",
  ]
  output_path = abspath("./.tmp/webhook.zip")
}

resource "google_storage_bucket_object" "webhook_staging" {
  name   = "webhook-staging/${data.archive_file.webhook_staging.output_base64sha256}.zip"
  bucket = google_storage_bucket.main.name
  source = data.archive_file.webhook_staging.output_path
}

#-- Eventarc trigger --#
resource "google_eventarc_trigger" "trigger" {
  project         = module.project_services.project_id
  location        = var.region
  name            = local.trigger_name
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
      region  = var.region
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
  account_id   = local.trigger_sa_name
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
  display_name = local.ocr_processor_name
  type         = "OCR_PROCESSOR"
}

#-- Firestore --#
resource "google_firestore_database" "main" {
  project         = module.project_services.project_id
  name            = local.firestore_name
  location_id     = var.firestore_location
  type            = "FIRESTORE_NATIVE"
  deletion_policy = "DELETE"
}

#-- Vertex AI Vector Search --#
resource "google_vertex_ai_index" "docs" {
  project             = module.project_services.project_id
  region              = var.region
  display_name        = local.docs_index_name
  index_update_method = "STREAM_UPDATE"
  metadata {
    contents_delta_uri = "gs://${google_storage_bucket.main.name}/vector-search-index"
    config {
      dimensions                  = 768
      approximate_neighbors_count = 150
      shard_size                  = "SHARD_SIZE_SMALL"
      distance_measure_type       = "SQUARED_L2_DISTANCE"
      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 1000
          leaf_nodes_to_search_percent = 10
        }
      }
    }
  }
  depends_on = [google_storage_bucket_object.index_initial]
}

resource "google_vertex_ai_index_endpoint" "docs" {
  project                 = module.project_services.project_id
  region                  = var.region
  display_name            = "docs-index-endpoint"
  public_endpoint_enabled = true
}

resource "google_storage_bucket_object" "index_initial" {
  bucket = google_storage_bucket.main.name
  name   = "vector-search-index/initial.json"
  source = abspath("initial-index.json")
}
