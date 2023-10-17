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
import pytest
from datetime import datetime

from google.cloud import firestore

from firestore_collection import get_qas_count
from firestore_collection import write_qas_to_collection


_PROJECT_ID = os.environ["PROJECT_ID"]
# Make sure this is a test collection. It is entirely deleted in teardown.
_COLLECTION_NAME = os.environ["COLLECTION"]


@pytest.fixture
def populate_collection():
    db = firestore.Client(project=_PROJECT_ID)
    collection_ref = db.collection(_COLLECTION_NAME)
    question_1 = "Who is the Greek goddess of the hunt?"
    question_2 = "Which Israelite prophet lived at the time of King Ahab?"
    # TODO: Fix this to match correct DB schema
    data_rows = [
        {   
            "question": question_1,
            "answers": "Artemis",
        },
        {
            "question": question_2,
            "answer": "Elijah",
        },
    ]

    for d in data_rows:
        collection_ref.add(d, str(hash(d["question"])))

    yield


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def clean_collection(client: firestore.Client,
                     coll_ref: firestore.CollectionReference):
    client.recursive_delete(coll_ref)


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def test_write_qas_to_collection_it(capsys):
    # Arrange
    timestamp = datetime.now()
    question_1 = "Who is the Greek goddess of the hunt?"
    question_2 = "Which Israelite prophet lived at the time of King Ahab?"
    data_rows = [
        (question_1, "Artemis"),
        (question_2, "Elijah"),
    ]
    gcs_uri = "gs://i/am/a/test.pdf"

    client = firestore.Client()
    collection = client.collection(_COLLECTION_NAME)

    # Act
    try:
        write_qas_to_collection(
            project_id=_PROJECT_ID,
            collection_name=_COLLECTION_NAME,
            question_answer_pairs=data_rows,
            input_file_gcs_uri=gcs_uri,
            time_created=timestamp)

        # Assert
        assert capsys.readouterr().out == ""
        got_1 = collection.document(str(hash(question_1))).get()
        got_2 = collection.document(str(hash(question_2))).get()

        assert got_1.exists
        assert got_2.exists

    finally:
        # Clean up
        clean_collection(client, collection)


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def test_get_qas_count_it(capsys, populate_collection):
    # Act
    try:
        count = get_qas_count(
            project_id=_PROJECT_ID,
            collection_name=_COLLECTION_NAME)

        # Assert
        assert capsys.readouterr().out == ""
        assert count == 2

    finally:
        # Clean up
        client = firestore.Client(project=_PROJECT_ID)
        collection = client.collection(_COLLECTION_NAME)

        clean_collection(client, collection)
