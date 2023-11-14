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

import os
from google.cloud import vision
from google.api_core.operation import Operation
from unittest.mock import MagicMock, patch

import webhook.documentai_utils as documentai_utils

_PROJECT_ID = os.environ["PROJECT_ID"]
_BUCKET_NAME = os.environ["BUCKET"]
_OUTPUT_BUCKET = f"{_PROJECT_ID}_output"
_FILE_NAME = "9404001v1.pdf"


@patch.object(vision.ImageAnnotatorClient, "async_batch_annotate_files")
@patch.object(documentai_utils, "get_ocr_output_from_bucket")
def test_async_document_extract(mock_get_output, mock_annotate):
    want = "this is fake complete output"
    mock_annotate.return_value = MagicMock(spec=Operation)
    mock_get_output.return_value = want

    bucket = "my-fake-bucket"
    name = "fake.pdf"
    output_bucket = "my-fake-output-bucket"
    timeout = 0
    gcs_source_uri = f"gs://{bucket}/{name}"
    gcs_destination_uri = f"gs://{output_bucket}/ocr/"

    feature = vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)

    gcs_source = vision.GcsSource(uri=gcs_source_uri)
    input_config = vision.InputConfig(
        gcs_source=gcs_source, mime_type="application/pdf"
    )

    gcs_destination = vision.GcsDestination(uri=gcs_destination_uri)
    output_config = vision.OutputConfig(gcs_destination=gcs_destination, batch_size=2)

    async_request = vision.AsyncAnnotateFileRequest(
        features=[feature], input_config=input_config, output_config=output_config
    )

    # Act
    got = documentai_utils.async_document_extract(bucket, name, output_bucket, timeout)

    # Assert
    assert want == got
    mock_annotate.assert_called_once()
    mock_annotate.assert_called_with(requests=[async_request])
