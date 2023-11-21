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

import re

import vertexai
from vertexai.preview.language_models import TextGenerationModel

QUESTION_RE = re.compile(r"^Q:\s*", re.MULTILINE)

PROMPT_TEMPLATE = """
TEXT:
{text}

Give me 20 specific questions and answers that can be answered from the above text.
Q:"""


def generate_questions(text: str, location: str) -> list[tuple[str, str]]:
    """Extract questions & answers using a large language model (LLM)

    For more information, see:
        https://cloud.google.com/vertex-ai/docs/generative-ai/learn/models

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
    vertexai.init(location=location)

    # Ask the model to generate the questions and answers.
    model = TextGenerationModel.from_pretrained("text-bison@001")
    response = model.predict(
        PROMPT_TEMPLATE.format(text=text),
        temperature=0.2,
        max_output_tokens=1024,
        top_k=40,
        top_p=0.8,
    )
    return [
        tuple(map(str.strip, question_answer.split("\nA:", 1)))
        for question_answer in QUESTION_RE.split(f"Q: {response.text}")
        if "\nA:" in question_answer
    ]
