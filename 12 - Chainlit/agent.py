import os
import logging
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.functions import kernel_function, KernelArguments
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from datetime import datetime
from vector_search_plugin import VectorSearchPlugin
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from config import config
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Global variables for agent and plugins
AGENT_KERNEL = None
FAQ_PLUGIN = None
SUPPORT_AGENT = None
HISTORY_MEMORY = None
brand = config["azure"].get("brand", "Support")

# Import our HistoryMemory class
from history_memory import HistoryMemory


def initialize_agent_and_plugins():
    """Initialize the Semantic Kernel agent and plugins."""
    global AGENT_KERNEL, FAQ_PLUGIN, SUPPORT_AGENT, HISTORY_MEMORY
    
    # Load environment variables or config
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT") or config["azure"].get("search_endpoint")
    search_key = os.getenv("AZURE_SEARCH_KEY") or config["azure"].get("search_key")
    search_index = os.getenv("AZURE_SEARCH_INDEX") or config["azure"].get("search_index")
    
    # Load AI service config - try GitHub models first, then Azure AI Inference
    github_token = os.getenv("GITHUB_TOKEN")
    api_key = os.getenv("AZURE_AI_MODEL_INFERENCE_API_KEY") or config['azure'].get('azure_ai_model_inference_api_key')
    endpoint = os.getenv("AZURE_AI_MODEL_INFERENCE_ENDPOINT") or config['azure'].get('azure_ai_model_inference_endpoint')
    ai_model_name = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME") or config['azure'].get('azure_ai_model_deployment_name', 'gpt-4o-mini')
    
    if not search_endpoint:
        logger.warning("Azure Cognitive Search configuration missing. FAQ plugin will not be available.")
        
    if not github_token:
        logger.warning("GITHUB_TOKEN not found. Agent will not be available.")
        return None, None, None
    
    try:
        # Initialize Semantic Kernel
        kernel = Kernel()
        
        # Configure the AI service using GitHub models
        logger.info(f"Configuring GitHub models with model: {ai_model_name}")
        client = AsyncOpenAI(
            api_key=github_token,
            base_url="https://models.inference.ai.azure.com/",
        )
        ai_service = OpenAIChatCompletion(
            ai_model_id=ai_model_name,
            async_client=client,
        )
        
        kernel.add_service(ai_service)
        
        # Initialize Azure Search client and plugin (optional)
        search_client = None
        if search_endpoint and search_key and search_index:
            search_client = SearchClient(
                endpoint=search_endpoint,
                index_name=search_index,
                credential=AzureKeyCredential(search_key)
            )
        
        FAQ_PLUGIN = VectorSearchPlugin(search_client)
        
        # Register the search_faq function with the kernel
        AGENT_KERNEL = kernel
        settings = PromptExecutionSettings(
            extension_data={
                "temperature": 0.1,
                "max_tokens": 2000
            }
        )
        settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
        
        # Create the agent and register the plugin
        agent = ChatCompletionAgent(
            kernel=kernel, 
            name="SupportAgent",
            instructions="You are a helpful assistant. Answer questions and help users with their requests.",
            execution_settings=settings
        )
        
        # Add plugin to kernel if available
        if FAQ_PLUGIN.search_client:
            kernel.add_plugin(FAQ_PLUGIN, plugin_name="VectorSearch")
        
        SUPPORT_AGENT = agent
        
        # Initialize the HistoryMemory instance
        HISTORY_MEMORY = HistoryMemory()
        
        logger.info("Agent, FAQ plugin, and HistoryMemory successfully initialized.")
        return kernel, FAQ_PLUGIN, agent
        
    except Exception as e:
        logger.error(f"Failed to initialize agent and plugins: {str(e)}", exc_info=True)
        return None, None, None

# Initialize on module load
initialize_agent_and_plugins()

async def get_response(messages: str, user_id: str = "default_user", discussion_id: str = "default_discussion") -> str:
    """
    Gets a response from the AI assistant using the conversation history.
    
    Args:
        messages: The user's message.
        user_id: The ID of the user.
        discussion_id: The ID of the discussion.
        
    Returns:
        The AI assistant's response as a string.
    """
    global SUPPORT_AGENT, HISTORY_MEMORY
    
    if not SUPPORT_AGENT:
        logger.error("SUPPORT_AGENT is not initialized")
        raise RuntimeError("AI assistant is not initialized")
    
    try:
        # Get or create a history thread for this user and discussion
        thread = HISTORY_MEMORY.get_or_create_history(user_id, discussion_id)
        
        # Add the user message to the thread
        from semantic_kernel.contents import ChatMessageContent, AuthorRole
        user_message = ChatMessageContent(role=AuthorRole.USER, content=messages)
        await thread.add_chat_message(user_message)
        
        # Prepare arguments with current timestamp
        arguments = KernelArguments(now=datetime.now().strftime("%Y-%m-%d %H:%M"))
        
        # Get the response from the agent using the thread
        response = None
        async for response_chunk in SUPPORT_AGENT.invoke(thread=thread, arguments=arguments):
            response = response_chunk
        
        if response and response.content:
            logger.info(f"Generated AI response with thread: {response.content}")
            
            # Update the history with the new thread
            if response.thread:
                HISTORY_MEMORY.update_history(user_id, discussion_id, response.thread)
                
            return response.content
        else:
            logger.error("The agent returned an empty response")
            return "Je suis désolé, je n'ai pas pu générer une réponse. Veuillez réessayer."
    
    except Exception as e:
        logger.exception(f"Error getting response from agent: {str(e)}")
        raise RuntimeError(f"Error getting response from AI assistant: {str(e)}")