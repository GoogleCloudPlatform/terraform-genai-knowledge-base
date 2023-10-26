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

import backoff
import os

from extraction import extract_questions


_MODEL_NAME = "text-bison@001"
_PROJECT_ID = os.environ["PROJECT_ID"]

extracted_text = """
Our quantum computers work by manipulating qubits in an orchestrated 
fashion that we call quantum algorithms. The challenge is that qubits 
are so sensitive that even stray light can cause calculation errors 
— and the problem worsens as quantum computers grow. This has significant 
consequences, since the best quantum algorithms that we know for running 
useful applications require the error rates of our qubits to be far lower 
than we have today. To bridge this gap, we will need quantum error correction. 
Quantum error correction protects information by encoding it across 
multiple physical qubits to form a “logical qubit,” and is believed to be 
the only way to produce a large-scale quantum computer with error rates 
low enough for useful calculations. Instead of computing on the individual 
qubits themselves, we will then compute on logical qubits. By encoding 
larger numbers of physical qubits on our quantum processor into one 
logical qubit, we hope to reduce the error rates to enable useful 
quantum algorithms.
"""


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def test_extract_questions():
    question_list = extract_questions(
        project_id=_PROJECT_ID,
        model_name=_MODEL_NAME,
        temperature=0.2,
        max_decode_steps=1024,
        top_p=0.8,
        top_k=40,
        text=extracted_text,
        location="us-central1",
    )

    assert question_list is not None
    assert len(question_list) > 0

    first_question = question_list[0]
    assert first_question[0] != ""
