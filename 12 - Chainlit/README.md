# Hotel Concierge Assistant with Azure AD Authentication

This Chainlit application provides a hotel concierge service powered by AI agents, with optional Azure Active Directory (Azure AD) authentication.

## Features

- **Multi-Agent AI System**: Uses Semantic Kernel with multiple AI agents for travel recommendations
- **Azure AD Authentication**: Optional OAuth2-based authentication using Azure Active Directory
- **Weather Plugin**: Provides weather information for various cities
- **Interactive Chat Interface**: Built with Chainlit for a smooth user experience

## Setup Instructions

### Prerequisites

1. Python 3.8 or higher
2. An Azure subscription (for Azure AD authentication)
3. Required API keys (see environment variables section)

### Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy the environment configuration:
   ```bash
   cp .env.example .env
   ```

3. Update the `.env` file with your configuration (see Environment Variables section)

### Environment Variables

Edit the `.env` file with the following required variables:

#### Core Application Settings
```bash
GITHUB_TOKEN="your-github-token"
# Add other Azure OpenAI settings as needed
```

#### Azure AD Authentication (Optional)

To enable Azure AD authentication, set these variables:

```bash
OAUTH_AZURE_AD_CLIENT_ID="your-azure-ad-client-id"
OAUTH_AZURE_AD_CLIENT_SECRET="your-azure-ad-client-secret"
OAUTH_AZURE_AD_TENANT_ID="your-azure-ad-tenant-id"
```

**If these variables are not set, the application will run without authentication.**

## Azure AD Setup

### 1. Register an Application in Azure AD

1. Go to the [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Fill in the details:
   - **Name**: Hotel Concierge App (or any name you prefer)
   - **Supported account types**: Choose based on your needs
   - **Redirect URI**: Select "Web" and enter: `http://localhost:8000/auth/oauth/azure-ad/callback`

### 2. Configure the Application

1. After registration, go to **Overview** and copy the **Application (client) ID** → use for `OAUTH_AZURE_AD_CLIENT_ID`
2. Copy the **Directory (tenant) ID** → use for `OAUTH_AZURE_AD_TENANT_ID`
3. Go to **Certificates & secrets** > **Client secrets** > **New client secret**
4. Add a description and expiration, then copy the **Value** → use for `OAUTH_AZURE_AD_CLIENT_SECRET`

### 3. Set API Permissions (Optional)

If you want to access user profile information:
1. Go to **API permissions**
2. Click **Add a permission** > **Microsoft Graph** > **Delegated permissions**
3. Add: `User.Read`, `Profile`, `Email`
4. Click **Grant admin consent** (if you have admin rights)

## Running the Application

### Without Authentication
If you don't set up Azure AD variables, the app runs in open mode:
```bash
chainlit run app.py
```

### With Azure AD Authentication
Set up the Azure AD environment variables in `.env`, then run:
```bash
chainlit run app.py
```

The application will automatically detect the Azure AD configuration and enable authentication.

## Usage

1. **Without Authentication**: Users can immediately start chatting with the hotel concierge agents
2. **With Authentication**: Users must log in with their Azure AD credentials before accessing the chat

### Example Queries

- "What's the weather like in Paris?"
- "What are some fun activities in London?"
- "Recommend places to visit in Tokyo"

## Authentication Flow

When Azure AD is configured:

1. User visits the application
2. Chainlit redirects to Azure AD login
3. User authenticates with Azure AD
4. Azure AD redirects back with user information
5. Application creates a user session with profile data
6. User can now chat with the concierge agents

## Security Considerations

- Keep your client secret secure and never commit it to version control
- Use HTTPS in production environments
- Set appropriate redirect URIs for your deployment environment
- Regularly rotate client secrets as per your organization's security policies

## Troubleshooting

### Common Issues

1. **"Authentication required" message**: Ensure Azure AD environment variables are set correctly
2. **OAuth errors**: Check that redirect URI matches exactly what's configured in Azure AD
3. **Import errors**: Ensure all dependencies are installed with `pip install -r requirements.txt`

### Debug Mode

To see authentication status, check the welcome message when the app starts. It will indicate:
- ✅ Azure AD Authentication: Enabled & Authenticated
- ⚠️ Azure AD Authentication: Enabled but not authenticated  
- ℹ️ Azure AD Authentication: Not configured (running without authentication)

## Development

The authentication implementation consists of:
- `auth.py`: Azure AD OAuth callback and configuration functions
- `app.py`: Main application with conditional authentication checks
- `.chainlit/config.toml`: Chainlit configuration (auto-generated)

To modify authentication behavior, edit the functions in `auth.py`.