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
import json
import logging
import os

from cloudevents.http import CloudEvent
import functions_framework

from process_document import process_document

# Required variables.
DATABASE = os.environ["DATABASE"]
DOCAI_PROCESSOR = os.environ["DOCAI_PROCESSOR"]
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]


@functions_framework.cloud_event
def webhook(event: CloudEvent) -> None:
    try:
        process_document(
            event_id=event.data["id"],
            input_bucket=event.data["bucket"],
            input_name=event.data["name"],
            mime_type=event.data["contentType"],
            docai_prcessor_id=DOCAI_PROCESSOR,
            time_uploaded=datetime.fromisoformat(event.data["timeCreated"]),
            output_bucket=OUTPUT_BUCKET,
            database=DATABASE,
        )
    except Exception as e:
        logging.exception(e, stack_info=True)
