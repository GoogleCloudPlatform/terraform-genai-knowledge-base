# Generative AI Knowledge Base

## Description
### Tagline
Fine tune an LLM model to answer questions from your documents.

### Detailed
This solution showcases how to extract question & answer pairs out of documents
using Generative AI. It provides an end-to-end demonstration of QA extraction and
fine-tuning of a large language model (LLM) on Vertex AI. Along the way, the
solution utilizes Document AI Character Recognition (OCR), Firestore,
Vertex AI Studio, and Cloud Functions.

The resources that this module creates are:

- Create a GCS bucket with the provided name

### PreDeploy
To deploy this blueprint you must have an active billing account and billing permissions.

## Architecture
![Knowledge Base using Generative AI]()
<!-- TODO: Update the image with the correct diagram -->

The solution has three separate, but related workflows: ingestion, training,
and fulfillment.

### Ingestion
1. The developer uploads a document like a PDF to a Cloud Storage bucket, using `gsutil`,
   the Console UI, or the Cloud Storage client libraries.
1. Uploading a document file triggers a Cloud Function that processes the document.
   - Uses Document AI OCR to extract all text from the document file.
   - Uses Vertex AI LLM API to extract question and answer pairs from the document text.
   - Stores the extracted question and answer pairs in a Firestore collection.
   - Generates a fine tuning dataset from the Firestore collection.

### Fine tuning
1. When satisified with the fine tuning dataset, the developer launches a fine tuning job on Vertex AI.
1. The fine tuning job deploys a tuned model to an endpoint when the job is complete.

### Fulfillment
1. Ask queries to the tuned model using Vertex AI Studio, and compare it with the foundation model.

## Prerequisites
- [Google Cloud Project](https://cloud.google.com/resource-manager/docs/creating-managing-projects)

## Documentation
- [Knowledge Base using Generative AI]()
{TODO: Update link}

## Deployment Duration
Configuration: 2 mins
Deployment: 8 mins

## Cost
[Cost Details](https://cloud.google.com/products/calculator-legacy#id=94ab5d75-4134-410f-b2d0-350762ae2588)

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| disable\_services\_on\_destroy | Whether project services will be disabled when the resources are destroyed. | `bool` | `false` | no |
| documentai\_location | Document AI location, see https://cloud.google.com/document-ai/docs/regions | `string` | `"us"` | no |
| firestore\_location | Firestore location, see https://firebase.google.com/docs/firestore/locations | `string` | `"nam5"` | no |
| project\_id | The Google Cloud project ID to deploy to | `string` | n/a | yes |
| region | The Google Cloud region to deploy to | `string` | `"us-central1"` | no |
| webhook\_path | Path to the webhook source directory | `string` | `"webhook"` | no |

## Outputs

| Name | Description |
|------|-------------|
| bucket\_docs\_name | The name of the docs bucket created |
| bucket\_main\_name | The name of the main bucket created |
| documentai\_processor\_id | The full Document AI processor path ID |
| firestore\_database\_name | The name of the Firestore database created |
| neos\_walkthrough\_url | The URL to launch the in-console tutorial for the Generative AI Document Summarization solution |
| unique\_id | The unique ID for this deployment |

<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->

## Requirements

These sections describe requirements for using this module.

### Software

The following dependencies must be available:

- [Terraform][terraform] v0.13
- [Terraform Provider for GCP][terraform-provider-gcp] plugin v5.8

### Service Account

A service account with the following roles must be used to provision
the resources of this module:

- Storage Admin: `roles/storage.admin`

The [Project Factory module][project-factory-module] and the
[IAM module][iam-module] may be used in combination to provision a
service account with the necessary roles applied.

### APIs

A project with the following APIs enabled must be used to host the
resources of this module:

- Google Cloud Storage JSON API: `storage-api.googleapis.com`

The [Project Factory module][project-factory-module] can be used to
provision a project with the necessary APIs enabled.

## Contributing

Refer to the [contribution guidelines](./docs/CONTRIBUTING.md) for
information on contributing to this module.

[iam-module]: https://registry.terraform.io/modules/terraform-google-modules/iam/google
[project-factory-module]: https://registry.terraform.io/modules/terraform-google-modules/project-factory/google
[terraform-provider-gcp]: https://www.terraform.io/docs/providers/google/index.html
[terraform]: https://www.terraform.io/downloads.html

## Security Disclosures

Please see our [security disclosure process](./SECURITY.md).
