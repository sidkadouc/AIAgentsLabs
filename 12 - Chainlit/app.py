import chainlit as cl
import os
from dotenv import load_dotenv
from agent import SUPPORT_AGENT, AGENT_KERNEL, initialize_agent_and_plugins, get_streaming_response
from history_memory import HistoryMemory

# We'll create a simple ChatHistory class since we need it for Chainlit integration
class ChatHistory:
    def __init__(self):
        self.messages = []
    
    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})
    
    def add_assistant_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content})

@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session."""
    load_dotenv()
    
    # Initialize agent and plugins if not already done
    if not SUPPORT_AGENT or not AGENT_KERNEL:
        initialize_agent_and_plugins()
    
    # Initialize chat history and memory
    chat_history = ChatHistory()
    history_memory = HistoryMemory()
    
    # Store in user session
    cl.user_session.set("chat_history", chat_history)
    cl.user_session.set("history_memory", history_memory)
    cl.user_session.set("user_id", "default_user")
    cl.user_session.set("session_id", cl.user_session.get("id", "default_session"))
    
    # Welcome message
    await cl.Message(
        content="Welcome to the Support Assistant! I'm here to help answer your questions using our knowledge base.",
        author="System"
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages with streaming response."""
    try:
        # Get session data
        chat_history = cl.user_session.get("chat_history")
        history_memory = cl.user_session.get("history_memory")
        user_id = cl.user_session.get("user_id", "default_user")
        session_id = cl.user_session.get("session_id", "default_session")
        
        if not SUPPORT_AGENT:
            await cl.Message(content="Sorry, the AI assistant is not available.", author="System").send()
            return
        
        # Add user message to history
        chat_history.add_user_message(message.content)
        
        # Create a Chainlit message for the response stream
        answer = cl.Message(content="")
        full_response = ""
        
        # Stream the response using the agent's get_streaming_response method
        try:
            async for response_chunk in get_streaming_response(
                messages=message.content, 
                user_id=user_id, 
                discussion_id=session_id,
                history_memory=history_memory
            ):
                # Ensure response_chunk is a string
                if response_chunk:
                    try:
                        chunk_str = str(response_chunk) if not isinstance(response_chunk, str) else response_chunk
                        await answer.stream_token(chunk_str)
                        full_response += chunk_str
                    except Exception as chunk_error:
                        print(f"Error processing chunk: {chunk_error}, chunk type: {type(response_chunk)}")
                        # Try alternative extraction methods
                        chunk_str = str(response_chunk)
                        await answer.stream_token(chunk_str)
                        full_response += chunk_str
        except Exception as stream_error:
            print(f"Streaming error: {stream_error}")
            raise
        
        # Add the full assistant response to chat history
        chat_history.add_assistant_message(full_response)
        
        # Send the final message
        await answer.send()
        
    except Exception as e:
        error_msg = f"Sorry, I encountered an error: {str(e)}"
        await cl.Message(content=error_msg, author="System").send()