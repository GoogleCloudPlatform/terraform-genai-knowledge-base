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
import backoff
from datetime import datetime

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


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def test_write_summarization_to_table_system(capsys):
    errors = write_summarization_to_table(
        project_id=_PROJECT_ID,
        dataset_id=_DATASET_ID,
        table_id=_TABLE_ID,
        bucket="gs://fake_bucket",
        filename="fake.pdf",
        complete_text="This is fake text of an academic paper",
        complete_text_uri="gs://fake_bucket/texts/fake.txt",
        summary="Some fake text summary",
        summary_uri="gs://fake_bucket/fake-summary.txt",
        timestamp=datetime.now(),
    )

    assert len(errors) == 0
