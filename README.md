# AIAgentsLabs

This repository contains various AI agent implementations and labs for learning and experimentation.

## 12 - Chainlit Support Assistant

A Chainlit-based chat application with a simple support assistant. This version uses a mock AI agent that provides basic responses without requiring external AI services.

### Features

- Interactive chat interface using Chainlit
- Simple rule-based response system
- Conversation history management
- No external API dependencies required
- Session-based memory management

### Prerequisites

1. **Python 3.8+**
2. **Chainlit** - For the web interface

### Setup Instructions

#### 1. Install Dependencies

Navigate to the project directory and install required packages:

```bash
cd "12 - Chainlit"
pip install chainlit python-dotenv
```

#### 2. Running the Application

No configuration needed! Just run the application:

#### Method 1: Using Chainlit directly

```bash
cd "12 - Chainlit"
chainlit run app.py
```

#### Method 2: Using Python

```bash
cd "12 - Chainlit"
python -m chainlit run app.py
```

The application will start and be available at `http://localhost:8000`

### Usage

1. Open your browser and navigate to `http://localhost:8000`
2. Start typing your questions in the chat interface
3. The assistant will respond with simple rule-based answers
4. Try keywords like: "hello", "help", "weather", "thanks", "goodbye"

### Upgrading to Full AI Service

If you want to upgrade to use real AI services later, you can:

1. Get a GitHub Token for GitHub Models API
2. Or configure Azure OpenAI services
3. Update the agent.py to use semantic-kernel with real AI services

### Configuration

The application uses simple rule-based responses and doesn't require external configuration.

### Troubleshooting

**Common Issues:**

1. **"AI assistant is not initialized"**
   - This should not happen with the mock agent. Try restarting the application.

2. **Import errors**
   - Ensure chainlit is installed: `pip install chainlit python-dotenv`

3. **Port already in use**
   - Change the port: `chainlit run app.py --port 8001`

### Project Structure

```
12 - Chainlit/
├── app.py                    # Main Chainlit application
├── agent.py                  # AI agent implementation
├── config.py                 # Configuration settings
├── history_memory.py         # Conversation history management
├── vector_search_plugin.py   # Azure Search integration
└── .env                      # Environment variables
```