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

import vertexai
from vertexai.preview.language_models import TextGenerationModel


def extract_questions(
        *,
        project_id: str,
        model_name: str,
        text: str,
        temperature: float = 0.2,
        max_decode_steps: int = 1024,
        top_p: float = 0.8,
        top_k: int = 40,
        location: str = "us-central1",
) -> str:
    """Extract questions & answers using a large language model (LLM)

    Args:
        project_id (str): the Google Cloud project ID
        model_name (str): the name of the LLM model to use
        temperature (float): controls the randomness of predictions
        max_decode_steps (int): the number of tokens to generate
        top_p (float): cumulative probability of parameter highest vocabulary tokens
        top_k (int): number of highest probability vocabulary tokens to keep for top-k-filtering
        text (str): the text to summarize
        location (str): the Google Cloud region to run in

    Returns:
        The summarization of the content
    """
    vertexai.init(
        project=project_id,
        location=location,
    )

    model = TextGenerationModel.from_pretrained(model_name)

    response = model.predict(
        f"""Extract at least 20 Questions based on the following article: {text}\nQuestions:""",
        temperature=temperature,
        max_output_tokens=max_decode_steps,
        top_k=top_k,
        top_p=top_p,
    )
    question_list = response.text.splitlines()

    return question_list
