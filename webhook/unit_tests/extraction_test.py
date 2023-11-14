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


from unittest.mock import MagicMock, PropertyMock, patch

import vertexai
from vertexai.preview.language_models import TextGenerationModel


from webhook.vertexai_utils import generate_questions

_PROJECT_ID = "fake-project-id"
_BUCKET_NAME = "fake-bucket"


@patch.object(vertexai, "init")
@patch.object(TextGenerationModel, "from_pretrained")
def test_tuning_mock(mock_get_model, mock_init):
    project_id = _PROJECT_ID
    model_name = _BUCKET_NAME
    temperature = 0.2
    max_decode_steps = 1024
    top_p = 0.8
    top_k = 40
    content = """
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
    location = "us-central1"
    want = "1. fake question?\nfake answer"

    # Arrange
    mock_response = MagicMock()
    mock_prop = PropertyMock(return_value=want)
    type(mock_response).text = mock_prop
    mock_model = MagicMock(spec=TextGenerationModel)
    mock_model.predict.return_value = mock_response
    mock_get_model.return_value = mock_model

    # Act
    got = generate_questions(
        project_id=project_id,
        model_name=model_name,
        temperature=temperature,
        max_decode_steps=max_decode_steps,
        top_p=top_p,
        top_k=top_k,
        text_gcs_uri=content,
        location=location,
    )

    # Assert
    assert ("1. fake question?", "fake answer") in got
    mock_init.assert_called_with(project=project_id, location=location)
    mock_model.predict.assert_called()
