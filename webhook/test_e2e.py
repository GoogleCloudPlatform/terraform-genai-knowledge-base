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

from collections.abc import Iterator
import datetime
import os
import pytest
import subprocess
import uuid

from google.cloud import documentai
from google.cloud import firestore
from google.cloud import storage

import storage_utils
import firestore_utils
from process_document import DATASET_COLLECTION, OUTPUT_NAME, process_document

UUID = uuid.uuid4().hex[:6]
print(f"{UUID=}")

LOCATION = "us-central1"


def run_cmd(*cmd: str) -> None:
    print(f">> {cmd}")
    subprocess.run(cmd, check=True)


@pytest.fixture(scope="session")
def project() -> str:
    run_cmd("gcloud", "config", "list")
    project = os.environ["PROJECT_ID"]
    print(f"{project=}")
    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    run_cmd("gcloud", "config", "set", "project", project)
    return project


@pytest.fixture(scope="session")
def bucket_name(project: str) -> Iterator[str]:
    storage_client = storage.Client()
    bucket_name = f"jss-22p1-test-{UUID}"
    print(f"{bucket_name=}")
    bucket = storage_client.create_bucket(bucket_name, location=LOCATION)
    yield bucket_name
    print(f"deleting {bucket_name=}")
    bucket.delete(force=True)


@pytest.fixture(scope="session")
def docai_processor_id(project: str) -> Iterator[str]:
    docai_client = documentai.DocumentProcessorServiceClient()
    docai_client.common_location_path(project, "us")
    processor = docai_client.create_processor(
        parent=docai_client.common_location_path(project, "us"),
        processor=documentai.Processor(
            display_name=f"jss-22p1-test-{UUID}",
            type_="OCR_PROCESSOR",
        ),
    )
    yield processor.name
    print(f"deleting {processor.name=}")
    operation = docai_client.delete_processor(name=processor.name)
    operation.result()


@pytest.fixture(scope="session")
def database() -> Iterator[str]:
    firestore_database = f"jss-22p1-test-{UUID}"
    print(f"{firestore_database=}")
    run_cmd(
        "gcloud",
        "alpha",
        "firestore",
        "databases",
        "create",
        f"--database={firestore_database}",
        "--location=nam5",  # US
    )
    yield firestore_database
    run_cmd(
        "gcloud",
        "alpha",
        "firestore",
        "databases",
        "delete",
        f"--database={firestore_database}",
        "--quiet",
    )


def test_end_to_end(
    bucket_name: str,
    docai_processor_id: str,
    database: str,
) -> None:
    process_document(
        event_id=f"test-event-id-{UUID}",
        input_bucket="arxiv-dataset",
        input_name="arxiv/cmp-lg/pdf/9410/9410009v1.pdf",
        mime_type="application/pdf",
        docai_prcessor_id=docai_processor_id,
        time_uploaded=datetime.datetime.now(),
        output_bucket=bucket_name,
        database=database,
    )

    # Make sure we have a non-empty dataset.
    with storage_utils.read(bucket_name, OUTPUT_NAME) as f:
        lines = [line.strip() for line in f]
        print(f"dataset {len(lines)=}")
        assert len(lines) > 0, "expected a non-empty dataset in the output bucket"

    # Make sure the Firestore database is populated.
    db = firestore.Client(database=database)
    entries = list(firestore_utils.read(db, DATASET_COLLECTION))
    print(f"database {len(entries)=}")
    assert len(entries) == len(lines), "database entries do not match the dataset"
