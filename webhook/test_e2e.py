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
import json
import os
import subprocess
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from google.cloud import storage  # type: ignore
from google.cloud import firestore  # type: ignore

from main import process_document

PROJECT_ID = os.environ["PROJECT_ID"]
LOCATION = os.environ.get("LOCATION", "us-central1")

# Persistent resource because it takes ~30 minutes to deploy.
VECTOR_SEARCH_INDEX_ID = os.environ.get("VECTOR_SEARCH_INDEX_ID", "3421719768057511936")


def run_cmd(*cmd: str, **kwargs: Any) -> subprocess.CompletedProcess:
    """Run a command in a subprocess.

    Args:
        *cmd: The command to run.
        **kwargs: Additional keyword arguments to pass to subprocess.run().

    Returns:
        The completed subprocess.
    """
    print(f">> {cmd}")
    return subprocess.run(cmd, check=True, **kwargs)


@pytest.fixture(scope="session")
def terraform_outputs() -> Iterator[dict[str, str]]:
    """Yield the Terraform outputs.

    Yields:
        The Terraform outputs as a dictionary.
    """
    print("---")
    print(f"{PROJECT_ID=}")
    if not os.environ.get("TEST_SKIP_TERRAFORM"):
        run_cmd("terraform", "-chdir=..", "init", "-input=false")
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
    outputs = {name: value["value"] for name, value in json.loads(p.stdout.decode("utf-8")).items()}
    print(f"{outputs=}")
    yield outputs
    if not os.environ.get("TEST_SKIP_TERRAFORM"):
        run_cmd(
            "terraform",
            "-chdir=..",
            "destroy",
            "-input=false",
            "-auto-approve",
            f"-var=project_id={PROJECT_ID}",
        )


def test_end_to_end(terraform_outputs: dict[str, str]) -> None:
    """End-to-end test.

    Args:
        terraform_outputs: The Terraform outputs.
    """
    print(">> process_document")
    process_document(
        event_id=f"webhook-test-{uuid4().hex[:6]}",
        input_bucket="arxiv-dataset",
        filename="arxiv/cmp-lg/pdf/9410/9410009v1.pdf",
        mime_type="application/pdf",
        time_uploaded=datetime.datetime.now(),
        project=PROJECT_ID,
        location=LOCATION,
        docai_processor_id=terraform_outputs["documentai_processor_id"],
        output_bucket=terraform_outputs["bucket_main_name"],
        database=terraform_outputs["firestore_database_name"],
        index_id=VECTOR_SEARCH_INDEX_ID,
    )

    # Make sure we have a non-empty dataset.
    print(">> Checking output bucket")
    storage_client = storage.Client(project=PROJECT_ID)
    output_bucket = terraform_outputs["bucket_main_name"]
    with storage_client.get_bucket(output_bucket).blob("dataset.jsonl").open("r") as f:
        lines = [line.strip() for line in f]
        print(f"dataset {len(lines)=}")
        assert len(lines) > 0, "expected a non-empty dataset in the output bucket"

    # Make sure the Firestore database is populated.
    print(">> Checking Firestore database")
    db = firestore.Client(project=PROJECT_ID, database=terraform_outputs["firestore_database_name"])
    entries = list(db.collection("dataset").stream())
    print(f"database {len(entries)=}")
    assert len(entries) == len(lines), "database entries do not match the dataset"
