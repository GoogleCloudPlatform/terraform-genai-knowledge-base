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
    "serviceusage.googleapis.com",
    "vision.googleapis.com",
    "cloudfunctions.googleapis.com",
    "serviceusage.googleapis.com",
    "artifactregistry.googleapis.com",
    "eventarc.googleapis.com",
    "bigquery.googleapis.com",
    "aiplatform.googleapis.com",
    "storage.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "iam.googleapis.com",
    "notebooks.googleapis.com",
    "dataform.googleapis.com",
  ]
}

data "google_project" "project" {
  project_id = var.project_id
  depends_on = [
    module.project_services,
  ]
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

resource "null_resource" "previous_time" {}

# Gate till APIs are enabled
resource "time_sleep" "wait_for_apis" {
  depends_on = [
    null_resource.previous_time,
    module.project_services,
    google_project_iam_member.eventarc_sa_role,
  ]

  create_duration = var.time_to_enable_apis
}

resource "random_id" "rand" {
  byte_length = 4
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

resource "google_service_account" "webhook" {
  project      = var.project_id
  account_id   = "webhook-service-account"
  display_name = "Serverless Webhooks Service Account"
  depends_on = [
    module.project_services,
  ]
}

resource "google_project_iam_member" "webhook_sa_roles" {
  project = var.project_id
  for_each = toset([
    "roles/run.invoker",
    "roles/cloudfunctions.invoker",
    "roles/storage.admin",
    "roles/logging.logWriter",
    "roles/artifactregistry.reader",
    "roles/bigquery.dataEditor",
    "roles/aiplatform.user",
  ])
  role   = each.key
  member = "serviceAccount:${google_service_account.webhook.email}"
}

resource "google_cloudfunctions2_function" "webhook" {
  project  = var.project_id
  name     = var.webhook_name
  location = var.region

  build_config {
    runtime     = "python310"
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
      PROJECT_ID    = var.project_id
      LOCATION      = var.region
      OUTPUT_BUCKET = google_storage_bucket.output.name
      DATASET_ID    = google_bigquery_dataset.default.dataset_id
      TABLE_ID      = google_bigquery_table.default.table_id
    }
  }
  depends_on = [
    module.project_services,
    time_sleep.wait_for_apis,
    google_project_iam_member.webhook_sa_roles,

  ]
}

resource "google_bigquery_dataset" "default" {
  dataset_id = "summary_dataset"
  project    = var.project_id
  depends_on = [
    module.project_services,
  ]
}

resource "google_bigquery_table" "default" {
  dataset_id          = google_bigquery_dataset.default.dataset_id
  table_id            = "summary_table"
  project             = var.project_id
  deletion_protection = false

  schema = <<EOF
[
  {
    "name": "bucket",
    "type": "STRING",
    "description": "Source bucket of artifact"
  },
  {
    "name": "filename",
    "type": "STRING",
    "description": "Filename of the source artifact"
  },
  {
    "name": "extracted_text",
    "type": "STRING",
    "description": "Text extracted from the source artifact"
  },
  {
    "name": "summary_uri",
    "type": "STRING",
    "description": "The Storage URI of the complete document text"
  },
  {
    "name": "complete_text_uri",
    "type": "STRING",
    "description": "The Storage URI of the complete document text"
  },
  {
    "name": "summary",
    "type": "STRING",
    "description": "Text summary generated by the LLM"
  },
  {
    "name": "timestamp",
    "type": "TIMESTAMP",
    "description": "TeTimestamp that the processing occurred on"
  }
]
EOF
}

resource "google_storage_bucket" "uploads" {
  project                     = var.project_id
  name                        = "${var.project_id}_uploads"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "output" {
  project                     = var.project_id
  name                        = "${var.project_id}_output"
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

resource "google_service_account" "upload_trigger" {
  project      = var.project_id
  account_id   = "upload-trigger-service-account"
  display_name = "Eventarc Service Account"
  depends_on = [
    module.project_services,
  ]
}

resource "google_project_iam_member" "event_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.upload_trigger.email}"
  depends_on = [
    module.project_services,
  ]
}

resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.upload_trigger.email}"
  depends_on = [
    module.project_services,
  ]
}

data "google_storage_project_service_account" "gcs_account" {
  project    = var.project_id
  depends_on = [time_sleep.wait_for_apis]
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

resource "google_eventarc_trigger" "summarization" {
  project  = var.project_id
  name     = "terraformdev"
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
  service_account = google_service_account.upload_trigger.email
  depends_on = [
    google_project_iam_member.event_receiver,
    google_project_iam_member.run_invoker,
    google_project_iam_member.pubsub_publisher,
  ]
}
