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

## Prerequisites

Authenticate:

```sh
gcloud auth application-default login
```

Make sure you `cd` into this directory before running the tests.

```sh
cd webhook/
```

Install the dependencies:

```sh
# Specify the project ID to use for the test.
export PROJECT_ID=my-project

# Install the dependencies on a virtual environment.
python -m venv env
source env/bin/activate
pip install -r requirements.txt -r requirements-test.txt
```

## Running the tests end-to-end

To run the tests creating and destroying all resources, run:

```sh
# Ignore deprecation warnings for cleaner outputs.
python -m pytest -v -s -W ignore::DeprecationWarning
```

## Running the tests with persistent resources

⚠️ WARNING: reusing resources from a previous run may lead to unexpected behavior.
    For example, files created from a previous run may cause tests to succeed 
    even if they should fail.

To avoid creating and destroying resources when debugging, you can use
persistent resources.

```sh
export TEST_UUID=$USER
export TEST_SKIP_DESTROY=1
```

Then, run the tests:

```sh
python -m pytest -v -s -W ignore::DeprecationWarning

# If you already have created the resources, you can skip all Terraform steps.
export TEST_SKIP_INIT=1
export TEST_SKIP_APPLY=1
```

Once you're finished, delete the resources manually:

```sh
terraform -chdir=.. destroy -auto-approve -var=project_id=$PROJECT_ID
```

"""

from collections.abc import Iterator
import datetime
import json
import os
import pytest
import subprocess
import uuid
from typing import Any

from google.cloud import firestore

import storage_utils
import firestore_utils
from process_document import DATASET_COLLECTION, OUTPUT_NAME, process_document

PROJECT_ID = os.environ["PROJECT_ID"]
UUID = os.environ.get("TEST_UUID", uuid.uuid4().hex[:6])


def run_cmd(*cmd: str, **kwargs: Any) -> subprocess.CompletedProcess:
    print(f">> {cmd}")
    return subprocess.run(cmd, check=True, **kwargs)


@pytest.fixture(scope="session")
def resources() -> Iterator[dict]:
    print("---")
    print(f"{PROJECT_ID=}")
    print(f"{UUID=}")
    resources = {
        "bucket_main": os.environ.get("TEST_BUCKET_MAIN", f"{PROJECT_ID}-{UUID}"),
        "documentai_processor_name": os.environ.get(
            "TEST_DOCUMENTAI_PROCESSOR_NAME", f"test-webhook-{UUID}"
        ),
        "firestore_name": os.environ.get(
            "TEST_FIRESTORE_DATABASE_NAME", f"test-webhook-{UUID}"
        ),
    }
    print(f"resources={json.dumps(resources, indent=2)}")
    if not os.environ.get("TEST_SKIP_INIT"):
        run_cmd("terraform", "-chdir=..", "init", "-input=false")
    if not os.environ.get("TEST_SKIP_APPLY"):
        run_cmd(
            "terraform",
            "-chdir=..",
            "apply",
            "-input=false",
            "-auto-approve",
            f"-var=project_id={PROJECT_ID}",
            *[f"-var={name}={value}" for name, value in resources.items()],
            "-target=google_storage_bucket.main",
            "-target=google_document_ai_processor.ocr",
            "-target=google_firestore_database.database",
        )
    yield resources
    if not os.environ.get("TEST_SKIP_DESTROY"):
        run_cmd(
            "terraform",
            "-chdir=..",
            "destroy",
            "-input=false",
            "-auto-approve",
            f"-var=project_id={PROJECT_ID}",
        )


@pytest.fixture(scope="session")
def outputs(resources: dict) -> dict[str, str]:
    p = run_cmd("terraform", "-chdir=..", "output", "-json", stdout=subprocess.PIPE)
    outputs = {
        name: value["value"]
        for name, value in json.loads(p.stdout.decode("utf-8")).items()
    }
    print(f"{outputs=}")
    return outputs


def test_end_to_end(resources: dict, outputs: dict[str, str]) -> None:
    print(f">> process_document")
    process_document(
        event_id=f"webhook-test-{UUID}",
        input_bucket="arxiv-dataset",
        input_name="arxiv/cmp-lg/pdf/9410/9410009v1.pdf",
        mime_type="application/pdf",
        time_uploaded=datetime.datetime.now(),
        docai_prcessor_id=outputs["documentai_processor_id"],
        output_bucket=resources["bucket_main"],
        database=resources["firestore_name"],
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
    db = firestore.Client(database=resources["firestore_name"])
    entries = list(firestore_utils.read(db, DATASET_COLLECTION))
    print(f"database {len(entries)=}")
    assert len(entries) == len(lines), "database entries do not match the dataset"
