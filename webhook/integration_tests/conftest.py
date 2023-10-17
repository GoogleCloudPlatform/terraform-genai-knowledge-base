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

import os
import pytest
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter, Or

_PROJECT_ID = os.environ["PROJECT_ID"]
_COLLECTION_NAME = os.environ["COLLECTION"]


@pytest.fixture()
def populate_collection():
    db = firestore.Client(project=_PROJECT_ID)
    collection_ref = db.collection(_COLLECTION_NAME)
    question_1 = "Who is the Greek goddess of the hunt?"
    question_2 = "Which Israelite prophet lived at the time of King Ahab?"

    filter_1 = FieldFilter("question", "==", question_1)
    filter_2 = FieldFilter("question", "==", question_2)

    or_filter = Or(filters=[filter_1, filter_2])
    docs = collection_ref.where(filter=or_filter).stream()

    docs_list = [d for d in docs]

    # If the collection is already populated with questions, just bail
    if len(docs_list) < 2:
        data_rows = [
            {
                "question": question_1,
                "answers": ["Artemis"],
            },
            {
                "question": question_2,
                "answers": ["Elijah"],
            },
        ]

        for d in data_rows:
            collection_ref.add(d, str(hash(d["question"])))

    yield
