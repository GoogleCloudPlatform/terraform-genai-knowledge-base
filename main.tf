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
  version                     = "~> 14.2"
  disable_services_on_destroy = false

  project_id = var.project_id

  activate_apis = [
    # cloudresourcemanager.googleapis.com is a prerequisite
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "dataform.googleapis.com",
    "documentai.googleapis.com",
    "eventarc.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "notebooks.googleapis.com",
    "run.googleapis.com",
    "serviceusage.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
    "vision.googleapis.com",
  ]
}

locals {
  database_name = "question-answering-${random_id.random_code.hex}"
}

resource "random_id" "random_code" {
  byte_length = 4
}

resource "random_id" "rand" {
  byte_length = 4
}

data "google_project" "project" {
  project_id = var.project_id
  depends_on = [
    module.project_services,
  ]
}

resource "null_resource" "previous_time" {}

#-- Cloud Storage buckets --#
resource "google_storage_bucket" "uploads" {
  project                     = var.project_id
  name                        = "${var.project_id}-uploads"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "output" {
  project                     = var.project_id
  name                        = "${var.project_id}-output"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "main" {
  project                     = var.project_id
  name                        = "${var.bucket_name}-${random_id.rand.hex}"
  location                    = "US"
  uniform_bucket_level_access = true
}

#-- Cloud Function webhook --#
resource "google_cloudfunctions2_function" "webhook" {
  project  = var.project_id
  name     = var.webhook_name
  location = var.region

  build_config {
    runtime     = "python312"
    entry_point = "entrypoint"
    source {
      storage_source {
        bucket = "${var.bucket_name}-${random_id.rand.hex}"
        object = google_storage_bucket_object.webhook.name
      }
    }
  }

  service_config {
    service_account_email            = google_service_account.webhook.email
    max_instance_count               = 5
    available_memory                 = "4G"
    available_cpu                    = 1
    max_instance_request_concurrency = 5
    timeout_seconds                  = var.gcf_timeout_seconds
    environment_variables = {
      PROJECT_ID      = var.project_id
      LOCATION        = var.region
      OUTPUT_BUCKET   = google_storage_bucket.output.name
      DOCAI_PROCESSOR = google_document_ai_processor.document_processor.name
      DATABASE        = local.database_name
      COLLECTION      = var.collection_name
    }
  }
  depends_on = [
    module.project_services,
    time_sleep.wait_for_apis,
    google_document_ai_processor.document_processor,
    google_project_iam_member.webhook_sa_roles,
  ]
}

resource "google_service_account" "webhook" {
  project      = var.project_id
  account_id   = "webhook-service-account"
  display_name = "Serverless webhook service account"
  depends_on = [
    module.project_services,
  ]
}

resource "google_project_iam_member" "webhook_sa_roles" {
  project = var.project_id
  for_each = toset([
    "roles/aiplatform.serviceAgent",  # https://cloud.google.com/vertex-ai/docs/general/access-control
    "roles/datastore.user",           # https://cloud.google.com/datastore/docs/access/iam
    "roles/documentai.apiUser",       # https://cloud.google.com/document-ai/docs/access-control/iam-roles
  ])
  role   = each.key
  member = "serviceAccount:${google_service_account.webhook.email}"
}

resource "google_document_ai_processor" "document_processor" {
  project  = var.project_id
  location = "us"
  display_name = "document-processor"
  type = "OCR_PROCESSOR"
}

data "archive_file" "webhook" {
  type        = "zip"
  source_dir  = var.webhook_path
  output_path = abspath("./.tmp/${var.webhook_name}.zip")
}

resource "google_storage_bucket_object" "webhook" {
  name   = "${var.webhook_name}.${data.archive_file.webhook.output_base64sha256}.zip"
  bucket = google_storage_bucket.main.name
  source = data.archive_file.webhook.output_path
}

#-- EventArc trigger --#
resource "google_eventarc_trigger" "trigger" {
  project  = var.project_id
  name     = "qa-eventarc-trigger"
  location = var.region
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.uploads.name
  }
  destination {
    cloud_run_service {
      service = google_cloudfunctions2_function.webhook.name
      region  = var.region
    }
  }
  service_account = google_service_account.trigger.email
  depends_on = [
    google_project_iam_member.trigger_sa_roles,
  ]
}

resource "google_service_account" "trigger" {
  project      = var.project_id
  account_id   = "trigger-service-account"
  display_name = "EventArc trigger service account"
  depends_on = [
    module.project_services,
  ]
}

resource "google_project_iam_member" "trigger_sa_roles" {
  project  = var.project_id
  for_each = toset([
    "roles/eventarc.eventReceiver",
    "roles/run.invoker",
  ])
  role   = each.key
  member = "serviceAccount:${google_service_account.trigger.email}"
}

resource "google_project_iam_member" "pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"
  depends_on = [
    module.project_services,
    data.google_storage_project_service_account.gcs_account,
  ]
}

data "google_storage_project_service_account" "gcs_account" {
  project    = var.project_id
  depends_on = [time_sleep.wait_for_apis]
}

resource "google_project_service_identity" "eventarc" {
  provider = google-beta
  project = data.google_project.project.project_id
  service = "eventarc.googleapis.com"
  depends_on = [
    module.project_services,
  ]
}

resource "google_project_iam_member" "eventarc_sa_role" {
  project = data.google_project.project.project_id
  role    = "roles/eventarc.serviceAgent"
  member  = "serviceAccount:${google_project_service_identity.eventarc.email}"
}

#-- Firestore database --#
resource "google_firestore_database" "database" {
  count       = var.init ? 1 : 0
  project     = var.project_id
  name        = local.database_name
  location_id = "nam5" # US
  type        = "FIRESTORE_NATIVE"
}

#-- Wait until the APIs are enabled --#
resource "time_sleep" "wait_for_apis" {
  create_duration = var.time_to_enable_apis
  depends_on = [
    null_resource.previous_time,
    module.project_services,
    google_project_iam_member.eventarc_sa_role,
  ]
}

# resource "google_service_account" "upload_trigger" {
#   project      = var.project_id
#   account_id   = "upload-trigger-service-account"
#   display_name = "Eventarc Service Account"
#   depends_on = [
#     module.project_services,
#   ]
# }

# resource "google_project_iam_member" "event_receiver" {
#   project = var.project_id
#   role    = "roles/eventarc.eventReceiver"
#   member  = "serviceAccount:${google_service_account.upload_trigger.email}"
#   depends_on = [
#     module.project_services,
#   ]
# }

# resource "google_project_iam_member" "run_invoker" {
#   project = var.project_id
#   role    = "roles/run.invoker"
#   member  = "serviceAccount:${google_service_account.upload_trigger.email}"
#   depends_on = [
#     module.project_services,
#   ]
# }

# resource "google_project_iam_member" "pubsub_publisher" {
#   project = var.project_id
#   role    = "roles/pubsub.publisher"
#   member  = "serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"
#   depends_on = [
#     module.project_services,
#     data.google_storage_project_service_account.gcs_account,
#   ]
# }
