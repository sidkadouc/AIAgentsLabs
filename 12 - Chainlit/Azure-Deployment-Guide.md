# Azure Container Registry and Container Apps Deployment Guide

This guide walks you through deploying your Chainlit application to Azure Container Registry (ACR) and running it with Azure Container Apps.

## Prerequisites

1. Azure CLI installed and logged in
2. Azure subscription with appropriate permissions
3. Resource group created (or create one as shown below)

## Step 1: Set Environment Variables

```bash
# Set your variables
$RESOURCE_GROUP = "rg-chainlit-app"
$LOCATION = "eastus"
$ACR_NAME = "acrchailitapp$(Get-Random -Maximum 9999)"  # Must be globally unique
$CONTAINER_APP_NAME = "chainlit-support-agent"
$CONTAINER_APP_ENV = "chainlit-env"
$IMAGE_NAME = "chainlit-support-agent"
$IMAGE_TAG = "latest"

# VNET Configuration
$VNET_NAME = "vnet-chainlit-app"
$SUBNET_NAME = "subnet-containerapp"

# Log Analytics (optional but recommended)
$LOG_ANALYTICS_WORKSPACE = "log-chainlit-app"

# Display the ACR name for reference
Write-Host "ACR Name: $ACR_NAME"
```

## Step 2: Create Resource Group (if not exists)

```bash
# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION
```

## Step 3: Create Azure Container Registry

```bash
# Create ACR with Basic SKU (you can use Standard or Premium for production)
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true

# Get ACR login server
$ACR_LOGIN_SERVER = az acr show --name $ACR_NAME --query loginServer --output tsv
Write-Host "ACR Login Server: $ACR_LOGIN_SERVER"
```

## Step 4: Build Image using ACR Tasks

```bash
# Navigate to your project directory
cd "c:\dev\Multi-Agents\ailabs\AIAgentsLabs\12 - Chainlit"

# Build and push image using ACR Tasks (no local Docker required)
az acr build --registry $ACR_NAME --image "${IMAGE_NAME}:${IMAGE_TAG}" .

# Verify the image was built
az acr repository list --name $ACR_NAME --output table
az acr repository show-tags --name $ACR_NAME --repository $IMAGE_NAME --output table
```

## Step 5: Create Virtual Network and Container Apps Environment

```bash
# Create Virtual Network for Container Apps
$VNET_NAME = "vnet-chainlit-app"
$SUBNET_NAME = "subnet-containerapp"

# Create VNet with appropriate address space
az network vnet create \
  --resource-group $RESOURCE_GROUP \
  --name $VNET_NAME \
  --location $LOCATION \
  --address-prefixes 10.0.0.0/16 \
  --subnet-name $SUBNET_NAME \
  --subnet-prefixes 10.0.0.0/21

# Get the subnet ID for Container Apps environment
$SUBNET_ID = az network vnet subnet show \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $SUBNET_NAME \
  --query id \
  --output tsv

Write-Host "Subnet ID: $SUBNET_ID"

# Create Container Apps environment with VNET integration
az containerapp env create \
  --name $CONTAINER_APP_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --infrastructure-subnet-resource-id $SUBNET_ID \
  --internal-only false \
  --logs-workspace-id $LOG_ANALYTICS_WORKSPACE_ID
```

### Optional: Create Log Analytics Workspace for better monitoring

```bash
# Create Log Analytics workspace (recommended for production)
$LOG_ANALYTICS_WORKSPACE = "log-chainlit-app"

az monitor log-analytics workspace create \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $LOG_ANALYTICS_WORKSPACE \
  --location $LOCATION

# Get the workspace ID
$LOG_ANALYTICS_WORKSPACE_ID = az monitor log-analytics workspace show \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $LOG_ANALYTICS_WORKSPACE \
  --query customerId \
  --output tsv

$LOG_ANALYTICS_WORKSPACE_KEY = az monitor log-analytics workspace get-shared-keys \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $LOG_ANALYTICS_WORKSPACE \
  --query primarySharedKey \
  --output tsv

Write-Host "Log Analytics Workspace ID: $LOG_ANALYTICS_WORKSPACE_ID"
```

### Alternative: Simple Container Apps Environment (without Log Analytics)

```bash
# If you don't want Log Analytics, use this simpler version
az containerapp env create \
  --name $CONTAINER_APP_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --infrastructure-subnet-resource-id $SUBNET_ID \
  --internal-only false
```

## Step 6: Create Container App

```bash
# Create the container app
az containerapp create \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_APP_ENV \
  --image "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}" \
  --registry-server $ACR_LOGIN_SERVER \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 1.0 \
  --memory 2.0Gi \
  --env-vars "PYTHONPATH=/app" "PORT=8000"
```

## Step 7: Set Environment Variables (Azure Configuration)

```bash
# Set your Azure AI and Search configuration
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    "AZURE_AI_MODEL_INFERENCE_ENDPOINT=your_azure_ai_inference_endpoint" \
    "AZURE_AI_MODEL_INFERENCE_API_KEY=your_azure_ai_inference_api_key" \
    "AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini" \
    "AZURE_SEARCH_ENDPOINT=your_azure_search_endpoint" \
    "AZURE_SEARCH_KEY=your_azure_search_key" \
    "AZURE_SEARCH_INDEX=your_azure_search_index"
```

## Step 8: Get Application URL

```bash
# Get the application URL
$APP_URL = az containerapp show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn --output tsv
Write-Host "Application URL: https://$APP_URL"
```

## Alternative: Using Secrets for Sensitive Data

For production deployments, use Azure Container Apps secrets instead of environment variables:

```bash
# Create secrets for sensitive data
az containerapp secret set \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --secrets \
    "azure-ai-api-key=your_azure_ai_inference_api_key" \
    "azure-search-key=your_azure_search_key"

# Update app to use secrets
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    "AZURE_AI_MODEL_INFERENCE_ENDPOINT=your_azure_ai_inference_endpoint" \
    "AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini" \
    "AZURE_SEARCH_ENDPOINT=your_azure_search_endpoint" \
    "AZURE_SEARCH_INDEX=your_azure_search_index" \
  --replace-env-vars \
    "AZURE_AI_MODEL_INFERENCE_API_KEY=secretref:azure-ai-api-key" \
    "AZURE_SEARCH_KEY=secretref:azure-search-key"
```

## Monitoring and Management Commands

```bash
# View container app logs
az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow

# Check container app status
az containerapp show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --query properties.runningStatus

# Scale the application
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 2 \
  --max-replicas 5

# Update the application with a new image
az acr build --registry $ACR_NAME --image "${IMAGE_NAME}:v2" .
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:v2"
```

## Cleanup Commands

```bash
# Delete the container app
az containerapp delete --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --yes

# Delete the container apps environment
az containerapp env delete --name $CONTAINER_APP_ENV --resource-group $RESOURCE_GROUP --yes

# Delete the ACR
az acr delete --name $ACR_NAME --resource-group $RESOURCE_GROUP --yes

# Delete the resource group (this deletes everything)
az group delete --name $RESOURCE_GROUP --yes
```

## Network Security Considerations

### Network Security Groups (NSGs)

```bash
# Create NSG for additional security (optional)
$NSG_NAME = "nsg-chainlit-app"

az network nsg create \
  --resource-group $RESOURCE_GROUP \
  --name $NSG_NAME \
  --location $LOCATION

# Add rules to allow HTTPS traffic
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name $NSG_NAME \
  --name "AllowHTTPS" \
  --protocol Tcp \
  --priority 1000 \
  --destination-port-range 443 \
  --access Allow \
  --direction Inbound

# Add rules to allow HTTP traffic (if needed)
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name $NSG_NAME \
  --name "AllowHTTP" \
  --protocol Tcp \
  --priority 1001 \
  --destination-port-range 80 \
  --access Allow \
  --direction Inbound

# Associate NSG with subnet
az network vnet subnet update \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $SUBNET_NAME \
  --network-security-group $NSG_NAME
```

### Private DNS Zone (for custom domains)

```bash
# Create private DNS zone if you plan to use custom domains
$PRIVATE_DNS_ZONE = "privatelink.azurecontainerapps.io"

az network private-dns zone create \
  --resource-group $RESOURCE_GROUP \
  --name $PRIVATE_DNS_ZONE

# Link the private DNS zone to the VNet
az network private-dns link vnet create \
  --resource-group $RESOURCE_GROUP \
  --zone-name $PRIVATE_DNS_ZONE \
  --name "dns-link-chainlit" \
  --virtual-network $VNET_NAME \
  --registration-enabled false
```

## Cost Optimization Tips

1. **Use consumption-based pricing** for Container Apps
2. **Set appropriate min/max replicas** based on your traffic
3. **Use Basic SKU for ACR** for development/testing
4. **Enable auto-scaling** based on HTTP requests or CPU/memory
5. **Use managed identity** instead of admin credentials for production
6. **Monitor VNet costs** - VNET integration may incur additional charges
7. **Use shared Log Analytics workspace** across multiple environments

## Troubleshooting

```bash
# Check container app events
az containerapp revision list --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --output table

# Get detailed information about a specific revision
az containerapp revision show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --revision [REVISION_NAME]

# Check ACR repositories
az acr repository list --name $ACR_NAME --output table

# Test ACR connectivity
az acr check-health --name $ACR_NAME
```

Remember to replace the placeholder values with your actual Azure AI Inference and Search credentials before running the deployment commands.
