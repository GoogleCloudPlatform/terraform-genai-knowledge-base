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

import datetime
from unittest import mock
import os
import pytest

from dataclasses import dataclass

_PROJECT_ID = os.environ["PROJECT_ID"]
_OUTPUT_BUCKET = f"{_PROJECT_ID}_output"
_LOCATION = os.environ["REGION"]
_DATASET_ID = "summary_dataset"
_TABLE_ID = "summary_table"


@dataclass
class CloudEventDataMock:
    bucket: str
    name: str
    metageneration: str
    timeCreated: str
    updated: str

    def __getitem__(self, key):
        return self.__getattribute__(key)


@dataclass
class CloudEventMock:
    data: str
    id: str
    type: str

    def __getitem__(self, key):
        if key == "id":
            return self.id
        elif key == "type":
            return self.type
        else:
            raise RuntimeError(f"Unknown key: {key}")

    def get_json(self):
        return {
            "name": self.data.name,
            "kind": "storage#object",
            "id": self.id,
            "bucket": self.data.bucket,
            "timeCreated": self.data.timeCreated,
        }


@pytest.fixture
def cloud_event():
    return CloudEventMock(
        id="7631145714375969",
        type="google.cloud.storage.object.v1.finalized",
        data=CloudEventDataMock(
            bucket="velociraptor-16p1-mock-users-bucket",
            name="9404001v1.pdf",
            metageneration="1",
            timeCreated=f"{datetime.datetime.now().isoformat()}Z",
            updated=f"{datetime.datetime.now().isoformat()}Z",
        ),
    )


class RequestMock:
    def get_json(self):
        return {
            "name": "MOCK_REQUEST_NAME",
            "text": "abstract: mock text. conclusion: there is none",
        }


@pytest.fixture
def curl_request():
    return RequestMock()


@mock.patch.dict(
    os.environ,
    {
        "OUTPUT_BUCKET": _OUTPUT_BUCKET,
        "PROJECT_ID": _PROJECT_ID,
        "LOCATION": _LOCATION,
        "DATASET_ID": _DATASET_ID,
        "TABLE_ID": _TABLE_ID,
    },
    clear=True,
)
def test_function_entrypoint_cloud_event(cloud_event):
    from main import entrypoint

    result = entrypoint(cloud_event)
    assert "summary" in result


@mock.patch.dict(
    os.environ,
    {
        "OUTPUT_BUCKET": _OUTPUT_BUCKET,
        "PROJECT_ID": _PROJECT_ID,
        "LOCATION": _LOCATION,
        "DATASET_ID": _DATASET_ID,
        "TABLE_ID": _TABLE_ID,
    },
    clear=True,
)
def test_function_entrypoint_curl(curl_request):
    from main import entrypoint

    result = entrypoint(curl_request)
    assert "summary" in result
