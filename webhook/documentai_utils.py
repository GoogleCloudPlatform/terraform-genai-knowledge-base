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

from pathlib import Path

from google.cloud import documentai
from google.cloud import storage


def get_document_text(
    project_id: str,
    gcs_uri: str,
    docai_processor: str,
) -> str:
    """Perform Optical Character Recognition (OCR) with Document AI on Cloud Storage files.

    For more information, see:
        https://cloud.google.com/document-ai/docs/process-documents-ocr

    Args:
        input_file_gcs_uri: GCS URI of the PDF/TIFF file.
    """
    client = documentai.DocumentProcessorServiceClient()
    response = client.process_document(
        request=documentai.ProcessRequest(
            name=client.processor_path(project_id, "us", docai_processor),
            gcs_document=documentai.GcsDocument(
                gcs_uri=gcs_uri,
                mime_type=infer_mime_type(gcs_uri),
            ),
        ),
    )
    return response.document.text


# https://cloud.google.com/document-ai/docs/file-types
def infer_mime_type(filename: str) -> str:
    match Path(filename).suffix:
        case ".pdf":
            return "application/pdf"
        case ".gif":
            return "image/gif"
        case ".tiff" | ".tif":
            return "image/tiff"
        case ".jpg" | ".jpeg":
            return "image/jpeg"
        case ".png":
            return "image/png"
        case ".bmp":
            return "image/bmp"
        case ".webp":
            return "image/webp"
        case ext:
            raise ValueError(
                f"file format {ext} is not supported, see: https://cloud.google.com/document-ai/docs/file-types"
            )
