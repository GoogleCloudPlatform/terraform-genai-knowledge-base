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
from unittest.mock import MagicMock, patch, mock_open

from google.cloud import firestore
from google.cloud.firestore_v1 import base_query
from google.cloud.firestore_v1 import base_aggregation

from firestore_collection import get_qas_count
from firestore_collection import write_qas_to_collection

_PROJECT_ID = "fake-project-id"
_COLLECTION_NAME = "fake-collection"
_DATABASE_NAME = "fake-database"
_BUCKET_NAME = "fake-bucket"
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
        project_id=_PROJECT_ID,
        database_name=_DATABASE_NAME,
        collection_name=_COLLECTION_NAME,
        question_answer_pairs=[data_row],
        input_file_gcs_uri=_GCS_URI,
        time_created=timestamp)

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
        project_id=_PROJECT_ID,
        database_name=_DATABASE_NAME,
        collection_name=_COLLECTION_NAME,
        question_answer_pairs=data_rows,
        input_file_gcs_uri=_GCS_URI,
        time_created=timestamp)

    # Assert
    mock_document.assert_called()
    mock_document_ref.get.assert_called()
    mock_bulkwriter_ref.create.assert_called()
    mock_bulkwriter_ref.update.assert_called()
    mock_bulkwriter_ref.close.assert_called()


@patch.object(firestore.Client, "collection")
@patch("google.cloud.firestore_v1.aggregation.AggregationQuery")
def test_get_qas_count(mock_aggregation, mock_collection):
    # Arrange
    mock_collection_ref = MagicMock(spec=firestore.CollectionReference)
    mock_collection.return_value = mock_collection_ref
    mock_query = MagicMock(spec=base_query.BaseQuery)
    mock_collection_ref.where.return_value = mock_query
    mock_result = MagicMock(spec=base_aggregation.AggregationResult)
    mock_result.value = 2
    mock_aggregation.return_value.get.return_value = [[mock_result]]

    # Act
    count = get_qas_count(project_id=_PROJECT_ID, 
                          database_name=_DATABASE_NAME, 
                          collection_name=_COLLECTION_NAME)

    # Assert
    mock_aggregation.assert_called()
    mock_aggregation.return_value.get.assert_called()
    assert count == 2
