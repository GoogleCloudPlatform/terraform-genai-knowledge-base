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
import sys
import uuid

from google.cloud import documentai
from google.cloud import firestore
from google.cloud import storage

import storage_utils
import firestore_utils
from process_document import DATASET_COLLECTION, OUTPUT_NAME, process_document

LOCATION = "us-central1"
FIRESTORE_LOCATION = "nam5"  # US


def run_cmd(*cmd: str) -> None:
    print(f">> {cmd}")
    subprocess.run(cmd, check=True)


@pytest.fixture(scope="session")
def project() -> str:
    project = os.environ["PROJECT_ID"]
    print(f"{project=}")
    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    run_cmd("gcloud", "config", "set", "project", project)
    return project


@pytest.fixture(scope="session")
def unique_name(project: str) -> str:
    unique_name = f"{project}-py{sys.version_info.major}{sys.version_info.minor}-{uuid.uuid4().hex[:6]}"
    print(f"{unique_name=}")
    return unique_name


@pytest.fixture(scope="session")
def bucket_name(unique_name: str) -> Iterator[str]:
    storage_client = storage.Client()
    bucket_name = unique_name
    print(f"{bucket_name=}")
    bucket = storage_client.create_bucket(bucket_name, location=LOCATION)
    yield bucket_name
    print(f"deleting {bucket_name=}")
    bucket.delete(force=True)


@pytest.fixture(scope="session")
def docai_processor_id(project: str, unique_name: str) -> Iterator[str]:
    docai_client = documentai.DocumentProcessorServiceClient()
    docai_client.common_location_path(project, "us")
    processor = docai_client.create_processor(
        parent=docai_client.common_location_path(project, "us"),
        processor=documentai.Processor(
            display_name=unique_name,
            type_="OCR_PROCESSOR",
        ),
    )
    yield processor.name
    print(f"deleting {processor.name=}")
    docai_client.delete_processor(name=processor.name).result()


@pytest.fixture(scope="session")
def firestore_database(unique_name: str) -> Iterator[str]:
    firestore_database = unique_name
    print(f"{firestore_database=}")
    run_cmd(
        "gcloud",
        "alpha",
        "firestore",
        "databases",
        "create",
        f"--database={firestore_database}",
        f"--location={FIRESTORE_LOCATION}",
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
    unique_name: str,
    bucket_name: str,
    docai_processor_id: str,
    firestore_database: str,
) -> None:
    process_document(
        event_id=unique_name,
        input_bucket="arxiv-dataset",
        input_name="arxiv/cmp-lg/pdf/9410/9410009v1.pdf",
        mime_type="application/pdf",
        docai_prcessor_id=docai_processor_id,
        time_uploaded=datetime.datetime.now(),
        output_bucket=bucket_name,
        database=firestore_database,
    )

    # Make sure we have a non-empty dataset.
    with storage_utils.read(bucket_name, OUTPUT_NAME) as f:
        lines = [line.strip() for line in f]
        print(f"dataset {len(lines)=}")
        assert len(lines) > 0, "expected a non-empty dataset in the output bucket"

    # Make sure the Firestore database is populated.
    db = firestore.Client(database=firestore_database)
    entries = list(firestore_utils.read(db, DATASET_COLLECTION))
    print(f"database {len(entries)=}")
    assert len(entries) == len(lines), "database entries do not match the dataset"
