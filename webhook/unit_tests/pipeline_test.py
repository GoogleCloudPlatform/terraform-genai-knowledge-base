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

from unittest.mock import MagicMock, patch, mock_open

import kfp
from google.cloud import firestore

from pipeline import get_qas_from_collection

_PROJECT_ID = "faked-project"
_COLLECTION_NAME = "faked-collection"
_BUCKET_NAME = "faked-bucket"


@patch.object(firestore.Client, "collection")
def test_get_qas_from_collection(mock_collection):
    # Arrange
    mock_collection_ref = MagicMock(spec=firestore.CollectionReference)
    mock_collection.return_value = mock_collection_ref
    mock_iterator = MagicMock()
    mock_collection_ref.stream.return_value = mock_iterator
    mock_doc = MagicMock(spec=firestore.DocumentSnapshot)
    mock_doc.to_dict.return_value = {
        "question": "Who is the Greek goddess of the hunt?",
        "answer": "Artemis"
    }
    mock_doc2 = MagicMock(spec=firestore.DocumentSnapshot)
    mock_doc2.to_dict.return_value = {
        "question": "Which Israelite prophet lived at the time of King Ahab?",
        "answer": "Elijah"
    }
    mock_iterator.__iter__.return_value = [mock_doc, mock_doc2]

    # Act
    with patch("builtins.open", mock_open()):
        op = get_qas_from_collection(
            project_id=_PROJECT_ID,
            collection_name=_COLLECTION_NAME,
            bucket_name=_BUCKET_NAME)

        # Assert
        assert type(op) == kfp.dsl.PipelineTask