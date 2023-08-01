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
from unittest.mock import MagicMock, patch

from google.cloud import storage
from storage import upload_to_gcs


_BUCKET_NAME = os.environ["BUCKET"]
_FILE_NAME = "system-test/fake.text"


@patch.object(storage.Client, "get_bucket")
def test_upload_to_gcs_mock(mock_get_bucket):
    mock_blob = MagicMock(spec=storage.Blob)
    mock_bucket = MagicMock(spec=storage.Bucket)
    mock_bucket.blob.return_value = mock_blob
    mock_get_bucket.return_value = mock_bucket
    bucket_name = "fake-bucket"
    blob_name = "fake-blob"
    data = "fake-data"

    # Act
    upload_to_gcs(bucket_name, blob_name, data)

    # Assert
    mock_get_bucket.assert_called_with(bucket_name)
    mock_bucket.blob.assert_called_with(blob_name)
    mock_blob.upload_from_string.assert_called_with(data)
