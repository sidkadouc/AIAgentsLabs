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
import time
import logging
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

# Import telemetry configuration
from telemetry import setup_telemetry, get_tracer, get_custom_metrics


# Initialize telemetry at module level
tracer, meter = setup_telemetry()
custom_metrics = get_custom_metrics()

request_settings = OpenAIChatPromptExecutionSettings(
    function_choice_behavior=FunctionChoiceBehavior.Auto(filters={"excluded_plugins": ["ChatBot"]})
)

# Example Native Plugin (Tool)
class WeatherPlugin:
    @kernel_function(name="get_weather", description="Gets the weather for a city")
    def get_weather(self, city: str) -> str:
        """Retrieves the weather for a given city."""
        # Add telemetry for function calls
        tracer = get_tracer()
        custom_metrics = get_custom_metrics()
        
        with tracer.start_as_current_span("weather_plugin.get_weather") as span:
            span.set_attribute("city", city)
            custom_metrics['function_call_counter'](1, {"function": "get_weather", "plugin": "weather"})
            
            if "paris" in city.lower():
                result = f"The weather in {city} is 20°C and sunny."
            elif "london" in city.lower():
                result = f"The weather in {city} is 15°C and cloudy."
            else:
                result = f"Sorry, I don't have the weather for {city}."
            
            span.set_attribute("result_length", len(result))
            logging.info(f"Weather request processed for city: {city}")
            return result

@cl.on_chat_start
async def on_chat_start():
    tracer = get_tracer()
    custom_metrics = get_custom_metrics()
    
    with tracer.start_span("chat_session.start") as span:
        load_dotenv()
        
        # Track new session
        custom_metrics['active_sessions'](1)
        
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
        # sk_filter = cl.SemanticKernelFilter(kernel=kernel)

        # Store everything in the session
        cl.user_session.set("kernel", kernel)
        cl.user_session.set("ai_service", ai_service)
        cl.user_session.set("chat_history", ChatHistory())
        cl.user_session.set("group_chat", group_chat)
        cl.user_session.set("front_desk_name", front_desk_name)
        cl.user_session.set("concierge_name", concierge_name)
        
        span.set_attribute("session_initialized", True)
        span.set_attribute("agents_count", 3)  # front_desk, concierge, weather
        logging.info("New chat session started with hotel concierge agents")
        
        # Welcome message
        await cl.Message(
            content="Welcome to the Hotel Concierge Service! I'll help you get travel recommendations from our agents. Ask about activities or places to visit in any city.",
            author="System"
        ).send()

@cl.on_message
async def on_message(message: cl.Message):
    tracer = get_tracer()
    custom_metrics = get_custom_metrics()
    
    start_time = time.time()
    
    with tracer.start_span("message.process") as span:
        span.set_attribute("message_length", len(message.content))
        span.set_attribute("user_id", cl.user_session.get("id", "unknown"))
        
        # Track message processing
        custom_metrics['message_counter'](1, {"type": "user_message"})
        
        kernel = cl.user_session.get("kernel")
        ai_service = cl.user_session.get("ai_service")
        chat_history = cl.user_session.get("chat_history")
        
        # Get the group chat setup
        group_chat = cl.user_session.get("group_chat")
        front_desk_name = cl.user_session.get("front_desk_name")
        concierge_name = cl.user_session.get("concierge_name")
        
        # Use group chat for recommendations
        await handle_group_chat(message, group_chat, front_desk_name, concierge_name)
        
        # Record processing time
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        custom_metrics['message_duration'](processing_time)
        span.set_attribute("processing_time_ms", processing_time)
        
        logging.info(f"Message processed in {processing_time:.2f}ms")


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
    tracer = get_tracer()
    custom_metrics = get_custom_metrics()
    
    with tracer.start_span("group_chat.handle") as span:
        span.set_attribute("message_content", message.content[:100])  # First 100 chars
        
        # Send user message with user's avatar
        await message.send()
        await group_chat.add_chat_message(ChatMessageContent(role=AuthorRole.USER, content=message.content))
        # Process the message through the group chat
        # result = await group_chat.send_async(message.content)
        
        # Track which agent messages we've already displayed
        displayed_messages = set()
        agent_interactions = 0
        
        # Display the conversation between agents
        async for content in group_chat.invoke():
            agent_interactions += 1
            
            # Skip user message and messages we've already displayed
            message_content = f"## Agent - {content.name or '*'}: \n '{content.content}'"
               
            # Add this message to displayed set
            displayed_messages.add(message_content)
            
            # Track agent interaction
            custom_metrics['agent_interaction_counter'](1, {
                "agent_name": content.name or "unknown",
                "interaction_type": "response"
            })
            
            # Determine the correct author name based on agent name
         
            
            # Create and send the agent message
            agent_msg = cl.Message(content=message_content, author=content.name )
            await agent_msg.send()
        
        span.set_attribute("agent_interactions_count", agent_interactions)
        span.set_attribute("displayed_messages_count", len(displayed_messages))
        
        logging.info(f"Group chat processed with {agent_interactions} agent interactions")


@cl.on_chat_end
async def on_chat_end():
    """Handle chat session end for telemetry cleanup."""
    tracer = get_tracer()
    custom_metrics = get_custom_metrics()
    
    with tracer.start_span("chat_session.end") as span:
        # Decrease active sessions count
        custom_metrics['active_sessions'](-1)
        
        span.set_attribute("session_ended", True)
        logging.info("Chat session ended")