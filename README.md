# Generative AI Enterprise Knowledge base

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
![Enterprise Knowledge Base using Generative AI]()
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
- [Enterprise Knowledge Base using Generative AI]()
{TODO: Update link}

## Deployment Duration
Configuration: 2 mins
Deployment: 8 mins

## Cost
[Cost Details](https://cloud.google.com/products/calculator/#id=78888c9b-02ac-4130-9327-fecd7f4cfb11)

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| bucket\_docs | Google Cloud Storage bucket for documents | `string` | `""` | no |
| bucket\_main | Google Cloud Storage bucket for staging and dataset files | `string` | `""` | no |
| disable\_services\_on\_destroy | Whether project services will be disabled when the resources are destroyed. | `bool` | `false` | no |
| documentai\_location | Document AI location | `string` | `"us"` | no |
| documentai\_processor\_name | Document AI processor name | `string` | `"docs-processor"` | no |
| firestore\_location | Firestore location | `string` | `"nam5"` | no |
| firestore\_name | Firestore database name | `string` | `""` | no |
| project\_id | The Google Cloud project ID to deploy to | `string` | n/a | yes |
| storage\_location | Cloud Storage buckets location | `string` | `"us-central1"` | no |
| trigger\_name | Name of the Cloud Function trigger | `string` | `"docs-trigger"` | no |
| vertexai\_location | Vertex AI location | `string` | `"us-central1"` | no |
| webhook\_location | Cloud Function location | `string` | `"us-central1"` | no |
| webhook\_name | Name of the Cloud Function webhook | `string` | `"webhook"` | no |
| webhook\_path | Path to the webhook source directory | `string` | `"webhook"` | no |

## Outputs

| Name | Description |
|------|-------------|
| documentai\_processor\_id | The full Document AI processor path ID |
| genai\_doc\_summary\_colab\_url | The URL to launch the notebook tutorial for the Generateive AI Document Summarization Solution |
| neos\_walkthrough\_url | The URL to launch the in-console tutorial for the Generative AI Document Summarization solution |

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

## Contributing

Refer to the [contribution guidelines](./docs/CONTRIBUTING.md) for
information on contributing to this module.

[iam-module]: https://registry.terraform.io/modules/terraform-google-modules/iam/google
[project-factory-module]: https://registry.terraform.io/modules/terraform-google-modules/project-factory/google
[terraform-provider-gcp]: https://www.terraform.io/docs/providers/google/index.html
[terraform]: https://www.terraform.io/downloads.html

## Security Disclosures

Please see our [security disclosure process](./SECURITY.md).
