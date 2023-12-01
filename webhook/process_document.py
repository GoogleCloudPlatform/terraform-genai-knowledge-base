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
import os

from google.cloud import firestore

import documentai_utils
import firestore_utils
import storage_utils
import vertexai_utils

# Optional variables.
LOCATION = os.environ.get("LOCATION", "us-central1")
DATASET_COLLECTION = os.environ.get("QA_COLLECTION", "dataset")
EVENTS_COLLECTION = os.environ.get("EVENTS_COLLECTION", "events")
OUTPUT_NAME = os.environ.get("OUTPUT_NAME", "dataset.jsonl")


def process_document(
    event_id: str,
    input_bucket: str,
    input_name: str,
    mime_type: str,
    docai_prcessor_id: str,
    time_uploaded: datetime,
    output_bucket: str,
    database: str,
) -> None:
    db = firestore.Client(database=database)
    doc = db.document(EVENTS_COLLECTION, event_id)
    if doc.get().exists:
        # We've already processed this event, this is probably an event retry.
        return
    event_entry = {
        "bucket": input_bucket,
        "input_name": input_name,
        "mime_type": mime_type,
        "time_uploaded": time_uploaded,
    }
    doc.create(event_entry)

    input_gcs_uri = f"gs://{input_bucket}/{input_name}"
    print(f"📖 {event_id}: Getting document text")
    text = documentai_utils.get_document_text(
        gcs_uri=input_gcs_uri,
        mime_type=mime_type,
        processor_id=docai_prcessor_id,
    )

    print(f"🔍 {event_id}: Generating Q&As with model")
    questions_answers = vertexai_utils.generate_questions(text, LOCATION)
    for q, a in questions_answers:
        print(f"  - Q: {q}")
        print(f"    A: {a}")

    print(f"🗂️ {event_id}: Saving Q&As to Firestore: {len(questions_answers)=}")
    entries = {
        question: {
            "answer": answer,
            "event_id": event_id,
        }
        for question, answer in questions_answers
    }
    firestore_utils.write(db, DATASET_COLLECTION, entries)

    print(f"📝 {event_id}: Writing tuning dataset: gs://{output_bucket}/{OUTPUT_NAME}")
    dataset_size = 0
    with storage_utils.write(output_bucket, OUTPUT_NAME) as f:
        for question, entry in firestore_utils.read(db, DATASET_COLLECTION):
            line = {"input_text": question, "output_text": entry["answer"]}
            f.write(f"{json.dumps(line)}\n")
            dataset_size += 1

    print(f"✅ {event_id}: Done! {dataset_size=}")
