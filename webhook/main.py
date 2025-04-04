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
from collections.abc import Iterable
from datetime import datetime

import functions_framework
from cloudevents.http import CloudEvent
from google import genai  # type: ignore
from google.genai.types import GenerateContentConfig  # type: ignore
from google.api_core.client_options import ClientOptions
from google.api_core.retry import Retry
from google.cloud import aiplatform
from google.cloud import documentai
from google.cloud import firestore  # type: ignore
from google.cloud import storage  # type: ignore
from google.cloud.aiplatform_v1.types import IndexDatapoint

DOCAI_LOCATION = os.environ.get("DOCAI_LOCATION", "us")


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
            project=os.environ["PROJECT_ID"],
            location=os.environ["LOCATION"],
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
    project: str,
    location: str,
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
        project: Google Cloud project ID.
        location: Google Cloud location.
        docai_processor_id: ID of the Document AI processor.
        database: Name of the Firestore database.
        output_bucket: Name of the output bucket.
        index_id: ID of the Vector Search index.
    """
    aiplatform.init(project=project, location=location)

    db = firestore.Client(project=project, database=database)
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
        return

    if doc.get().exists:
        doc.update(event_entry)
    else:
        doc.create(event_entry)

    input_gcs_uri = f"gs://{input_bucket}/{filename}"
    print(f"📖 {event_id}: Getting document text")
    pages = list(get_document_text(input_gcs_uri, mime_type, docai_processor_id, output_bucket))
    doc.update({"pages": pages})

    print(f"🗂️ {event_id}: Indexing pages into Vector Search")
    embeddings = get_pages_embeddings(project, location, pages)
    index_pages(index_id, filename, embeddings)

    print(f"🔍 {event_id}: Generating Q&As with model ({len(pages)} pages)")

    with multiprocessing.Pool(len(pages)) as pool:
        event_pages = [
            {
                "project": project,
                "location": location,
                "filename": filename,
                "page_number": i,
                "text": page,
            }
            for i, page in enumerate(pages)
        ]
        page_entries = pool.map(process_page, event_pages)
        document_entries = list(itertools.chain.from_iterable(page_entries))

    print(f"🗃️ {event_id}: Saving Q&As to Firestore ({len(document_entries)} entries)")
    for entry in document_entries:
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
        event_page: Dictionary containing the event pages information.

    Returns: Dictionaries containing the questions and answers.
    """
    project = event_page["project"]
    location = event_page["location"]
    filename = event_page["filename"]
    page_number = event_page["page_number"]
    text = event_page["text"]
    entries = generate_questions(project, location, text)
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
    input_file: str,
    mime_type: str,
    processor_id: str,
    temp_bucket: str,
) -> Iterable[str]:
    """Perform Optical Character Recognition (OCR) with Document AI on a Cloud Storage files.

    For more information, see:
        https://cloud.google.com/document-ai/docs/process-documents-ocr

    Args:
        input_file: GCS URI of the document file.
        mime_type: MIME type of the document file.
        processor_id: ID of the Document AI processor.
        temp_bucket: GCS bucket to store Document AI temporary files.

    Returns: A list of the text in each page of the document.
    """
    # You must set the `api_endpoint` if you use a location other than "us".
    documentai_client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(api_endpoint=f"{DOCAI_LOCATION}-documentai.googleapis.com")
    )

    # We're using batch_process_documents instead of process_document because
    # process_document has a quota limit of 15 pages per document, while
    # batch_process_documents has a quota limit of 500 pages per request.
    #   https://cloud.google.com/document-ai/quotas#general_processors
    operation = documentai_client.batch_process_documents(
        request=documentai.BatchProcessRequest(
            name=processor_id,
            input_documents=documentai.BatchDocumentsInputConfig(
                gcs_documents=documentai.GcsDocuments(
                    documents=[
                        documentai.GcsDocument(
                            gcs_uri=input_file,
                            mime_type=mime_type,
                        ),
                    ],
                ),
            ),
            document_output_config=documentai.DocumentOutputConfig(
                gcs_output_config=documentai.DocumentOutputConfig.GcsOutputConfig(
                    gcs_uri=f"gs://{temp_bucket}/ocr/{input_file.split('gs://')[-1]}",
                ),
            ),
        ),
    )
    operation.result()

    # Read the results of the Document AI operation from Cloud Storage.
    storage_client = storage.Client()
    metadata = documentai.BatchProcessMetadata(operation.metadata)
    output_gcs_path = metadata.individual_process_statuses[0].output_gcs_destination
    (output_bucket, output_prefix) = output_gcs_path.removeprefix("gs://").split("/", 1)
    for blob in storage_client.list_blobs(output_bucket, prefix=output_prefix):
        blob_contents = blob.download_as_bytes()
        document = documentai.Document.from_json(blob_contents, ignore_unknown_fields=True)
        for page in document.pages:
            segments = [
                (segment.start_index, segment.end_index)
                for segment in page.layout.text_anchor.text_segments
            ]
            yield "\n".join([document.text[start:end] for (start, end) in segments])


def get_pages_embeddings(
    project: str,
    location: str,
    pages: Iterable[str],
) -> Iterable[list[float]]:
    """Get embeddings for a list of pages.

    For more information, see:
        https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings

    Args:
        project: Google Cloud project ID.
        location: Google Cloud location.
        pages: A list of the text in each page of the document.
    """
    genai_client = genai.Client(vertexai=True, project=project, location=location)

    max_input_texts = 5
    for batch in itertools.batched(pages, max_input_texts):
        response = genai_client.models.embed_content(
            model="text-embedding-005",
            contents=batch,
        )
        embeddings = response.embeddings or []
        for embedding in embeddings:
            yield embedding.values or []


def index_pages(
    index_id: str,
    filename: str,
    embeddings: Iterable[list[float]],
) -> None:
    """Index pages into Vertex AI's Vector Search.

    Args:
        index_id: ID of the Vector Search index.
        filename: Name of the input file.
        embeddings: A list of embeddings for each page of the document.
    """
    points = [
        IndexDatapoint(
            datapoint_id=f"{filename}:{page_number}",
            feature_vector=embedding,
        )
        for page_number, embedding in enumerate(embeddings)
    ]

    index = aiplatform.MatchingEngineIndex(index_id)
    index.remove_datapoints(["null"])
    index.upsert_datapoints(points).wait()


@Retry(lambda _: True)  # any exception since models are non-deterministic.
def generate_questions(project: str, location: str, text: str) -> list[dict[str, str]]:
    """Extract questions & answers using a large language model (LLM).

    For more information, see:
        https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models

    Args:
        project: Google Cloud project ID.
        location: Google Cloud location.
        text: the text to generate questions and answers for

    Returns: A list of (question, answer) tuples
    """
    # Ask the model to generate the questions and answers.
    genai_client = genai.Client(vertexai=True, project=project, location=location)
    response = genai_client.models.generate_content(
        model="gemini-2.0-flash",
        contents="List 20 self-contained questions and answers that can be answered from the text.",
        config=GenerateContentConfig(
            # https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/system-instructions
            system_instruction=[
                "Use simple language and words that are easy to understand.",
                "Avoid technical terms in the answers.",
            ],
            # https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output
            response_mime_type="application/json",
            response_schema={
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "question": {"type": "STRING"},
                        "answer": {"type": "STRING"},
                    },
                    "required": ["question", "answer"],
                },
            },
        ),
    )
    text = response.text or ""

    # The response is sometimes in code blocks, so we need to extract it.
    code_block_start = text.find("```")
    if code_block_start == -1:
        code_block = text
    else:
        code_block = "\n".join(text[code_block_start:].splitlines()[1:-1])

    # Parse the response as JSON.
    try:
        return json.loads(code_block)
    except json.decoder.JSONDecodeError:
        logging.debug(f"Failed to parse response:\n{response}")
        raise


def write_tuning_dataset(db: firestore.Client, output_bucket: str) -> int:
    """Write the tuning dataset to Cloud Storage.

    For more information on the tuning dataset file format:
        https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-supervised-tuning-about

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
            context = doc_pages[entry["filename"]][entry["page_number"]]
            row = {
                "systemInstruction": {
                    "parts": [{"text": "Answer the question based on the following text"}],
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": f"Text: {context}"},
                            {"text": entry["question"]},
                        ],
                    },
                    {
                        "role": "model",
                        "parts": [{"text": entry["answer"]}],
                    },
                ],
            }
            f.write(f"{json.dumps(row)}\n")
            dataset_size += 1
    return dataset_size
