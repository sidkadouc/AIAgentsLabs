import chainlit as cl
import os
from dotenv import load_dotenv
from agent import get_response

@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session."""
    load_dotenv()
    
    # Welcome message
    await cl.Message(
        content="Welcome to the Support Assistant! I'm here to help answer your questions using our knowledge base.",
        author="System"
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages."""
    try:
        # Get user and session information
        user_id = cl.user_session.get("user_id", "default_user")
        session_id = cl.user_session.get("session_id", cl.user_session.get("id", "default_session"))
        
        # Create a loading message
        loading_msg = cl.Message(content="Thinking...", author="Assistant")
        await loading_msg.send()
        
        # Get response from the agent
        response = await get_response(
            messages=message.content,
            user_id=user_id,
            discussion_id=session_id
        )
        
        # Update the loading message with the actual response
        loading_msg.content = response
        await loading_msg.update()
        
    except Exception as e:
        error_msg = f"Sorry, I encountered an error: {str(e)}"
        await cl.Message(content=error_msg, author="System").send()