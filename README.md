# Project

This lab teaches you how to design and build AI applications and agents using Microsoft Foundry. You will learn how to create AI-powered applications that can interact with users, process natural language, and perform tasks based on user guidance. You will also learn how to monitor, troubleshoot, and perform red teaming activities against agents.

## Step by Step Instructions

The step by step instructions for this lab can be found in the [AI Apps and agents guide](https://microsoft.github.io/TechWorkshop-L300-AI-Apps-and-agents).

## Full GitHub Actions Automation

This repository now includes an end-to-end workflow at `.github/workflows/full_automation_deploy_validate.yml` that:

1. Deploys/updates Azure infrastructure via `src/infra/DeployAzureResources.bicep`
2. Builds and pushes the chat app container image to ACR
3. Updates Azure App Service to the latest container image
4. Ingests catalog data into Cosmos DB
5. Deploys/updates all Foundry agents
6. Runs post-deployment quality checks:
	- Model evaluation (`src/pipelines/run_model_evaluation.py`)
	- Agent evaluation (`src/pipelines/run_agent_evaluation.py`)
	- Prompt smoke tests with tracing (`src/pipelines/run_prompt_smoke_tests.py`)
	- Red teaming scan (`src/app/agents/redTeamingAgent_initializer.py`)

### Required GitHub repository secrets

- `AZURE_CREDENTIALS`
- `ENV`

### Optional (recommended) OIDC secrets for Azure login

If set, the workflow uses OIDC login instead of `AZURE_CREDENTIALS`:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

### Optional workflow_dispatch inputs

- `resource_group`
- `location`
- `run_model_evaluation`
- `run_agent_evaluation`
- `run_prompt_smoke_tests`
- `run_red_teaming`

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
