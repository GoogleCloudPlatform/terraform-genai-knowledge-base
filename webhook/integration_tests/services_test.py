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

import backoff
import datetime
import os

from google.auth import default
from google.cloud import storage

from bigquery import write_summarization_to_table
from document_extract import async_document_extract
from model_tuning import tuning
from storage import upload_to_gcs
from utils import clean_text

_PROJECT_ID = os.environ["PROJECT_ID"]
_CREDENTIALS, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
_BUCKET_NAME = os.environ["BUCKET"]
_OUTPUT_BUCKET = f"{_PROJECT_ID}_output"
_DATASET_ID = "summary_dataset"
_TABLE_ID = "summary_table"
_FILE_NAME = "9404001v1.pdf"
_MODEL_NAME = "text-bison@001"


def check_blob_exists(bucket, filename) -> bool:
    client = storage.Client()
    bucket = client.bucket(bucket)
    blob = bucket.blob(filename)
    return blob.exists()


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def test_up16_services():
    extracted_text = async_document_extract(
        _BUCKET_NAME, _FILE_NAME, output_bucket=_OUTPUT_BUCKET
    )

    assert "Abstract" in extracted_text

    complete_text_filename = (
        f'system-test/{_FILE_NAME.replace(".pdf", "")}_fulltext.txt'
    )
    upload_to_gcs(
        _OUTPUT_BUCKET,
        complete_text_filename,
        extracted_text,
    )

    assert check_blob_exists(_OUTPUT_BUCKET, complete_text_filename)

    # TODO(erschmid): replace truncate with better solution
    extracted_text_ = clean_text(extracted_text)
    tuning_dataset = tuning(
        credentials=_CREDENTIALS,
        project_id=_PROJECT_ID,
        model_name=_MODEL_NAME,
        temperature=0.2,
        max_decode_steps=1024,
        top_p=0.8,
        top_k=40,
        text=extracted_text_,
        location="us-central1",
    )
    assert tuning_dataset != ""

    output_filename = f'system-test/{_FILE_NAME.replace(".pdf", "")}_summary.txt'
    upload_to_gcs(
        _OUTPUT_BUCKET,
        output_filename,
        summary,
    )

    assert check_blob_exists(_OUTPUT_BUCKET, output_filename)

    errors = write_summarization_to_table(
        project_id=_PROJECT_ID,
        dataset_id=_DATASET_ID,
        table_id=_TABLE_ID,
        bucket=_BUCKET_NAME,
        filename=output_filename,
        complete_text=extracted_text,
        complete_text_uri=complete_text_filename,
        summary=summary,
        summary_uri=output_filename,
        timestamp=datetime.datetime.now(),
    )

    assert len(errors) == 0
