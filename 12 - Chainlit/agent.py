import os
import logging
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.azure_ai_inference import AzureAIInferenceChatCompletion
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.functions import kernel_function, KernelArguments
from datetime import datetime
from vector_search_plugin import VectorSearchPlugin
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from config import config

logger = logging.getLogger(__name__)

# Global variables for agent and plugins
AGENT_KERNEL = None
FAQ_PLUGIN = None
SUPPORT_AGENT = None
HISTORY_MEMORY = None

# Import our HistoryMemory class
from history_memory import HistoryMemory


def initialize_agent_and_plugins():
    """Initialize the Semantic Kernel agent and plugins."""
    global AGENT_KERNEL, FAQ_PLUGIN, SUPPORT_AGENT, HISTORY_MEMORY
    
    # Load Azure Search config
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT") or config["azure"].get("search_endpoint")
    search_key = os.getenv("AZURE_SEARCH_KEY") or config["azure"].get("search_key")
    search_index = os.getenv("AZURE_SEARCH_INDEX") or config["azure"].get("search_index")
    
    # Load Azure AI Inference config
    endpoint = os.getenv("AZURE_AI_MODEL_INFERENCE_ENDPOINT") or config['azure']['azure_ai_model_inference_endpoint']
    api_key = os.getenv("AZURE_AI_MODEL_INFERENCE_API_KEY") or config['azure']['azure_ai_model_inference_api_key']
    ai_model_name = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME") or config['azure']['azure_ai_model_deployment_name']
    
    if not (search_endpoint and search_key and search_index):
        logger.warning("Azure Cognitive Search configuration missing. FAQ plugin will not be available.")
        return None, None, None
        
    if not (endpoint and api_key):
        logger.warning("Azure AI Inference configuration missing. Agent will not be available.")
        return None, None, None
    
    try:
        # Initialize Semantic Kernel
        kernel = Kernel()
        
        # Configure the Azure AI Inference service
        logger.info(f"Configuring Azure AI Inference with endpoint: {endpoint}, model: {ai_model_name}")
        azure_ai = AzureAIInferenceChatCompletion(
            ai_model_id=ai_model_name,
            api_key=api_key,
            endpoint=endpoint,
            service_id="azureoai"
        )
        kernel.add_service(azure_ai)
        
        # Initialize Azure Search client and plugin
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=search_index,
            credential=AzureKeyCredential(search_key)
        )
        FAQ_PLUGIN = VectorSearchPlugin(search_client)
        
        # Register the search_faq function with the kernel
        # kernel.add_function(search_faq)
        AGENT_KERNEL = kernel
        settings = PromptExecutionSettings(
            service_id="azureoai",
            extension_data={
                "temperature": 0.1,
                "max_tokens": 2000
            }
        )
        settings.function_choice_behavior = FunctionChoiceBehavior.Auto()        # Create the agent and register the plugin
        agent = ChatCompletionAgent(
            kernel=kernel, 
            name="SupportAgent",
            instructions="Tu es un assistant virtuel ",
            arguments=KernelArguments(settings=settings),
            plugins=[FAQ_PLUGIN]
        )
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
    Gets a response from the AI assistant using the conversation history with streaming.
    
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
        
        # Prepare arguments with current timestamp
        arguments = KernelArguments(now=datetime.now().strftime("%Y-%m-%d %H:%M"))
        
        # Get the streaming response from the agent using the thread
        response_content = ""
        response_thread = None
        
        async for response_chunk in SUPPORT_AGENT.invoke_stream(messages=messages, thread=thread, arguments=arguments):
            if response_chunk.content:
                response_content += response_chunk.content
            # Keep track of the thread from the last response chunk
            response_thread = response_chunk.thread
        
        if response_content:
            logger.info(f"Generated AI response with streaming: {response_content}")
            
            # Update the history with the new thread
            if response_thread:
                HISTORY_MEMORY.update_history(user_id, discussion_id, response_thread)
                
            return response_content
        else:
            logger.error("The agent returned an empty response")
            return "Je suis désolé, je n'ai pas pu générer une réponse. Veuillez réessayer."
    
    except Exception as e:
        logger.exception(f"Error getting response from agent: {str(e)}")
        raise RuntimeError(f"Error getting response from AI assistant: {str(e)}")

async def get_streaming_response(messages: str, user_id: str = "default_user", discussion_id: str = "default_discussion", history_memory=None):
    """
    Gets a streaming response from the AI assistant using the conversation history.
    This generator yields response chunks as they arrive for real-time streaming in Chainlit.
    
    Args:
        messages: The user's message.
        user_id: The ID of the user.
        discussion_id: The ID of the discussion.
        history_memory: Optional HistoryMemory instance. If None, uses the global HISTORY_MEMORY.
        
    Yields:
        Response chunks as they arrive from the AI assistant.
    """
    global SUPPORT_AGENT, HISTORY_MEMORY
    
    if not SUPPORT_AGENT:
        logger.error("SUPPORT_AGENT is not initialized")
        raise RuntimeError("AI assistant is not initialized")
    
    try:
        # Use provided history_memory or fall back to global HISTORY_MEMORY
        memory_instance = history_memory or HISTORY_MEMORY
        if not memory_instance:
            raise RuntimeError("No history memory instance available")
            
        # Get or create a history thread for this user and discussion
        thread = memory_instance.get_or_create_history(user_id, discussion_id)
        
        # Prepare arguments with current timestamp
        arguments = KernelArguments(now=datetime.now().strftime("%Y-%m-%d %H:%M"))
        
        # Stream the response from the agent using the thread
        response_thread = None
        
        async for response_chunk in SUPPORT_AGENT.invoke_stream(messages=messages, thread=thread, arguments=arguments):
            if response_chunk.content:
                # Yield each chunk as it arrives
                yield response_chunk.content
            # Keep track of the thread from the last response chunk
            response_thread = response_chunk.thread
        
        # Update the history with the final thread state
        if response_thread:
            memory_instance.update_history(user_id, discussion_id, response_thread)
            logger.info("Updated conversation history after streaming response")
    
    except Exception as e:
        logger.exception(f"Error getting streaming response from agent: {str(e)}")
        raise RuntimeError(f"Error getting streaming response from AI assistant: {str(e)}")