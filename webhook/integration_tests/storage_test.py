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

from google.cloud import storage
from storage import upload_to_gcs


_BUCKET_NAME = os.environ["BUCKET"]
_FILE_NAME = "system-test/fake.text"


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def test_upload_to_gcs():
    want = datetime.datetime.now().isoformat()

    upload_to_gcs(bucket=_BUCKET_NAME, name=_FILE_NAME, data=want)

    client = storage.Client()
    bucket = client.bucket(_BUCKET_NAME)
    blob = bucket.blob(_FILE_NAME)
    got = str(blob.download_as_text())
    assert want in got
