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

from vertex_llm import predict_large_language_model


_MODEL_NAME = "text-bison@001"
_PROJECT_ID = os.environ["PROJECT_ID"]

extracted_text = """
arXiv:cmp-lg/9404001v1 4 Apr 1994
An Alternative Conception of
Tree-Adjoining Derivation
Yves Schabes
Mitsubishi Electric
Research Laboratories, Inc.
Cambridge, MA 02139
shieber@das.harvard.edu
Stuart M. Shieber
Division of Applied Sciences
Harvard University
Cambridge, MA 02138
schabes@merl.com
December 20, 1993
Abstract
The precise formulation of derivation for tree-adjoining grammars has impor-
tant ramifications for a wide variety of uses of the formalism, from syntactic analysis
to semantic interpretation and statistical language modeling. We argue that the
definition of tree-adjoining derivation must be reformulated in order to manifest
the proper linguistic dependencies in derivations. The particular proposal is both
precisely characterizable through a definition of TAG derivations as equivalence
classes of ordered derivation trees, and computationally operational, by virtue of
a compilation to linear indexed grammars together with an efficient algorithm for
recognition and parsing according to the compiled grammar.
This paper is to appear in Computational Linguistics, volume 20, number 1, and is available
from the Center for Research in Computing Technology, Division of Applied Sciences, Harvard
University as Technical Report TR-08-92 and through the Computation and Language e-print
archive as cmp-lg/9404001.1. Differentiates predicative and modifier auxiliary trees;
2. Requires dependent derivations for predicative trees;
3. Allows independent derivations for modifier trees; and
4. Unambiguously and nonredundantly specifies a derived tree.
Furthermore, following from considerations of the role of modifier trees in a grammar as
essentially optional and freely applicable elements, we would like the following criterion
to hold of extended derivations:
5. If a node can be modified at all, it can be modified any number of times, including
zero times.
Conclusion
The precise formulation of derivation for tree-adjoining grammars has important rami-
fications for a wide variety of uses of the formalism, from syntactic analysis to semantic
interpretation and statistical language modeling. We have argued that the definition of
tree-adjoining derivation must be reformulated in order to take greatest advantage of
the decoupling of derivation tree and derived tree by manifesting the proper linguistic
dependencies in derivations. The particular proposal is both precisely characterizable
through a definition of TAG derivations as equivalence classes of ordered derivation
trees, and computationally operational, by virtue of a compilation to linear indexed
grammars together with an efficient algorithm for recognition and parsing according to
the compiled grammar.
"""


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def test_predict_large_language_model():
    summary = predict_large_language_model(
        project_id=_PROJECT_ID,
        model_name=_MODEL_NAME,
        temperature=0.2,
        max_decode_steps=1024,
        top_p=0.8,
        top_k=40,
        content=f"Summarize:\n{extracted_text}",
        location="us-central1",
    )

    assert summary != ""
