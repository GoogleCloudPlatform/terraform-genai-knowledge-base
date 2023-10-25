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

import datetime
import json
import os
import requests
import flask

from typing import Mapping

from google.auth import default
from google.cloud import logging
import google.auth.transport.requests
import google.oauth2.id_token


from document_extract import async_document_extract
from firestore_collection import get_qas_count, write_qas_to_collection
from model_tuning import extract_questions
from pipeline import start_tuning_pipeline
from storage import upload_to_gcs
from utils import coerce_datetime_zulu, clean_text

_FUNCTIONS_VERTEX_EVENT_LOGGER = 'extractive-qa-by-llm'

_PROJECT_ID = os.environ["PROJECT_ID"]
_OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
_LOCATION = os.environ["LOCATION"]
_CREDENTIALS, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
_MODEL_NAME = "text-bison@001"
_DATABASE_NAME = os.environ["DATABASE"]
_COLLECTION_NAME = os.environ["COLLECTION"]
_TUNING_SIZE_INTERVALS = os.environ["TUNING_INTERVALS"]


def default_marshaller(o: object) -> str:
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    return str(o)


def redirect_and_reply(previous_data):
    endpoint = f'https://{_LOCATION}-{_PROJECT_ID}.cloudfunctions.net/{os.environ["K_SERVICE"]}'
    logging_client = logging.Client()
    logger = logging_client.logger(_FUNCTIONS_VERTEX_EVENT_LOGGER)

    auth_req = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(auth_req, endpoint)
    data = {
        'name': previous_data["name"],
        'id': previous_data["id"],
        'bucket': previous_data["bucket"],
        'timeCreated': previous_data["timeCreated"],
    }
    headers = {}
    headers["Authorization"] = f"Bearer {id_token}"
    logger.log(f'TRIGGERING JOB FLOW: {endpoint}')
    try:
        requests.post(
            endpoint,
            json=data,
            timeout=1,
            headers=headers,
        )
    except requests.exceptions.Timeout:
        return flask.Response(status=200)
    except Exception:
        return flask.Response(status=500)
    return flask.Response(status=200)


def entrypoint(request: object) -> Mapping[str, str]:
    data = request.get_json()
    if data.get("kind", None) == "storage#object":
        # Entrypoint called by Pub-Sub (Eventarc)
        return redirect_and_reply(data)

    if 'bucket' in data:
        # Entrypoint called by REST (possibly by redirect_and_replay)
        return cloud_event_entrypoint(
            name=data["name"],
            event_id=data["id"],
            bucket=data["bucket"],
            time_created=coerce_datetime_zulu(data["timeCreated"]),
        )
    else:
        return extraction_entrypoint(
            name=data['name'],
            extracted_text=data['text'],
            time_created=datetime.datetime.now(datetime.timezone.utc),
            event_id="CURL_TRIGGER",
        )

    return flask.Response(status=500)


def cloud_event_entrypoint(event_id, bucket, name, time_created) -> None:
    """Entrypoint for events arising from EventArc
    
    Arguments:
        event_id: the EventArc event ID
        bucket: the GCS bucket the document is in
        name: the name of the document in the GCS bucket
        time_created: the time the document was uploaded   
    """
    orig_pdf_uri = f"gs://{bucket}/{name}"
    logging_client = logging.Client()

    logger = logging_client.logger(_FUNCTIONS_VERTEX_EVENT_LOGGER)
    logger.log(f"cloud_event_id({event_id}): UPLOAD {orig_pdf_uri}",
               severity="INFO")

    extracted_text = async_document_extract(bucket, name, output_bucket=_OUTPUT_BUCKET)
    logger.log(
        f"cloud_event_id({event_id}): OCR  gs://{bucket}/{name}", severity="INFO"
    )

    extraction_entrypoint(
        name,
        extracted_text,
        time_created=time_created,
        event_id=event_id,
        bucket=bucket,
    )


def extraction_entrypoint(
        name: str,
        extracted_text: str,
        time_created: datetime.datetime,
        bucket: str = None,
        event_id: str = None):
    logging_client = logging.Client()
    logger = logging_client.logger(_FUNCTIONS_VERTEX_EVENT_LOGGER)

    output_filename = f'system-test/{name.replace(".pdf", "")}_tuning_dataset.txt'
    extracted_text_cleaned = clean_text(extracted_text)
    upload_to_gcs(
        _OUTPUT_BUCKET,
        output_filename,
        extracted_text,
    )
    logger.log(f"cloud_event_id({event_id}): PDF_TEXT_UPLOAD {upload_to_gcs}",
               severity="INFO")

    qa_pairs = extract_questions(
        project_id=_PROJECT_ID,
        model_name=_MODEL_NAME,
        text=extracted_text_cleaned,
    )
    logger.log(f"cloud_event_id({event_id}): QA_EXTRACTION", severity="INFO")

    write_qas_to_collection(
        project_id=_PROJECT_ID,
        database_name=_DATABASE_NAME,
        collection_name=_COLLECTION_NAME,
        question_answer_pairs=qa_pairs,
        input_file_gcs_uri=f"gs://{bucket}/{name}",
        time_created=time_created,
    )
    logger.log(f"cloud_event_id({event_id}): DB_WRITE", severity="INFO")

    count = get_qas_count(project_id=_PROJECT_ID,
                          database_name=_DATABASE_NAME,
                          collection_name=_COLLECTION_NAME)
    if (count % _TUNING_SIZE_INTERVALS) == 0:
        logger.log(f"cloud_event_id({event_id}): START_TUNING", severity="INFO")
        start_tuning_pipeline(
            project_id=_PROJECT_ID,
            database_name=_DATABASE_NAME,
            collection_name=_COLLECTION_NAME,
            bucket_name=_OUTPUT_BUCKET,
            location=_LOCATION,
        )
        return flask.Response(status=200)

    logger.log(f"cloud_event_id({event_id}): FINISHED", severity="INFO")
    return flask.Response(status=200)
