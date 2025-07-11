# Azure Container Apps Deployment Script
# This script deploys the Chainlit application to Azure Container Registry and Container Apps

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$Location = "eastus",
    
    [Parameter(Mandatory=$false)]
    [string]$AcrName = "acrchailitapp$(Get-Random -Maximum 9999)",
    
    [Parameter(Mandatory=$false)]
    [string]$ContainerAppName = "chainlit-support-agent",
    
    [Parameter(Mandatory=$false)]
    [string]$ContainerAppEnv = "chainlit-env",
    
    [Parameter(Mandatory=$false)]
    [string]$ImageName = "chainlit-support-agent",
    
    [Parameter(Mandatory=$false)]
    [string]$ImageTag = "latest",
    
    # Network Configuration
    [Parameter(Mandatory=$false)]
    [string]$VnetName = "vnet-chainlit-app",
    
    [Parameter(Mandatory=$false)]
    [string]$SubnetName = "subnet-containerapp",
    
    [Parameter(Mandatory=$false)]
    [string]$LogAnalyticsWorkspace = "log-chainlit-app",
    
    # Azure AI Configuration
    [Parameter(Mandatory=$true)]
    [string]$AzureAIEndpoint,
    
    [Parameter(Mandatory=$true)]
    [string]$AzureAIApiKey,
    
    [Parameter(Mandatory=$false)]
    [string]$AzureAIModelName = "gpt-4o-mini",
    
    # Azure Search Configuration (optional)
    [Parameter(Mandatory=$false)]
    [string]$AzureSearchEndpoint = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AzureSearchKey = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AzureSearchIndex = ""
)

# Function to check if Azure CLI is logged in
function Test-AzureLogin {
    try {
        $account = az account show --query name -o tsv 2>$null
        if ($account) {
            Write-Host "✓ Logged in to Azure as: $account" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "✗ Not logged in to Azure" -ForegroundColor Red
        return $false
    }
}

# Function to create resource group if it doesn't exist
function New-ResourceGroupIfNotExists {
    param([string]$Name, [string]$Location)
    
    $exists = az group exists --name $Name
    if ($exists -eq "false") {
        Write-Host "Creating resource group: $Name" -ForegroundColor Yellow
        az group create --name $Name --location $Location
    } else {
        Write-Host "✓ Resource group $Name already exists" -ForegroundColor Green
    }
}

# Main deployment function
function Deploy-ChainlitApp {
    Write-Host "🚀 Starting Chainlit App Deployment to Azure" -ForegroundColor Cyan
    Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor White
    Write-Host "Location: $Location" -ForegroundColor White
    Write-Host "ACR Name: $AcrName" -ForegroundColor White
    Write-Host "Container App: $ContainerAppName" -ForegroundColor White
    
    # Check Azure login
    if (-not (Test-AzureLogin)) {
        Write-Host "Please login to Azure first: az login" -ForegroundColor Red
        return
    }
    
    try {
        # Step 1: Create Resource Group
        Write-Host "📦 Step 1: Creating Resource Group" -ForegroundColor Cyan
        New-ResourceGroupIfNotExists -Name $ResourceGroupName -Location $Location
        
        # Step 2: Create ACR
        Write-Host "📦 Step 2: Creating Azure Container Registry" -ForegroundColor Cyan
        $acrExists = az acr show --name $AcrName --resource-group $ResourceGroupName --query name -o tsv 2>$null
        if (-not $acrExists) {
            az acr create --resource-group $ResourceGroupName --name $AcrName --sku Basic --admin-enabled true
            Write-Host "✓ ACR created successfully" -ForegroundColor Green
        } else {
            Write-Host "✓ ACR already exists" -ForegroundColor Green
        }
        
        # Get ACR login server
        $acrLoginServer = az acr show --name $AcrName --query loginServer --output tsv
        Write-Host "ACR Login Server: $acrLoginServer" -ForegroundColor White
        
        # Step 3: Build and Push Image using ACR Tasks
        Write-Host "🔨 Step 3: Building image using ACR Tasks" -ForegroundColor Cyan
        $currentDir = Get-Location
        Set-Location "c:\dev\Multi-Agents\ailabs\AIAgentsLabs\12 - Chainlit"
        
        az acr build --registry $AcrName --image "${ImageName}:${ImageTag}" .
        Write-Host "✓ Image built and pushed successfully" -ForegroundColor Green
        
        Set-Location $currentDir
        
        # Step 4: Create Virtual Network and Log Analytics
        Write-Host "� Step 4: Creating Virtual Network and Log Analytics" -ForegroundColor Cyan
        
        # Create VNet
        $vnetExists = az network vnet show --name $VnetName --resource-group $ResourceGroupName --query name -o tsv 2>$null
        if (-not $vnetExists) {
            az network vnet create `
                --resource-group $ResourceGroupName `
                --name $VnetName `
                --location $Location `
                --address-prefixes 10.0.0.0/16 `
                --subnet-name $SubnetName `
                --subnet-prefixes 10.0.0.0/21
            Write-Host "✓ VNet created successfully" -ForegroundColor Green
        } else {
            Write-Host "✓ VNet already exists" -ForegroundColor Green
        }
        
        # Get subnet ID
        $subnetId = az network vnet subnet show `
            --resource-group $ResourceGroupName `
            --vnet-name $VnetName `
            --name $SubnetName `
            --query id `
            --output tsv
        Write-Host "Subnet ID: $subnetId" -ForegroundColor White
        
        # Create Log Analytics workspace
        $logWorkspaceExists = az monitor log-analytics workspace show --name $LogAnalyticsWorkspace --resource-group $ResourceGroupName --query name -o tsv 2>$null
        if (-not $logWorkspaceExists) {
            az monitor log-analytics workspace create `
                --resource-group $ResourceGroupName `
                --workspace-name $LogAnalyticsWorkspace `
                --location $Location
            Write-Host "✓ Log Analytics workspace created" -ForegroundColor Green
        } else {
            Write-Host "✓ Log Analytics workspace already exists" -ForegroundColor Green
        }
        
        # Get Log Analytics workspace details
        $logWorkspaceId = az monitor log-analytics workspace show `
            --resource-group $ResourceGroupName `
            --workspace-name $LogAnalyticsWorkspace `
            --query customerId `
            --output tsv
        
        $logWorkspaceKey = az monitor log-analytics workspace get-shared-keys `
            --resource-group $ResourceGroupName `
            --workspace-name $LogAnalyticsWorkspace `
            --query primarySharedKey `
            --output tsv
        
        Write-Host "Log Analytics Workspace ID: $logWorkspaceId" -ForegroundColor White
        # Step 5: Create Container Apps Environment with VNET Integration
        Write-Host "🌍 Step 5: Creating Container Apps Environment with VNET Integration" -ForegroundColor Cyan
        $envExists = az containerapp env show --name $ContainerAppEnv --resource-group $ResourceGroupName --query name -o tsv 2>$null
        if (-not $envExists) {
            az containerapp env create `
                --name $ContainerAppEnv `
                --resource-group $ResourceGroupName `
                --location $Location `
                --infrastructure-subnet-resource-id $subnetId `
                --internal-only false `
                --logs-workspace-id $logWorkspaceId `
                --logs-workspace-key $logWorkspaceKey
            Write-Host "✓ Container Apps environment created with VNET integration" -ForegroundColor Green
        } else {
            Write-Host "✓ Container Apps environment already exists" -ForegroundColor Green
        }
        Write-Host "🚀 Step 6: Creating Container App" -ForegroundColor Cyan
        $appExists = az containerapp show --name $ContainerAppName --resource-group $ResourceGroupName --query name -o tsv 2>$null
        if (-not $appExists) {
            az containerapp create `
                --name $ContainerAppName `
                --resource-group $ResourceGroupName `
                --environment $ContainerAppEnv `
                --image "${acrLoginServer}/${ImageName}:${ImageTag}" `
                --registry-server $acrLoginServer `
                --target-port 8000 `
                --ingress external `
                --min-replicas 1 `
                --max-replicas 3 `
                --cpu 1.0 `
                --memory 2.0Gi `
                --env-vars "PYTHONPATH=/app" "PORT=8000"
            
            Write-Host "✓ Container App created successfully" -ForegroundColor Green
        } else {
            Write-Host "✓ Container App already exists, updating..." -ForegroundColor Yellow
            az containerapp update `
                --name $ContainerAppName `
                --resource-group $ResourceGroupName `
                --image "${acrLoginServer}/${ImageName}:${ImageTag}"
        }
        
        # Step 7: Set Environment Variables
        Write-Host "⚙️ Step 7: Setting Environment Variables" -ForegroundColor Cyan
        $envVars = @(
            "AZURE_AI_MODEL_INFERENCE_ENDPOINT=$AzureAIEndpoint",
            "AZURE_AI_MODEL_INFERENCE_API_KEY=$AzureAIApiKey",
            "AZURE_AI_MODEL_DEPLOYMENT_NAME=$AzureAIModelName"
        )
        
        if ($AzureSearchEndpoint) {
            $envVars += "AZURE_SEARCH_ENDPOINT=$AzureSearchEndpoint"
        }
        if ($AzureSearchKey) {
            $envVars += "AZURE_SEARCH_KEY=$AzureSearchKey"
        }
        if ($AzureSearchIndex) {
            $envVars += "AZURE_SEARCH_INDEX=$AzureSearchIndex"
        }
        
        az containerapp update `
            --name $ContainerAppName `
            --resource-group $ResourceGroupName `
            --set-env-vars $envVars
        
        Write-Host "✓ Environment variables set successfully" -ForegroundColor Green
        
        # Step 8: Get Application URL
        Write-Host "🌐 Step 8: Getting Application URL" -ForegroundColor Cyan
        $appUrl = az containerapp show --name $ContainerAppName --resource-group $ResourceGroupName --query properties.configuration.ingress.fqdn --output tsv
        
        Write-Host "🎉 Deployment completed successfully!" -ForegroundColor Green
        Write-Host "Application URL: https://$appUrl" -ForegroundColor Yellow
        Write-Host "You can now access your Chainlit application at the above URL" -ForegroundColor White
        
    }
    catch {
        Write-Host "❌ Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

# Execute deployment
Deploy-ChainlitApp
