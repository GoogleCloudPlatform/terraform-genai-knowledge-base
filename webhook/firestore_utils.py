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

from collections.abc import Iterator

from google.cloud import firestore


def read(client: firestore.Client, collection: str) -> Iterator[tuple[str, dict]]:
    for doc in client.collection(collection).stream():
        yield (doc.id, doc.to_dict() or {})


def write(client: firestore.Client, collection: str, entries: dict[str, dict]) -> None:
    for key, value in entries.items():
        doc = client.document(collection, key)
        if doc.get().exists:
            doc.update(value)
        else:
            doc.create(value)
