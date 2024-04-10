<walkthrough-metadata>
  <meta name="title" content="Edit Jumpstart Solution and deploy tutorial " />
  <meta name="description" content="Make it mine neos tutorial" />
  <meta name="component_id" content="1361081" />
  <meta name="short_id" content="true" />
</walkthrough-metadata>

# Customize a Generative AI Knowledge Base Solution

Learn how to build and deploy your own proof of concept based on the deployed [Generative AI Knowledge Base](https://console.cloud.google.com/products/solutions/details/generative-ai-knowledge-base) Jump Start Solution. You can customize the Jump Start Solution deployment by creating a copy of the source code. You can modify the infrastructure and application code as needed and redeploy the solution with the changes.

To avoid conflicts, only one user should modify and deploy a solution in a single Google Cloud project.

## Open cloned repository as workspace

Open the directory where the repository is cloned as a workspace in the editor, follow the steps based on whether you are using the Cloud Shell Editor in Preview Mode or Legacy Mode.

---
**Legacy Cloud Shell Editor**

1. Go to the `File` menu.
2. Select `Open Workspace`.
3. Choose the directory where the repository has been cloned. This directory is the current directory in the cloud shell terminal.

**New Cloud Shell Editor**

1. Go the hamburger icon located in the top left corner of the editor.
2. Go to the `File` Menu.
3. Select `Open Folder`.
4. Choose the directory where the repository has been cloned. This directory is the current directory in the cloud shell terminal.

## Before you begin

We also strongly recommend that you familiarize yourself with the Generative AI Knowledge Base solution by reading the [solution guide](https://cloud.google.com/architecture/big-data-analytics/generative-ai-knowledge-base).

NOTE: A change in the infrastructure code might cause a change in the incurred cost.

---
**Create an automated deployment**

Run the <walkthrough-editor-open-file filePath="./deploy_solution.sh">deploy_solution.sh</walkthrough-editor-open-file> script.

```bash
./deploy_solution.sh
```

---
**Monitor the deployment**

Get the deployment details.

```bash
gcloud infra-manager deployments describe <var>DEPLOYMENT_NAME</var> --location <var>REGION</var>
```

Monitor your deployment at [Solution deployments page](https://console.cloud.google.com/products/solutions/deployments?pageState=(%22deployments%22:(%22f%22:%22%255B%257B_22k_22_3A_22Labels_22_2C_22t_22_3A13_2C_22v_22_3A_22_5C_22modification-reason%2520_3A%2520make-it-mine_5C_22_22_2C_22s_22_3Atrue_2C_22i_22_3A_22deployment.labels_22%257D%255D%22))).

## Save your edits to the solution

Use any of the following methods to save your edits to the solution

---
**Download the solution**

To download your solution, in the `File` menu, select `Download Workspace`. The solution is downloaded in a compressed format.


---
**Save the solution to your Git repository**

Set the remote URL to your Git repository
```bash
git remote set-url origin [git-repo-url]
```

Review the modified files, commit and push to your remote repository branch.

## Delete the deployed solution

Optional: Use one of the below options in case you want to delete the deployed solution

* Go to [Solution deployments page](https://console.cloud.google.com/products/solutions/deployments?pageState=(%22deployments%22:(%22f%22:%22%255B%257B_22k_22_3A_22Labels_22_2C_22t_22_3A13_2C_22v_22_3A_22_5C_22modification-reason%2520_3A%2520make-it-mine_5C_22_22_2C_22s_22_3Atrue_2C_22i_22_3A_22deployment.labels_22%257D%255D%22))).
* Click on the link under "Deployment name". It will take you to the deployment details page for the solution.
* Click on the "DELETE" button located at the top right corner of the page.
<walkthrough-inline-feedback></walkthrough-inline-feedback>
