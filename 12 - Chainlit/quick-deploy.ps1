# Quick Azure Deployment Commands
# Copy and paste these commands one by one in PowerShell

# Set your configuration variables
$RESOURCE_GROUP = "rg-chainlit-app"
$LOCATION = "eastus"
$ACR_NAME = "acrchailitapp$(Get-Random -Maximum 9999)"
$CONTAINER_APP_NAME = "chainlit-support-agent"
$CONTAINER_APP_ENV = "chainlit-env"
$IMAGE_NAME = "chainlit-support-agent"
$IMAGE_TAG = "latest"

# VNET Configuration
$VNET_NAME = "vnet-chainlit-app"
$SUBNET_NAME = "subnet-containerapp"
$LOG_ANALYTICS_WORKSPACE = "log-chainlit-app"

# YOUR AZURE CONFIGURATION - UPDATE THESE VALUES
$AZURE_AI_ENDPOINT = "your_azure_ai_inference_endpoint"
$AZURE_AI_API_KEY = "your_azure_ai_inference_api_key"
$AZURE_AI_MODEL_NAME = "gpt-4o-mini"
$AZURE_SEARCH_ENDPOINT = "your_azure_search_endpoint"
$AZURE_SEARCH_KEY = "your_azure_search_key"
$AZURE_SEARCH_INDEX = "your_azure_search_index"

Write-Host "ACR Name will be: $ACR_NAME"

# 1. Create Resource Group
az group create --name $RESOURCE_GROUP --location $LOCATION

# 2. Create ACR
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true

# 3. Get ACR login server
$ACR_LOGIN_SERVER = az acr show --name $ACR_NAME --query loginServer --output tsv
Write-Host "ACR Login Server: $ACR_LOGIN_SERVER"

# 4. Create Virtual Network and Log Analytics
az network vnet create `
  --resource-group $RESOURCE_GROUP `
  --name $VNET_NAME `
  --location $LOCATION `
  --address-prefixes 10.0.0.0/16 `
  --subnet-name $SUBNET_NAME `
  --subnet-prefixes 10.0.0.0/21

# Get subnet ID
$SUBNET_ID = az network vnet subnet show `
  --resource-group $RESOURCE_GROUP `
  --vnet-name $VNET_NAME `
  --name $SUBNET_NAME `
  --query id `
  --output tsv

Write-Host "Subnet ID: $SUBNET_ID"

# Create Log Analytics workspace
az monitor log-analytics workspace create `
  --resource-group $RESOURCE_GROUP `
  --workspace-name $LOG_ANALYTICS_WORKSPACE `
  --location $LOCATION

# Get Log Analytics workspace details
$LOG_ANALYTICS_WORKSPACE_ID = az monitor log-analytics workspace show `
  --resource-group $RESOURCE_GROUP `
  --workspace-name $LOG_ANALYTICS_WORKSPACE `
  --query customerId `
  --output tsv

$LOG_ANALYTICS_WORKSPACE_KEY = az monitor log-analytics workspace get-shared-keys `
  --resource-group $RESOURCE_GROUP `
  --workspace-name $LOG_ANALYTICS_WORKSPACE `
  --query primarySharedKey `
  --output tsv

Write-Host "Log Analytics Workspace ID: $LOG_ANALYTICS_WORKSPACE_ID"

# 5. Build and push image using ACR Tasks (navigate to project directory first)
Set-Location "c:\dev\Multi-Agents\ailabs\AIAgentsLabs\12 - Chainlit"
az acr build --registry $ACR_NAME --image "${IMAGE_NAME}:${IMAGE_TAG}" .

# 6. Create Container Apps Environment with VNET Integration
az containerapp env create `
  --name $CONTAINER_APP_ENV `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --infrastructure-subnet-resource-id $SUBNET_ID `
  --internal-only false `
  --logs-workspace-id $LOG_ANALYTICS_WORKSPACE_ID `
  --logs-workspace-key $LOG_ANALYTICS_WORKSPACE_KEY

# 7. Create Container App
az containerapp create `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --environment $CONTAINER_APP_ENV `
  --image "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}" `
  --registry-server $ACR_LOGIN_SERVER `
  --target-port 8000 `
  --ingress external `
  --min-replicas 1 `
  --max-replicas 3 `
  --cpu 1.0 `
  --memory 2.0Gi `
  --env-vars "PYTHONPATH=/app" "PORT=8000"

# 8. Set environment variables (update with your actual values)
az containerapp update `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --set-env-vars `
    "AZURE_AI_MODEL_INFERENCE_ENDPOINT=$AZURE_AI_ENDPOINT" `
    "AZURE_AI_MODEL_INFERENCE_API_KEY=$AZURE_AI_API_KEY" `
    "AZURE_AI_MODEL_DEPLOYMENT_NAME=$AZURE_AI_MODEL_NAME" `
    "AZURE_SEARCH_ENDPOINT=$AZURE_SEARCH_ENDPOINT" `
    "AZURE_SEARCH_KEY=$AZURE_SEARCH_KEY" `
    "AZURE_SEARCH_INDEX=$AZURE_SEARCH_INDEX"

# 9. Get application URL
$APP_URL = az containerapp show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn --output tsv
Write-Host "🎉 Application URL: https://$APP_URL"

# Optional: View logs
# az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow
