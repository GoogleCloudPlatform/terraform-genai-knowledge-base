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
from typing import List, Mapping, Tuple

from google.cloud import firestore
from google.cloud.firestore_v1 import aggregation


def write_qas_to_collection(
    project_id: str,
    collection_name: str,
    question_answer_pairs: List[Tuple[str, str]],
    input_file_gcs_uri: str,
    time_created: datetime,
):
    """Writes question and answer pairs to the specified Firestore collection.

    Arguments:
      project_id: the project that contains this database
      collection_name: the collection to store the Q&A pairs in
      question_answer_pairs: the Q&A pairs to add
      input_file_gcs_uri: the Cloud Storage URI for the source PDF
      time_created: the time that this PDF was uploaded
    """
    db = firestore.Client(project=project_id)
    bulkwriter = db.bulk_writer()

    for qa in question_answer_pairs:

        # Create a unique ID for each question
        question_hash = hash(qa[0])

        doc_ref = db.document(collection_name, str(question_hash))
        doc_snap = doc_ref.get()

        document_data = {
            "question": qa[0],
            "answers": [{
                "answer": qa[1],
                "gcs_uri": input_file_gcs_uri,
                "time_uploaded": time_created,
            }]
        }

        if doc_snap.exists:
            bulkwriter.update(doc_ref, document_data)
            continue

        bulkwriter.create(doc_ref, document_data)

    # Send all updates and close the BulkWriter
    bulkwriter.close()


def get_qas_from_collection(project_id: str, collection_name: str) -> List[Mapping[str, str]]:
    """Gets all QA sets as a list of dict objects.

    Arguments:
      project_id: the project that contains this database
      collection_name: the collection to get the Q&A pairs from

    Returns:
        All documents (QAs) in the collection. Each document is a dict object.
    """
    db = firestore.Client(project=project_id)
    collection_ref = db.collection(collection_name)
    docs_iter = collection_ref.stream()

    all_qas = []

    for doc in docs_iter:
        qa = doc.to_dict()
        all_qas.append(qa)

    return all_qas


def get_qas_count(project_id: str,
                  collection_name: str,
                  field: str = "question") -> int:
    """Gets the COUNT of all questions in the Firestore Collection.

    Arguments:
      project_id: the project that contains this database
      collection_name: the collection to get the question count of
      field: the field to filter on for the COUNT. Default is 'question'.

    Returns:
        Integer representing the COUNT of all questions in the collection.
    """
    db = firestore.Client(project=project_id)
    collection_ref = db.collection(collection_name)

    query = collection_ref.where(filter=firestore.FieldFilter(field, "!=", ""))
    aggregate_query = aggregation.AggregationQuery(query)
    aggregate_query.count(alias="all")

    results = aggregate_query.get()
    number = 0

    for result in results:
        number = result[0].value

    return number
