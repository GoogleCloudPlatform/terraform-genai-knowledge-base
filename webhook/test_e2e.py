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

"""End-to-end test of the process_document function.

```sh
export PROJECT_ID=my-project
export UUID=$USER
python -m pytest -v -s -W ignore::DeprecationWarning

export SKIP_INIT=1
export SKIP_APPLY=1
export SKIP_DESTROY=1

unset SKIP_INIT
unset SKIP_APPLY
unset SKIP_DESTROY
```
"""

from collections.abc import Iterator
import datetime
import json
import os
import pytest
import subprocess
import sys
import uuid

from google.cloud import firestore

import storage_utils
import firestore_utils
from process_document import DATASET_COLLECTION, OUTPUT_NAME, process_document

PROJECT_ID = os.environ["PROJECT_ID"]
UUID = os.environ.get("UUID", uuid.uuid4().hex[:6])


def run_cmd(*cmd: str) -> None:
    print(f">> {cmd}")
    subprocess.run(cmd, check=True)


@pytest.fixture(scope="session")
def resources() -> Iterator[dict]:
    print(f"{PROJECT_ID=}")
    print(f"{UUID=}")
    resources = {
        "bucket_main": f"{PROJECT_ID}-{UUID}",
        "documentai_processor_name": f"test-webhook-{UUID}",
        "firestore_database_name": f"test-webhook-{UUID}",
    }
    print(f"resources={json.dumps(resources, indent=2)}")
    if not os.environ.get("SKIP_INIT"):
        run_cmd("terraform", "-chdir=..", "init")
    if not os.environ.get("SKIP_APPLY"):
        run_cmd(
            "terraform",
            "-chdir=..",
            "apply",
            "-auto-approve",
            f"-var=project_id={PROJECT_ID}",
            "-var=enable_apis=false",
            *[f"-var={name}={value}" for name, value in resources.items()],
            "-target=google_storage_bucket.main",
            "-target=google_document_ai_processor.document_processor",
            "-target=google_firestore_database.database",
        )
    yield resources
    if not os.environ.get("SKIP_DESTROY"):
        run_cmd("terraform", "-chdir=..", "destroy", "-auto-approve")


def test_end_to_end(resources: dict) -> None:
    print(f">> process_document")
    process_document(
        event_id=f"webhook-test-{UUID}",
        input_bucket="arxiv-dataset",
        input_name="arxiv/cmp-lg/pdf/9410/9410009v1.pdf",
        mime_type="application/pdf",
        time_uploaded=datetime.datetime.now(),
        docai_prcessor_id=resources["documentai_processor_name"],
        output_bucket=resources["bucket_main"],
        database=resources["firestore_database_name"],
        force_reprocess=True,
    )

    # Make sure we have a non-empty dataset.
    print(f">> Checking output bucket")
    with storage_utils.read(resources["bucket_main"], OUTPUT_NAME) as f:
        lines = [line.strip() for line in f]
        print(f"dataset {len(lines)=}")
        assert len(lines) > 0, "expected a non-empty dataset in the output bucket"

    # Make sure the Firestore database is populated.
    print(f">> Checking Firestore database")
    db = firestore.Client(database=resources["firestore_database_name"])
    entries = list(firestore_utils.read(db, DATASET_COLLECTION))
    print(f"database {len(entries)=}")
    assert len(entries) == len(lines), "database entries do not match the dataset"
