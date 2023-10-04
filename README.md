# Generative AI Extractive Question and Answers

## Description
### Tagline
Create a chatbot powered by an extractive QA LLM model.

### Detailed
This solution showcases how to extract question & answer pairs out of documents
using Generative AI. It provides end-to-end demonstration of QA extraction and
fine-tuning of a large language model (LLM) on Vertex AI. Along the way, the
solution utilizes Cloud Vision Optical Character Recognition (OCR), Firestore,
Vertex AI Pipelines, and Cloud Run.

### PreDeploy
To deploy this blueprint you must have an active billing account and billing permissions.

## Architecture
![Extractive QA using Generative AI]()
<!-- TODO: Update the image with the correct diagram -->

The solution has three separate, but related workflows: ingestion, training,
and fulfillment.

### Ingestion

1. The developer uploads a PDF to a Cloud Storage bucket, using `gsutil`, the Console UI, or 
   the Cloud Storage client libraries.
1. The uploaded PDF file is sent to a Cloud Function. This function handles PDF file processing.
1. The Cloud Function uses Cloud Vision OCR to extract all text from the PDF file.
1. The Cloud Function uses Vertex AI’s LLM API to extract question and answer pairs from the extracted text.
1. The Cloud Function stores the extracted question and answer pair in a Firestore collection.

### Training

1. Once the Firestore collection reaches a certain size (% 10), the Cloud 
   Function triggers a Vertex AI Pipeline.
1. The Vertex AI Pipeline fine-tunes a LLM on the QAs stored in the Firestore collection.
1. The Vertex AI Pipeline deploys the tuned LLM to a Vertex AI endpoint.

### Fulfillment

1. A Cloud Run instance hosts a simple chatbot user interface, where the chatbot
   queries the tuned LLM.
1. Users can ask the chatbot questions, and the chatbot respond with an
   answer derived from the source Q&As. 

## Prerequisites
- [Google Cloud Project](https://cloud.google.com/resource-manager/docs/creating-managing-projects)

## Documentation
- [Generative AI Extractive Q & A]()
{TODO: Update link}

## Deployment Duration
Configuration: 1 mins
Deployment: 10 mins

## Cost
[Cost Details](https://cloud.google.com/products/calculator/#id=78888c9b-02ac-4130-9327-fecd7f4cfb11)

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| bucket\_name | The name of the bucket to create | `string` | `"genai-doc-summary-webhook"` | no |
| gcf\_timeout\_seconds | GCF execution timeout | `number` | `900` | no |
| project\_id | The Google Cloud project ID to deploy to | `string` | n/a | yes |
| region | Google Cloud region | `string` | `"us-central1"` | no |
| time\_to\_enable\_apis | Wait time to enable APIs in new projects | `string` | `"180s"` | no |
| webhook\_name | Name of the webhook | `string` | `"webhook"` | no |
| webhook\_path | Path to the webhook directory | `string` | `"webhook"` | no |

## Outputs

| Name | Description |
|------|-------------|
| genai\_doc\_summary\_colab\_url | The URL to launch the notebook tutorial for the Generative AI Document Summarization Solution |
| neos\_walkthrough\_url | The URL to launch the in-console tutorial for the Generative AI Document Summarization solution |

<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->

## Requirements

These sections describe requirements for using this module.

### Software

The following dependencies must be available:

- [Terraform][terraform] v0.13
- [Terraform Provider for GCP][terraform-provider-gcp] plugin v3.0

### Service Account

A service account with the following roles must be used to provision
the resources of this module:

- Storage Admin: `roles/storage.admin`

### APIs

A project with the following APIs enabled must be used to host the
resources of this module:

- Google Cloud Storage JSON API: `storage-api.googleapis.com`

## Contributing

Refer to the [contribution guidelines](./docs/CONTRIBUTING.md) for
information on contributing to this module.

[iam-module]: https://registry.terraform.io/modules/terraform-google-modules/iam/google
[project-factory-module]: https://registry.terraform.io/modules/terraform-google-modules/project-factory/google
[terraform-provider-gcp]: https://www.terraform.io/docs/providers/google/index.html
[terraform]: https://www.terraform.io/downloads.html

## Security Disclosures

Please see our [security disclosure process](./SECURITY.md).
