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

import documentai_utils
import firestore_utils
import storage_utils
import vertexai_utils

# Project resources.
PROJECT_ID = os.environ["PROJECT_ID"]
LOCATION = os.environ["LOCATION"]
DATABASE = os.environ["DATABASE"]
DATASET_COLLECTION = os.environ.get("QA_COLLECTION", "dataset")
EVENTS_COLLECTION = os.environ.get("EVENTS_COLLECTION", "events")

# Output dataset.
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
DATASET_NAME = os.environ.get("DATASET_NAME", "dataset.jsonl")


@functions_framework.cloud_event
def webhook(event: CloudEvent) -> None:
    try:
        process_document(
            event_id=event.data["id"],
            bucket=event.data["bucket"],
            input_name=event.data["name"],
            mime_type=event.data["contentType"],
            time_uploaded=datetime.fromisoformat(event.data["timeCreated"]),
        )
    except Exception as e:
        logging.exception(e, stack_info=True)


def process_document(
    event_id: str,
    bucket: str,
    input_name: str,
    mime_type: str,
    time_uploaded: datetime,
) -> None:
    database = firestore_utils.client(DATABASE)
    doc = database.document(EVENTS_COLLECTION, event_id)
    if doc.get().exists:
        # We've already processed this event, this is probably an event retry.
        return
    event_entry = {
        "bucket": bucket,
        "input_name": input_name,
        "mime_type": mime_type,
        "time_uploaded": time_uploaded,
    }
    doc.create(event_entry)

    input_gcs_uri = f"gs://{bucket}/{input_name}"
    print(f"📖 {event_id}: Getting document text")
    text = documentai_utils.get_document_text(
        project_id=PROJECT_ID,
        gcs_uri=input_gcs_uri,
        mime_type=mime_type,
    )

    print(f"🔍 {event_id}: Generating Q&As with model")
    question_answers = vertexai_utils.generate_questions(text, LOCATION)
    for q, a in question_answers:
        print(f"  - Q: {q}")
        print(f"    A: {a}")

    print(f"🗂️ {event_id}: Saving Q&As to Firestore: {len(question_answers)=}")
    entries = {
        question: {
            "answer": answer,
            "event_id": event_id,
        }
        for question, answer in question_answers
    }
    firestore_utils.write(database, DATASET_COLLECTION, entries)

    print(f"📝 {event_id}: Writing tuning dataset: gs://{OUTPUT_BUCKET}/{DATASET_NAME}")
    dataset_size = 0
    with storage_utils.write(OUTPUT_BUCKET, DATASET_NAME) as f:
        for question, entry in firestore_utils.read(database, DATASET_COLLECTION):
            line = {"input_text": question, "output_text": entry["answer"]}
            f.write(f"{json.dumps(line)}\n")
            dataset_size += 1

    print(f"✅ {event_id}: Done! {dataset_size=}")
