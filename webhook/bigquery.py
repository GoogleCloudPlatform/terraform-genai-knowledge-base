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

from typing import Sequence, Mapping

from datetime import datetime

from google.cloud import bigquery


def write_summarization_to_table(
    project_id: str,
    dataset_id: str,
    table_id: str,
    bucket: str,
    filename: str,
    complete_text: str,
    complete_text_uri: str,
    summary: str,
    summary_uri: str,
    timestamp: datetime,
) -> Sequence[Mapping]:
    """Updates the BigQuery table with the document summarization

    Original sample is here:
    https://cloud.google.com/bigquery/docs/samples/bigquery-table-insert-rows-explicit-none-insert-ids

    Args:
      project_id (str): the Google Cloud project ID
      dataset_id (str): the name of the BigQuery dataset
      table_id (str): the name of the BigQuery table
      bucket (str): the name of the bucket with the PDF
      filename (str): path of PDF relative to bucket root
      complete_text (str): the complete text of the PDF
      complete_text_uri (str): the Storage URI of the complete TXT document
      summary (str): the text summary of the document
      summary_uri (str): the Storage URI of the summary TXT document
      timestamp (datetime): when the processing occurred
    """
    if (project_id == "") or (dataset_id == "") or (table_id == ""):
        return [ValueError("project_id, dataset_id, or table_id is missing")]

    if (
        (bucket == "")
        and (filename == "")
        and (complete_text == "")
        and (summary_uri == "")
        and (summary == "")
        and (complete_text_uri == "")
        and (timestamp is None)
    ):
        return [ValueError("no row data provided for updating table")]
    client = bigquery.Client()

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

    errors = client.insert_rows_json(
        table_name, rows_to_insert, row_ids=bigquery.AutoRowIDs.GENERATE_UUID
    )

    return errors
