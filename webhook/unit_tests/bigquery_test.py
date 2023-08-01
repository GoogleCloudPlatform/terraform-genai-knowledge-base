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
from unittest.mock import ANY, patch
from datetime import datetime
from google.cloud import bigquery

from bigquery import write_summarization_to_table


_DATASET_ID = "summary_dataset"
_TABLE_ID = "summary_table"
_PROJECT_ID = os.environ["PROJECT_ID"]

bucket = "fake-bucket"
filename = "fake-file-name"
summary_uri = "fake-summary/uri/"
summary = "this is a fake summary"
complete_text = "this is the fake complete text"
complete_text_uri = "fake-complete-text/uri/"
timestamp = datetime.now()


@patch.object(bigquery.Client, "insert_rows_json")
def test_insert_rows_json(mock_insert_rows):
    mock_insert_rows.return_value = []

    project_id = "project-name"
    dataset_id = "dataset-id"
    table_id = "my-table"
    table_name = f"{project_id}.{dataset_id}.{table_id}"

    rows_to_insert = [
        {
            "bucket": bucket,
            "filename": filename,
            "extracted_text": complete_text,
            "summary_uri": summary_uri,
            "summary": summary,
            "complete_text_uri": complete_text_uri,
            "timestamp": timestamp.isoformat(),
        }
    ]

    # Act
    write_summarization_to_table(
        project_id,
        dataset_id,
        table_id,
        bucket,
        filename,
        complete_text,
        complete_text_uri,
        summary,
        summary_uri,
        timestamp,
    )

    # Assert
    mock_insert_rows.assert_called_with(table_name, rows_to_insert, row_ids=ANY)


def test_write_summarization_bad_inputs():
    # Act
    errors = write_summarization_to_table(
        "",
        "",
        "",
        bucket,
        filename,
        complete_text,
        complete_text_uri,
        summary,
        summary_uri,
        timestamp,
    )

    # Assert
    assert len(errors) == 1
    assert type(errors[0]) == ValueError


def test_write_summarization_no_row_data():
    # Act
    errors = write_summarization_to_table(
        "project", "dataset", "table", "", "", "", "", "", "", None
    )

    # Assert
    assert len(errors) == 1
    assert type(errors[0]) == ValueError
