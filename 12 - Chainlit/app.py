import chainlit as cl
import semantic_kernel as sk
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.functions import kernel_function
from semantic_kernel.contents import ChatHistory

from typing import Annotated
from openai import AsyncOpenAI

import os
from dotenv import load_dotenv


from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.functions import kernel_function

from semantic_kernel.agents import ChatCompletionAgent, AgentGroupChat
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)
from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.contents import AuthorRole, ChatMessageContent
from semantic_kernel.functions import KernelFunctionFromPrompt
from group import create_hotel_concierge_group_chat



request_settings = OpenAIChatPromptExecutionSettings(
    function_choice_behavior=FunctionChoiceBehavior.Auto(filters={"excluded_plugins": ["ChatBot"]})
)

# Example Native Plugin (Tool)
class WeatherPlugin:
    @kernel_function(name="get_weather", description="Gets the weather for a city")
    def get_weather(self, city: str) -> str:
        """Retrieves the weather for a given city."""
        if "paris" in city.lower():
            return f"The weather in {city} is 20°C and sunny."
        elif "london" in city.lower():
            return f"The weather in {city} is 15°C and cloudy."
        else:
            return f"Sorry, I don't have the weather for {city}."

@cl.on_chat_start
async def on_chat_start():

    load_dotenv()
    # Setup Semantic Kernel
    kernel = sk.Kernel()
    client = AsyncOpenAI(
    api_key=os.environ.get("GITHUB_TOKEN"), 
    base_url="https://models.inference.ai.azure.com/",
    )   

    # Create an AI Service that will be used by the `ChatCompletionAgent`
    chat_completion_service = OpenAIChatCompletion(
        ai_model_id="gpt-4o-mini",
        async_client=client,
    )
    # Add your AI service (e.g., OpenAI)
    # Make sure OPENAI_API_KEY and OPENAI_ORG_ID are set in your environment
    ai_service = chat_completion_service
    kernel.add_service(ai_service)

    # Import the WeatherPlugin
    kernel.add_plugin(WeatherPlugin(), plugin_name="Weather")
    
    # Set up the agent group chat
    group_chat, front_desk_name, concierge_name = create_hotel_concierge_group_chat(kernel)
    
    # Instantiate and add the Chainlit filter to the kernel
    # This will automatically capture function calls as Steps
    sk_filter = cl.SemanticKernelFilter(kernel=kernel)

    # Store everything in the session
    cl.user_session.set("kernel", kernel)
    cl.user_session.set("ai_service", ai_service)
    cl.user_session.set("chat_history", ChatHistory())
    cl.user_session.set("group_chat", group_chat)
    cl.user_session.set("front_desk_name", front_desk_name)
    cl.user_session.set("concierge_name", concierge_name)
    
    
    # Welcome message
    await cl.Message(
        content="Welcome to the Hotel Concierge Service! I'll help you get travel recommendations from our agents. Ask about activities or places to visit in any city.",
        author="System"
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    kernel = cl.user_session.get("kernel")
    ai_service = cl.user_session.get("ai_service")
    chat_history = cl.user_session.get("chat_history")
    
    # Get the group chat setup
    group_chat = cl.user_session.get("group_chat")
    front_desk_name = cl.user_session.get("front_desk_name")
    concierge_name = cl.user_session.get("concierge_name")
    
    # Use group chat for recommendations
    await handle_group_chat(message, group_chat, front_desk_name, concierge_name)


async def handle_regular_chat(message: cl.Message, kernel: sk.Kernel, ai_service, chat_history: ChatHistory):
    # Add user message to history
    chat_history.add_user_message(message.content)

    # Create a Chainlit message for the response stream
    answer = cl.Message(content="")

    async for msg in ai_service.get_streaming_chat_message_content(
        chat_history=chat_history,
        user_input=message.content,
        settings=request_settings,
        kernel=kernel,
    ):
        if msg.content:
            await answer.stream_token(msg.content)

    # Add the full assistant response to history
    chat_history.add_assistant_message(answer.content)

    # Send the final message
    await answer.send()

async def handle_group_chat(message: cl.Message, group_chat, front_desk_name: str, concierge_name: str):
    # Send user message with user's avatar
    await message.send()
    await group_chat.add_chat_message(ChatMessageContent(role=AuthorRole.USER, content=message.content))
    # Process the message through the group chat
    # result = await group_chat.send_async(message.content)
    
    # Track which agent messages we've already displayed
    displayed_messages = set()
    
    # Display the conversation between agents
    async for content in group_chat.invoke():
        # Skip user message and messages we've already displayed
        message = content.content
           
        # Add this message to displayed set
        displayed_messages.add(message)
        
        # Determine the correct author name based on agent name
     
        
        # Create and send the agent message
        agent_msg = cl.Message(content=message, author=content.name )
        await agent_msg.send()