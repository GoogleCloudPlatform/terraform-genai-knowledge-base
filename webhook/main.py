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

import itertools
import json
import logging
import multiprocessing
import os
import re
from datetime import datetime

import functions_framework
import vertexai  # type: ignore
from cloudevents.http import CloudEvent
from google.api_core.client_options import ClientOptions
from google.cloud import aiplatform
from google.cloud import documentai
from google.cloud import firestore  # type: ignore
from google.cloud import storage  # type: ignore
from google.cloud.aiplatform_v1.types import IndexDatapoint
from retry import retry
from timeout import timeout, TimeoutException  # type: ignore
from vertexai.language_models import TextEmbeddingModel  # type: ignore
from vertexai.preview.generative_models import GenerativeModel  # type: ignore

DEPLOYED_INDEX_ID = "deployed_index"
DOCAI_LOCATION = os.environ.get("DOCAI_LOCATION", "us")

QUESTION_RE = re.compile(r"^Q:\s*", re.MULTILINE)

GENERATE_QUESTIONS_PROMPT = """\
TEXT:
{text}

Give me 20 self-contained questions and answers that can be answered from the above text.
Return a JSON list of (question, answer) objects.
"""

MODEL_INPUT_PROMPT = """\
TEXT:
{text}
----

Please answer the following question given the provided text.

Explain to a sixth-grader.

QUESTION:
{question}

ANSWER:
"""

# Initialize Vertex AI client libraries.
vertexai.init(location=os.environ.get("VERTEXAI_LOCATION", "us-central1"))
aiplatform.init(location=os.environ.get("VERTEXAI_LOCATION", "us-central1"))


@timeout(duration=5)
def deploy_index(index_id: str, index_endpoint_id: str) -> None:
    """Deploy a Vector Search index to an endpoint.

    Args:
        index_id: ID of the Vector Search index.
        index_endpoint_id: ID of the Vector Search index endpoint.
    """
    index = aiplatform.MatchingEngineIndex(index_id)
    endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_id)
    if not any(index.id == DEPLOYED_INDEX_ID for index in endpoint.deployed_indexes):
        print("⏱️ Deploying Vector Search index, this may take up to 30 minutes...")
        endpoint.deploy_index(
            index,
            DEPLOYED_INDEX_ID,
            min_replica_count=1,
            max_replica_count=1,
        )
        index.remove_datapoints(["null"]).wait()


# Deploy the Vertex AI Vector Search index if it isn't already deployed.
try:
    # Deploying the index can take up to 30 minutes, so don't wait for it.
    if os.environ.get("INDEX_ID") and os.environ.get("INDEX_ENDPOINT_ID"):
        deploy_index(os.environ["INDEX_ID"], os.environ["INDEX_ENDPOINT_ID"])
except TimeoutException:
    # The index is already being deployed by the service, so it's safe to ignore this.
    pass


@functions_framework.cloud_event
def on_cloud_event(event: CloudEvent) -> None:
    """Process a new document from an Eventarc event.

    Args:
        event: CloudEvent object.
    """
    try:
        process_document(
            event_id=event.data["id"],
            input_bucket=event.data["bucket"],
            filename=event.data["name"],
            mime_type=event.data["contentType"],
            time_uploaded=datetime.fromisoformat(event.data["timeCreated"]),
            docai_processor_id=os.environ["DOCAI_PROCESSOR"],
            database=os.environ["DATABASE"],
            output_bucket=os.environ["OUTPUT_BUCKET"],
            index_id=os.environ["INDEX_ID"],
        )
    except Exception as e:
        logging.exception(e, stack_info=True)


def process_document(
    event_id: str,
    input_bucket: str,
    filename: str,
    mime_type: str,
    time_uploaded: datetime,
    docai_processor_id: str,
    database: str,
    output_bucket: str,
    index_id: str,
) -> None:
    """Process a new document.

    Args:
        event_id: ID of the event.
        input_bucket: Name of the input bucket.
        filename: Name of the input file.
        mime_type: MIME type of the input file.
        time_uploaded: Time the input file was uploaded.
        docai_processor_id: ID of the Document AI processor.
        database: Name of the Firestore database.
        output_bucket: Name of the output bucket.
        index_id: ID of the Vector Search index.
    """
    db = firestore.Client(database=database)
    doc = db.document("documents", filename.replace("/", "-"))
    event_entry = {
        "event_id": event_id,
        "bucket": input_bucket,
        "filename": filename,
        "mime_type": mime_type,
        "time_uploaded": time_uploaded,
    }
    if (entry := doc.get().to_dict() or {}) and entry.get("event_id") == event_id:
        # We've already processed this event, this is probably an event retry.
        print(f"✅ {event_id}: Already processed")
        return

    if doc.get().exists:
        doc.update(event_entry)
    else:
        doc.create(event_entry)

    input_gcs_uri = f"gs://{input_bucket}/{filename}"
    print(f"📖 {event_id}: Getting document text")
    pages = get_document_text(
        gcs_uri=input_gcs_uri,
        mime_type=mime_type,
        processor_id=docai_processor_id,
    )
    doc.update({"pages": pages})

    print(f"🗂️ {event_id}: Indexing pages into Vector Search")
    index_pages(index_id, filename, pages)

    print(f"🔍 {event_id}: Generating Q&As with model ({len(pages)} pages)")
    with multiprocessing.Pool(len(pages)) as pool:
        event_pages = [
            {"filename": filename, "page_number": i, "text": page}
            for i, page in enumerate(pages)
        ]
        results = pool.map(process_page, event_pages)
        entries = list(itertools.chain.from_iterable(results))

    print(f"🗃️ {event_id}: Saving Q&As to Firestore ({len(entries)} entries)")
    for entry in entries:
        doc = db.document("dataset", entry["question"].replace("/", " "))
        if doc.get().exists:
            doc.update(entry)
        else:
            doc.create(entry)

    print(f"📝 {event_id}: Writing tuning dataset: gs://{output_bucket}/dataset.jsonl")
    dataset_size = write_tuning_dataset(db, output_bucket)
    print(f"✅ {event_id}: Done! {dataset_size=}")


def process_page(event_page: dict) -> list[dict[str, str]]:
    """Generate questions and answers for a single page of a document.

    Args:
        event_page: Dictionary containing the filename, page number, and text of the pages.

    Returns: Dictionaries containing the questions and answers.
    """
    filename = event_page["filename"]
    page_number = event_page["page_number"]
    text = event_page["text"]
    entries = generate_questions(text)
    try:
        return [
            {
                "question": entry["question"],
                "answer": entry["answer"],
                "filename": filename,
                "page_number": page_number,
            }
            for entry in entries
        ]
    except KeyError:
        logging.exception(f"Q&A generation failed: {entries}", stack_info=True)
        return []


def get_document_text(
    gcs_uri: str,
    mime_type: str,
    processor_id: str,
) -> list[str]:
    """Perform Optical Character Recognition (OCR) with Document AI on a Cloud Storage files.

    For more information, see:
        https://cloud.google.com/document-ai/docs/process-documents-ocr

    Args:
        gcs_uri: GCS URI of the document file.
        mime_type: MIME type of the document file.
        processor_id: ID of the Document AI processor.

    Returns: A list of the text in each page of the document.
    """
    # You must set the `api_endpoint` if you use a location other than "us".
    client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(
            api_endpoint=f"{DOCAI_LOCATION}-documentai.googleapis.com"
        )
    )
    response = client.process_document(
        request=documentai.ProcessRequest(
            name=processor_id,
            gcs_document=documentai.GcsDocument(
                gcs_uri=gcs_uri,
                mime_type=mime_type,
            ),
        ),
    )
    page_segments = [
        [
            (segment.start_index, segment.end_index)
            for segment in page.layout.text_anchor.text_segments
        ]
        for page in response.document.pages
    ]
    return [
        "\n".join(
            response.document.text[start_index:end_index]
            for start_index, end_index in segments
        )
        for segments in page_segments
    ]


def index_pages(index_id: str, filename: str, pages: list[str]) -> None:
    """Index pages into Vertex AI's Vector Search.

    Args:
        index_id: ID of the Vector Search index.
        filename: Name of the input file.
        pages: A list of the text in each page of the document.
    """
    model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
    page_embeddings = [
        vector
        for pages_batch in itertools.batched(pages, 5)
        for vector in model.get_embeddings(pages_batch)
    ]
    points = [
        IndexDatapoint(
            datapoint_id=f"{filename}:{page_number}",
            feature_vector=embedding.values,
        )
        for page_number, embedding in enumerate(page_embeddings)
    ]

    index = aiplatform.MatchingEngineIndex(index_id)
    index.remove_datapoints(["null"])
    index.upsert_datapoints(points).wait()


@retry(tries=3)
def generate_questions(text: str) -> list[dict[str, str]]:
    """Extract questions & answers using a large language model (LLM).

    For more information, see:
        https://cloud.google.com/vertex-ai/docs/generative-ai/learn/models

    Args:
        text: the text to generate questions and answers for

    Returns: A list of (question, answer) tuples
    """
    # Ask the model to generate the questions and answers.
    model = GenerativeModel("gemini-pro")
    prompt = GENERATE_QUESTIONS_PROMPT.format(text=text)
    response = model.generate_content(prompt).text
    if response.startswith("```"):
        response = "\n".join(response.splitlines()[1:-1])
    try:
        return json.loads(response)
    except json.decoder.JSONDecodeError:
        print(f"Failed to parse response:\n{response}")
        return []


def write_tuning_dataset(db: firestore.Client, output_bucket: str) -> int:
    """Write the tuning dataset to Cloud Storage.

    Args:
        db: Firestore client.
        output_bucket: Name of the output bucket.

    Returns: The number of entries in the tuning dataset.
    """
    storage_client = storage.Client()

    documents = [doc.to_dict() or {} for doc in db.collection("documents").stream()]
    doc_pages = {doc["filename"]: doc["pages"] for doc in documents}

    dataset_size = 0
    with storage_client.get_bucket(output_bucket).blob("dataset.jsonl").open("w") as f:
        for doc in db.collection("dataset").stream():
            entry = doc.to_dict() or {}
            line = {
                "input_text": MODEL_INPUT_PROMPT.format(
                    text=doc_pages[entry["filename"]][entry["page_number"]],
                    question=entry["question"],
                ),
                "output_text": entry["answer"],
            }
            f.write(f"{json.dumps(line)}\n")
            dataset_size += 1
    return dataset_size
