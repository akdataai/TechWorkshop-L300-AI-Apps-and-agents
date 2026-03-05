# GitHub Actions Secrets Reference

This document lists every secret that must be created in your GitHub repository's **Settings → Secrets and variables → Actions** before the workflows in this project can run successfully.

---

## How to add a secret

1. Go to your fork of this repository on GitHub.
2. Click **Settings** → **Secrets and variables** → **Actions**.
3. Click **New repository secret**.
4. Enter the **Name** exactly as shown below and paste the **Value**.

---

## Required secrets

### `ENV`

**Used by:** `deploy-acr.yml`, `deploy-customer-loyalty-agent.yml`

The entire contents of your `.env` file, pasted as a single multi-line secret. The workflow writes this value to `src/.env` on the runner before any Python or Docker steps run.

Copy `src/env_sample.txt`, fill in all the blank values, and paste the result here.

```
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT="true"
AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED="true"

# Microsoft Foundry credentials
FOUNDRY_ENDPOINT=""
FOUNDRY_KEY=""
FOUNDRY_API_VERSION="2025-01-01-preview"

# GPT credentials
gpt_endpoint=""
gpt_deployment="gpt-5-mini"
gpt_api_key=""
gpt_api_version="2025-01-01-preview"

# Text-embedding-3-large credentials
embedding_endpoint=""
embedding_deployment="text-embedding-3-large"
embedding_api_key=""
embedding_api_version="2025-01-01-preview"

# Phi-4 credentials
phi_4_endpoint=""
phi_4_deployment="Phi-4"
phi_4_api_key=""
phi_4_api_version="2024-05-01-preview"

# Storage account credentials
blob_connection_string=""
storage_account_name=""
storage_container_name="zava"

# Cosmos DB credentials
COSMOS_ENDPOINT=""
COSMOS_KEY=""
DATABASE_NAME="zava"
CONTAINER_NAME="product_catalog"

# Application Insights credentials
APPLICATIONINSIGHTS_CONNECTION_STRING=""

# MCP Server URL
MCP_SERVER_URL="http://localhost:8000/mcp-inventory/sse"

# Agent IDs
customer_loyalty="customer-loyalty"
inventory_agent="inventory-agent"
interior_designer="interior-designer"
cora="cora"
cart_manager="cart-manager"
handoff_service="handoff-service"
```

---

### `AZURE_CONTAINER_REGISTRY`

**Used by:** `deploy-acr.yml`

The **login server** hostname of your Azure Container Registry.

| Where to find it | Azure Portal → your Container Registry → **Overview** → **Login server** |
|---|---|
| Example value | `myregistry.azurecr.io` |

---

### `AZURE_CONTAINER_REGISTRY_USERNAME`

**Used by:** `deploy-acr.yml`

The **admin username** for your Azure Container Registry.

| Where to find it | Azure Portal → your Container Registry → **Settings** → **Access keys** → **Username** (admin user must be enabled) |
|---|---|
| Example value | `myregistry` |

You can also retrieve it via the Azure CLI:

```bash
az acr credential show --name <registry-name> --query username -o tsv
```

---

### `AZURE_CONTAINER_REGISTRY_PASSWORD`

**Used by:** `deploy-acr.yml`

One of the two **admin passwords** for your Azure Container Registry.

| Where to find it | Azure Portal → your Container Registry → **Settings** → **Access keys** → **password** or **password2** |
|---|---|
| Example value | *(a long random string)* |

You can also retrieve it via the Azure CLI:

```bash
az acr credential show --name <registry-name> --query "passwords[0].value" -o tsv
```

---

### `AZURE_CREDENTIALS`

**Used by:** `deploy-customer-loyalty-agent.yml` (and any future workflow that uses `azure/login`)

A JSON object containing the credentials for an Azure service principal. This is used by the `azure/login@v2` action to authenticate the Azure CLI.

Create a service principal and capture its output:

```bash
az ad sp create-for-rbac \
  --name "github-actions-sp" \
  --role contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/<resource-group> \
  --sdk-auth
```

Paste the entire JSON output as the secret value:

```json
{
  "clientId": "<app-id>",
  "clientSecret": "<client-secret>",
  "subscriptionId": "<subscription-id>",
  "tenantId": "<tenant-id>",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

---

## Summary table

| Secret name | Required by | Description |
|---|---|---|
| `ENV` | `deploy-acr.yml`, `deploy-customer-loyalty-agent.yml` | Full contents of the `.env` file (see `src/env_sample.txt`) |
| `AZURE_CONTAINER_REGISTRY` | `deploy-acr.yml` | ACR login server hostname, e.g. `myregistry.azurecr.io` |
| `AZURE_CONTAINER_REGISTRY_USERNAME` | `deploy-acr.yml` | ACR admin username |
| `AZURE_CONTAINER_REGISTRY_PASSWORD` | `deploy-acr.yml` | ACR admin password |
| `AZURE_CREDENTIALS` | `deploy-customer-loyalty-agent.yml` | Azure service principal JSON (from `az ad sp create-for-rbac --sdk-auth`) |
