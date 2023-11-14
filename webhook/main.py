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
import flask
import json
import logging
import os
import requests

import google.auth.transport.requests
import google.oauth2.id_token

import documentai_utils
import firestore_utils
import storage_utils
import vertexai_utils

PROJECT_ID = os.environ["PROJECT_ID"]
LOCATION = os.environ["LOCATION"]
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
DOCAI_PROCESSOR = os.environ["DOCAI_PROCESSOR"]
DATABASE = os.environ["DATABASE"]
COLLECTION = os.environ["COLLECTION"]

MODEL_NAME = "text-bison@001"


def entrypoint(request: flask.Request) -> flask.Response:
    data = request.get_json()
    if data.get("kind", None) == "storage#object":
        # Entrypoint called by the Eventarc trigger.
        return ack_and_process(data, fields=["name", "id", "bucket", "timeCreated"])

    try:
        process_document(
            event_id=data["id"],
            bucket=data["bucket"],
            input_name=data["name"],
            time_uploaded=datetime.fromisoformat(data["timeCreated"]),
        )
    except Exception as e:
        logging.exception(e, stack_info=True)
    return flask.Response(status=200)


def ack_and_process(data: dict, fields: list[str]) -> None:
    # Each document can take a while to process.
    # The Eventarc trigger might want to retry if it doesn't finish in time.
    # Events are acked on a 200 status response so it won't retry.
    print(f"📬 {data['id']}: New file uploaded")
    endpoint = (
        f"https://{LOCATION}-{PROJECT_ID}.cloudfunctions.net/{os.environ['K_SERVICE']}"
    )
    auth_req = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(auth_req, endpoint)
    try:
        # Resend the request, but don't wait for the response.
        requests.post(
            endpoint,
            json={key: data[key] for key in fields},
            headers={"Authorization": f"Bearer {id_token}"},
            timeout=0.1,
        )
    except requests.exceptions.Timeout:
        pass
    # Ack the event immediately to avoid retries.
    return flask.Response(status=200)


def process_document(
    event_id: str,
    bucket: str,
    input_name: str,
    time_uploaded: datetime,
) -> None:
    input_gcs_uri = f"gs://{bucket}/{input_name}"
    print(f"📖 {event_id}: Getting document text")
    text = documentai_utils.get_document_text(
        PROJECT_ID,
        input_gcs_uri,
        DOCAI_PROCESSOR,
    )

    print(f"🔍 {event_id}: Generating Q&As with model: {MODEL_NAME}")
    question_answers = vertexai_utils.generate_questions(text, MODEL_NAME)
    for q, a in question_answers:
        print(f"  - Q: {q}")
        print(f"    A: {a}")

    print(f"🗂️ {event_id}: Saving Q&As to Firestore: {len(question_answers)=}")
    firestore_utils.write(
        database=DATABASE,
        collection=COLLECTION,
        entries={
            question: {
                "answer": answer,
                "event_id": event_id,
                "time_uploaded": time_uploaded,
            }
            for question, answer in question_answers
        },
    )

    dataset_name = "dataset.jsonl"
    print(f"📝 {event_id}: Writing tuning dataset: gs://{OUTPUT_BUCKET}/{dataset_name}")
    dataset_size = 0
    with storage_utils.write(OUTPUT_BUCKET, dataset_name) as f:
        for question, entry in firestore_utils.read(DATABASE, COLLECTION):
            line = {"input_text": question, "output_text": entry["answer"]}
            f.write(f"{json.dumps(line)}\n")
            dataset_size += 1

    print(f"✅ {event_id}: Done! {dataset_size=}")
