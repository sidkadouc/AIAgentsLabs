"""
Azure Active Directory authentication for Chainlit

This module provides authentication functions for Azure AD integration.
To enable Azure AD authentication:

1. Set up an Azure AD app registration:
   - Go to https://portal.azure.com
   - Navigate to Azure Active Directory > App registrations
   - Click "New registration"
   - Add redirect URI: http://localhost:8000/auth/oauth/azure-ad/callback
   - Generate a client secret in "Certificates & secrets"

2. Set environment variables:
   - OAUTH_AZURE_AD_CLIENT_ID
   - OAUTH_AZURE_AD_CLIENT_SECRET  
   - OAUTH_AZURE_AD_TENANT_ID

3. Restart the Chainlit application
"""
import os
import chainlit as cl
from typing import Optional


def setup_oauth_callback():
    """
    Set up OAuth callback for Azure AD authentication.
    Call this function after environment variables are loaded.
    """
    @cl.oauth_callback
    def oauth_callback(
        provider_id: str,
        token: str,
        raw_user_data: dict,
        default_user: cl.User,
    ) -> Optional[cl.User]:
        """
        OAuth callback for Azure AD authentication.
        """
        if provider_id != "azure-ad":
            return None
        
        try:
            # Extract user information from Azure AD response
            user_id = raw_user_data.get("oid") or raw_user_data.get("sub") or raw_user_data.get("id")
            display_name = raw_user_data.get("name") or raw_user_data.get("displayName", "")
            email = raw_user_data.get("email") or raw_user_data.get("mail") or raw_user_data.get("userPrincipalName", "")
            
            if not user_id:
                print("Failed to get user ID from Azure AD response")
                return None
                
            # Create authenticated user
            return cl.User(
                identifier=user_id,
                metadata={
                    "email": email,
                    "name": display_name,
                    "provider": "azure-ad",
                    "token": token,
                    "raw_data": raw_user_data
                }
            )
            
        except Exception as e:
            print(f"Error in oauth_callback: {e}")
            return None
    
    return oauth_callback


def is_azure_ad_configured():
    """Check if Azure AD OAuth is properly configured."""
    required_vars = [
        "OAUTH_AZURE_AD_CLIENT_ID",
        "OAUTH_AZURE_AD_CLIENT_SECRET", 
        "OAUTH_AZURE_AD_TENANT_ID"
    ]
    return all(os.getenv(var) for var in required_vars)