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
import json
import os
import pytest
import subprocess
from typing import Any

from google.cloud import firestore

import storage_utils
import firestore_utils
from process_document import DATASET_COLLECTION, OUTPUT_NAME, process_document

PROJECT_ID = os.environ["PROJECT_ID"]


def run_cmd(*cmd: str, **kwargs: Any) -> subprocess.CompletedProcess:
    print(f">> {cmd}")
    return subprocess.run(cmd, check=True, **kwargs)


@pytest.fixture(scope="session")
def outputs() -> Iterator[dict[str, str]]:
    print("---")
    print(f"{PROJECT_ID=}")
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
            "-var=unique_names=true",
            "-target=google_storage_bucket.main",
            "-target=google_document_ai_processor.ocr",
            "-target=google_firestore_database.main",
        )
    p = run_cmd("terraform", "-chdir=..", "output", "-json", stdout=subprocess.PIPE)
    outputs = {
        name: value["value"]
        for name, value in json.loads(p.stdout.decode("utf-8")).items()
    }
    print(f"{outputs=}")
    yield outputs
    if not os.environ.get("TEST_SKIP_DESTROY"):
        run_cmd(
            "terraform",
            "-chdir=..",
            "destroy",
            "-input=false",
            "-auto-approve",
            f"-var=project_id={PROJECT_ID}",
        )


def test_end_to_end(outputs: dict[str, str]) -> None:
    print(">> process_document")
    process_document(
        event_id=f"webhook-test-{outputs['unique_id']}",
        input_bucket="arxiv-dataset",
        input_name="arxiv/cmp-lg/pdf/9410/9410009v1.pdf",
        mime_type="application/pdf",
        time_uploaded=datetime.datetime.now(),
        docai_prcessor_id=outputs["documentai_processor_id"],
        output_bucket=outputs["bucket_main_name"],
        database=outputs["firestore_database_name"],
        force_reprocess=True,
    )

    # Make sure we have a non-empty dataset.
    print(">> Checking output bucket")
    with storage_utils.read(outputs["bucket_main_name"], OUTPUT_NAME) as f:
        lines = [line.strip() for line in f]
        print(f"dataset {len(lines)=}")
        assert len(lines) > 0, "expected a non-empty dataset in the output bucket"

    # Make sure the Firestore database is populated.
    print(">> Checking Firestore database")
    db = firestore.Client(database=outputs["firestore_database_name"])
    entries = list(firestore_utils.read(db, DATASET_COLLECTION))
    print(f"database {len(entries)=}")
    assert len(entries) == len(lines), "database entries do not match the dataset"
