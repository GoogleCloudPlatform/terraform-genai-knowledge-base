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

from datetime import datetime
from unittest.mock import MagicMock, patch

from google.cloud import firestore
from firestore_collection import write_qas_to_collection, get_qas_from_collection

_PROJECT_ID = "fake-project-id"
_COLLECTION_NAME = "fake-collection"
_GCS_URI = "gs://i/dont/exist"


@patch.object(firestore.Client, "document")
@patch.object(firestore.Client, "bulk_writer")
def test_write_qas_to_collection(mock_bulkwriter, mock_document):
    # Arrange
    mock_document_ref = MagicMock(spec=firestore.DocumentReference)
    mock_document.return_value = mock_document_ref
    mock_snapshot = MagicMock(spec=firestore.DocumentSnapshot, exists=False)
    mock_document_ref.get.return_value = mock_snapshot
    mock_bulkwriter_ref = MagicMock()
    mock_bulkwriter.return_value = mock_bulkwriter_ref

    timestamp = datetime.now()
    data_row = ("Who is the Greek goddess of the hunt?", "Artemis")

    # Act
    write_qas_to_collection(
        _PROJECT_ID,
        _COLLECTION_NAME,
        [data_row],
        _GCS_URI,
        timestamp)

    # Assert
    mock_document.assert_called_with(_COLLECTION_NAME, str(hash(data_row[0])))
    mock_document_ref.get.assert_called()
    mock_bulkwriter_ref.create.assert_called()
    mock_bulkwriter_ref.close.assert_called()


@patch.object(firestore.Client, "document")
@patch.object(firestore.Client, "bulk_writer")
def test_write_multiple_qas_to_collection(mock_bulkwriter, mock_document):
    # Arrange
    mock_document_ref = MagicMock(spec=firestore.DocumentReference)
    mock_document.return_value = mock_document_ref
    mock_snapshot_1 = MagicMock(spec=firestore.DocumentSnapshot, exists=False)
    mock_snapshot_2 = MagicMock(spec=firestore.DocumentSnapshot, exists=True)
    mock_document_ref.get.side_effect = [mock_snapshot_1, mock_snapshot_2]
    mock_bulkwriter_ref = MagicMock()
    mock_bulkwriter.return_value = mock_bulkwriter_ref

    timestamp = datetime.now()
    data_rows = [
        ("Who is the Greek goddess of the hunt?", "Artemis"),
        ("Which Israelite prophet lived at the time of King Ahab?", "Elijah"),
    ]

    # Act
    write_qas_to_collection(
        _PROJECT_ID,
        _COLLECTION_NAME,
        data_rows,
        _GCS_URI,
        timestamp)

    # Assert
    mock_document.assert_called()
    mock_document_ref.get.assert_called()
    mock_bulkwriter_ref.create.assert_called()
    mock_bulkwriter_ref.update.assert_called()
    mock_bulkwriter_ref.close.assert_called()


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
    qas = get_qas_from_collection(_PROJECT_ID, _COLLECTION_NAME)

    # Assert
    assert len(qas) > 1
    assert qas[0] is not None
    assert qas[0]["answer"] == "Artemis"
    assert qas[1] is not None
    assert qas[1]["answer"] == "Elijah"

    mock_collection.assert_called()
    mock_collection_ref.stream.assert_called()
