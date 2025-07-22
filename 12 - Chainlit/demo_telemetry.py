#!/usr/bin/env python3
"""
Simulation script to demonstrate the telemetry output for the Chainlit hotel concierge application.
This shows what telemetry data would be collected during typical user interactions.
"""

import time
import logging
from telemetry import get_tracer, get_custom_metrics

# Configure logging to show telemetry output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def simulate_chat_session():
    """Simulate a complete chat session with telemetry."""
    print("\n🎯 Simulating Chainlit Hotel Concierge Chat Session with Telemetry")
    print("=" * 70)
    
    tracer = get_tracer()
    custom_metrics = get_custom_metrics()
    
    # Simulate chat session start
    with tracer.start_span("chat_session.start") as span:
        custom_metrics['active_sessions'](1)
        span.set_attribute("session_initialized", True)
        span.set_attribute("agents_count", 3)
        print("🏨 Welcome! Hotel concierge agents are ready to help you!")
        time.sleep(0.1)  # Simulate initialization time
    
    # Simulate user message processing
    user_messages = [
        "What's the weather like in Paris?",
        "Can you recommend some local activities in Paris?", 
        "Are there any hidden gems to visit?"
    ]
    
    for i, message in enumerate(user_messages, 1):
        print(f"\n👤 User Message {i}: {message}")
        
        start_time = time.time()
        with tracer.start_span("message.process") as span:
            span.set_attribute("message_length", len(message))
            span.set_attribute("user_id", "demo_user_123")
            
            custom_metrics['message_counter'](1, {"type": "user_message"})
            
            # Simulate group chat processing
            simulate_group_chat(message, tracer, custom_metrics)
            
            # Record processing time
            processing_time = (time.time() - start_time) * 1000
            custom_metrics['message_duration'](processing_time)
            span.set_attribute("processing_time_ms", processing_time)
        
        time.sleep(0.2)  # Brief pause between messages

    # Simulate session end
    with tracer.start_span("chat_session.end") as span:
        custom_metrics['active_sessions'](-1)
        span.set_attribute("session_ended", True)
        print("\n👋 Thank you for using our hotel concierge service!")

def simulate_group_chat(message, tracer, custom_metrics):
    """Simulate the multi-agent conversation flow."""
    with tracer.start_span("group_chat.handle") as span:
        span.set_attribute("message_content", message[:50])
        
        agents = ["WeatherConditionsAgent", "FrontDesk", "Concierge"]
        agent_responses = 0
        
        for agent_name in agents:
            # Simulate agent processing time
            time.sleep(0.05)
            
            response = ""
            if agent_name == "WeatherConditionsAgent" and "weather" in message.lower():
                simulate_weather_function_call(message, tracer, custom_metrics)
                response = "🌤️ WeatherConditionsAgent: The weather in Paris is 20°C and sunny."
            elif agent_name == "FrontDesk":
                response = f"🏨 {agent_name}: I recommend visiting the Marais district for authentic local experiences."
            elif agent_name == "Concierge":
                response = f"👨‍💼 {agent_name}: This recommendation is approved - great choice for non-touristy experiences!"
            else:
                response = f"🤖 {agent_name}: I'm analyzing your request..."
            
            # Track agent interaction
            custom_metrics['agent_interaction_counter'](1, {
                "agent_name": agent_name,
                "interaction_type": "response"
            })
            
            agent_responses += 1
            print(f"  {response}")
        
        span.set_attribute("agent_interactions_count", agent_responses)

def simulate_weather_function_call(message, tracer, custom_metrics):
    """Simulate weather plugin function call."""
    with tracer.start_span("weather_plugin.get_weather") as span:
        # Extract city from message (simplified)
        city = "Paris" if "paris" in message.lower() else "Unknown"
        span.set_attribute("city", city)
        
        custom_metrics['function_call_counter'](1, {
            "function": "get_weather", 
            "plugin": "weather"
        })
        
        result = f"The weather in {city} is 20°C and sunny."
        span.set_attribute("result_length", len(result))
        
        time.sleep(0.02)  # Simulate API call time

def show_final_metrics():
    """Display collected metrics summary."""
    print("\n📊 Final Telemetry Summary")
    print("=" * 40)
    
    meter = get_custom_metrics()
    if hasattr(meter, '__self__') and hasattr(meter['message_counter'].__self__, 'get_metrics'):
        metrics = meter['message_counter'].__self__.get_metrics()
        for name, value in metrics.items():
            print(f"  {name}: {value}")
    else:
        print("  (Metrics are being exported to Azure Application Insights)")

if __name__ == "__main__":
    print("🚀 Starting Chainlit Hotel Concierge Telemetry Demonstration")
    
    try:
        simulate_chat_session()
        show_final_metrics()
        
        print(f"\n✅ Simulation completed successfully!")
        print(f"💡 In production, this telemetry data would be sent to Azure Application Insights")
        print(f"📈 You could then create dashboards, alerts, and analytics based on this data")
        
    except Exception as e:
        print(f"❌ Error during simulation: {e}")
        import traceback
        traceback.print_exc()