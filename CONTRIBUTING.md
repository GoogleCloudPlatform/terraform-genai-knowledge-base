# Contributing

We'd love to accept your patches and contributions to this project. There are
just a few small guidelines you need to follow.

## Contributor License Agreement

Contributions to this project must be accompanied by a Contributor License
Agreement (CLA). You (or your employer) retain the copyright to your
contribution; this simply gives us permission to use and redistribute your
contributions as part of the project. Head over to
<https://cla.developers.google.com/> to see your current agreements on file or
to sign a new one.

You generally only need to submit a CLA once, so if you've already submitted one
(even if it was for a different project), you probably don't need to do it
again.

## Code Reviews

All submissions, including submissions by project members, require review. We
use GitHub pull requests for this purpose. Consult
[GitHub Help](https://help.github.com/articles/about-pull-requests/) for more
information on using pull requests.

## Development

The following dependencies must be installed on the development system:

- [Docker Engine](https://docs.docker.com/engine/install/)
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- [make](https://www.gnu.org/software/make/)

### Generating Documentation for Inputs and Outputs

The Inputs and Outputs tables in the READMEs of the root module,
submodules, and example modules are automatically generated based on
the `variables` and `outputs` of the respective modules. These tables
must be refreshed if the module interfaces are changed.

#### Execution

Run `make generate_docs` to generate new Inputs and Outputs tables.

### Integration Testing

Integration tests are used to verify the behaviour of the root module,
submodules, and example modules. Additions, changes, and fixes should
be accompanied with tests.

The integration tests are run using [Kitchen][kitchen],
[Kitchen-Terraform][kitchen-terraform], and [InSpec][inspec]. These
tools are packaged within a Docker image for convenience.

The general strategy for these tests is to verify the behaviour of the
[example modules](./examples/), thus ensuring that the root module,
submodules, and example modules are all functionally correct.

#### Test Environment
The easiest way to test the module is in an isolated test project.
The setup for such a project is defined in [test/setup](./test/setup/) directory.

You must have an existing "Management project" to manage the test projects.
This project is used to create a "Test project" where the tests are run.

In the "Management project":

1. Enable the Resource Manager, Identity and Access Management (IAM), and Billing APIs:

   [Click here to enable the APIs](https://console.cloud.google.com/flows/enableapi?apiid=cloudresourcemanager.googleapis.com,iam.googleapis.com,cloudbilling.googleapis.com)

1. [Create a service account](https://cloud.google.com/iam/docs/service-accounts-create), this will be used to create the test project.

1. [Grant the following roles](https://cloud.google.com/iam/docs/manage-access-service-accounts) to the service account:
   - `roles/billing.projectManager`
   <!-- - `roles/resourcemanager.organizationViewer` -->
   <!-- - `roles/resourcemanager.projectCreator` -->

1. [Create a service account key](https://cloud.google.com/iam/docs/keys-create-delete) and save it to `credentials.json` in the root directory of this repository.
   Any file called `credentials.json` is in the [`.gitignore`](.gitignore) so you won't accidentally commit it.

In your development environment:

1. Export the service account credentials to the `SERVICE_ACCOUNT_JSON` environment variable like so:

   ```sh
   export SERVICE_ACCOUNT_JSON=$(< credentials.json)
   ```

1. Export the following environment variables to configure the test project:

   ```sh
   export TF_VAR_org_id="your_org_id"
   export TF_VAR_folder_id="your_folder_id"
   export TF_VAR_billing_account="your_billing_account_id"
   ```

   > 💡 To find your current settings:
   >
   > ```sh
   > gcloud organizations list
   > gcloud resource-manager folders list --organization=$TF_VAR_org_id --format='value(name)'
   > gcloud beta billing projects describe $PROJECT_ID --format='value(billingAccountName)'
   > ```

1. Create and prepare a new test project using Docker:

   ```sh
   make docker_test_prepare
   ```

#### Noninteractive Execution

Run `make docker_test_integration` to test all of the example modules
noninteractively, using the prepared test project.

#### Interactive Execution

1. Run `make docker_run` to start the testing Docker container in
   interactive mode.

1. Run `kitchen_do create <EXAMPLE_NAME>` to initialize the working
   directory for an example module.

1. Run `kitchen_do converge <EXAMPLE_NAME>` to apply the example module.

1. Run `kitchen_do verify <EXAMPLE_NAME>` to test the example module.

1. Run `kitchen_do destroy <EXAMPLE_NAME>` to destroy the example module
   state.

### Running the webhook tests locally

#### Prerequisites

Authenticate:

```sh
gcloud auth application-default login
```

Make sure you `cd` into this directory before running the tests.

```sh
cd webhook/
```

Install the dependencies:

```sh
# Specify the project ID to use for the test.
export PROJECT_ID=my-project

# Install the dependencies on a virtual environment.
python -m venv env
source env/bin/activate
pip install -r requirements.txt -r requirements-test.txt
```

#### Running the tests end-to-end

To run the tests creating and destroying all resources, run:

```sh
# Ignore deprecation warnings for cleaner outputs.
python -m pytest -v -s -W ignore::DeprecationWarning
```

#### Running the tests with persistent resources

> ⚠️ WARNING: reusing resources from a previous run may lead to unexpected behavior.
> For example, files created from a previous run may cause tests to succeed even if they should fail.

To avoid creating and destroying resources when debugging, you can use
persistent resources.

```sh
export TEST_UUID=$USER
export TEST_SKIP_DESTROY=1
```

Then, run the tests:

```sh
python -m pytest -v -s -W ignore::DeprecationWarning

# If you already have created the resources, you can skip all Terraform steps.
export TEST_SKIP_INIT=1
export TEST_SKIP_APPLY=1
```

Once you're finished, delete the resources manually:

```sh
terraform -chdir=.. destroy -auto-approve -var=project_id=$PROJECT_ID
```

### Linting and Formatting

Many of the files in the repository can be linted or formatted to
maintain a standard of quality.

#### Execution

Run `make docker_test_lint`.

[docker-engine]: https://www.docker.com/products/docker-engine
[flake8]: http://flake8.pycqa.org/en/latest/
[gofmt]: https://golang.org/cmd/gofmt/
[google-cloud-sdk]: https://cloud.google.com/sdk/install
[hadolint]: https://github.com/hadolint/hadolint
[inspec]: https://inspec.io/
[kitchen-terraform]: https://github.com/newcontext-oss/kitchen-terraform
[kitchen]: https://kitchen.ci/
[make]: https://en.wikipedia.org/wiki/Make_(software)
[shellcheck]: https://www.shellcheck.net/
[terraform-docs]: https://github.com/segmentio/terraform-docs
[terraform]: https://terraform.io/
