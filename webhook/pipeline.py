# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
from kfp.v2.dsl import component, pipeline
from google.cloud import aiplatform

"""About this pipeline:

The @component and @pipeline functions defined in this file have been
pre-compiled for you. The resulting DAG / YAML template is stored in the
'extractive-qa.yaml' file. The `get_qas_from_collection()` and `tuning`
functions are provided here for your reference.

If you want to edit this pipeline or make your own, follow the directions
provided here:

https://cloud.google.com/vertex-ai/docs/pipelines/build-pipeline
"""


@component(packages_to_install=["google-cloud-firestore", "google-cloud-storage"])
def get_qas_from_collection(
    *,
    project_id: str,
    database_name: str,
    collection_name: str,
    bucket_name: str,
) -> str:
    """Gets all QA sets as a list of dict objects.

    Arguments:
      project_id: the project that contains this database
      collection_name: the collection to get the Q&A pairs from

    Returns:
        All documents (QAs) in the collection. Each document is a dict object.
    """
    import json
    from google.cloud import firestore
    from google.cloud import storage

    db = firestore.Client(project=project_id, database=database_name)
    collection_ref = db.collection(collection_name)
    docs_iter = collection_ref.stream()

    all_qas = []

    for doc in docs_iter:
        qa = doc.to_dict()
        all_qas.append(qa)

    # TODO: Switch to GCS FUSE
    gcs_qa_dir = f"gs://{bucket_name}/extractive-qa"
    gcs_qa_file = f"{gcs_qa_dir}/qas.json"

    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(f"extractive-qa/qas.json")

    blob.upload_from_string(json.dumps(all_qas))

    return gcs_qa_file


@component(
    base_image="python:3.9",
    packages_to_install=[
        "google-cloud-aiplatform",
        "google-cloud-storage",
        "importlib-metadata",
        "pandas",
        "pyyaml",
    ],
)
def tuning(
    *,
    project_id: str,
    location: str = "us-central1",
    gcs_qa_file: str = "",
    tuned_model_name: str = "",
) -> None:
    """Tune a new model, based on Q&A data stored in a Firestore collection.

    Args:
        project_id: Google Cloud project ID, used to initialize Vertex AI
        location: Google Cloud region, used to initialize Vertex AI
        gcs_qa_file: Cloud Storage FUSE URI of a file containing questions & answers
        tuned_model_name: name of a previously tuned model
    """
    import json
    import pandas as pd

    from google.cloud import storage

    import vertexai
    from vertexai.preview.language_models import TextGenerationModel

    vertexai.init(
        project=project_id,
        location=location,
    )

    if tuned_model_name == "":
        model = TextGenerationModel.from_pretrained("google/text-bison@001")

    storage_client = storage.Client(project=project_id)
    uri_paths = gcs_qa_file.split("/")
    bucket = storage_client.bucket(uri_paths[2])
    blob_path = "/".join(uri_paths[3:])
    blob = bucket.blob(blob_path)
    jsonl_as_str = blob.download_as_string()

    qas = json.loads(jsonl_as_str)
    jsonl_dataset = [
        {"input_text": qa["question"], "output_text": qa["answers"][0]["answer"]}
        for qa in qas
    ]

    job = model.tune_model(
        training_data=pd.DataFrame(data=jsonl_dataset),
        # Optional:
        train_steps=10,
        tuning_job_location="europe-west4",
        tuned_model_location=location,
    )
    return job


@pipeline(name="extractive-qa-pipeline", description="Fine-tunes an extractive QA LLM")
def tuning_pipeline(
    project_id: str, database_name: str, collection_name: str, bucket_name: str
):
    """Use questions & answers stored in Firestore to finetune a Vertex LLM.

    Arguments:
        project_id: the Google Cloud project ID for this run
        collection_name: the Firestore collection that stores the Q&As
        bucket_name: the Cloud Storage bucket to store artifacts
    """
    firestore_operation = get_qas_from_collection(
        project_id=project_id,
        database_name=database_name,
        collection_name=collection_name,
        bucket_name=bucket_name,
    )

    tuning(project_id=project_id, gcs_qa_file=firestore_operation.output)


def start_tuning_pipeline(
    *,
    project_id: str,
    database_name: str,
    location: str = "us-central1",
    collection_name: str,
    bucket_name: str,
):
    aiplatform.init(project=project_id, location=location)

    timestamp = datetime.now().isoformat().replace(":", "-").replace(".", "-")

    job = aiplatform.PipelineJob(
        display_name=f"extractive-qa-{timestamp}-job",
        template_path="extractive-qa.yaml",
        pipeline_root=f"gs://{bucket_name}/extractive-qa/pipeline_root/",
        parameter_values={
            "project_id": project_id,
            "database_name": database_name,
            "collection_name": collection_name,
            "bucket_name": bucket_name,
        },
        enable_caching=False,
    )
    job.submit()
    return job.name
