#!/bin/bash
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
set -e

export PROJECT_ID="velociraptor-16p1-test-15"
export TF_PLAN_STORAGE_BUCKET="${PROJECT_ID?}-tf"
export BUCKET_NAME=${TF_PLAN_STORAGE_BUCKET?}-main
export TERRAFORM_IMAGE="hashicorp/terraform:1.4.6"
export PREFIX="terraform/${PROJECT_ID?}"

DESTROY=
while (( ${#} > 0 )); do
  case "${1}" in
    ( '--destroy' | '-d' ) DESTROY='-destroy' ;;      # Handles --destroy
    ( '--' ) operands+=( "${@:2}" ); break ;;         # End of options
    ( '-'?* ) ;;                                      # Discard non-valid options
    ( * ) operands+=( "${1}" )                        # Handles operands
  esac
  shift
done

gcloud config set project "${PROJECT_ID?}"
gcloud --quiet auth login "$(whoami)@google.com" --no-launch-browser
gcloud services enable cloudresourcemanager.googleapis.com

sudo docker run \
  -w /app \
  -v "$(pwd)":/app \
  "${TERRAFORM_IMAGE?}" \
  init \
  -upgrade \
  -reconfigure \
  -backend-config="access_token=$(gcloud auth print-access-token)" \
  -backend-config="bucket=${TF_PLAN_STORAGE_BUCKET?}" \
  -backend-config="prefix=${PREFIX?}"

sudo docker run \
  -w /app \
  -v "$(pwd)":/app \
  -e GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)" \
  "${TERRAFORM_IMAGE?}" \
  apply \
  --auto-approve \
  -var project_id="${PROJECT_ID?}" \
  -var bucket_name="${BUCKET_NAME?}" \
  "${DESTROY?}"
