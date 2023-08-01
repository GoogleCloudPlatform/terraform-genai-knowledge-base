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
import os

import document_extract

_PROJECT_ID = os.environ["PROJECT_ID"]
_BUCKET_NAME = os.environ["BUCKET"]
_OUTPUT_BUCKET = f"{_PROJECT_ID}_output"
_FILE_NAME = "9404001v1.pdf"


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def test_async_document_extract_system(capsys):
    out = document_extract.async_document_extract(
        _BUCKET_NAME, _FILE_NAME, _OUTPUT_BUCKET
    )
    assert "Abstract" in out
