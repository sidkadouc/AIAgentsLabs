# Chainlit Support Agent Docker Setup

This directory contains Docker configuration for the Chainlit-based support agent application.

## Prerequisites

- Docker and Docker Compose installed on your system
- Azure AI Inference endpoint and API key
- Azure Search service configuration (optional for FAQ functionality)

## Quick Start

1. **Copy the environment template:**
   ```bash
   cp .env.template .env
   ```

2. **Edit the `.env` file with your Azure credentials:**
   ```bash
   # Edit .env file with your actual values
   AZURE_AI_MODEL_INFERENCE_ENDPOINT=your_azure_ai_inference_endpoint
   AZURE_AI_MODEL_INFERENCE_API_KEY=your_azure_ai_inference_api_key
   AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
   AZURE_SEARCH_ENDPOINT=your_azure_search_endpoint
   AZURE_SEARCH_KEY=your_azure_search_key
   AZURE_SEARCH_INDEX=your_azure_search_index
   ```

3. **Run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   Open your browser and go to `http://localhost:8000`

## Docker Commands

### Build the Docker image:
```bash
docker build -t chainlit-support-agent .
```

### Run the container:
```bash
docker run -p 8000:8000 --env-file .env chainlit-support-agent
```

### Run with Docker Compose:
```bash
# Run in foreground
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## Docker Image Optimizations

The Dockerfile includes several optimizations:

1. **Multi-stage builds** - Uses Python 3.11 slim for smaller image size
2. **Layer caching** - Requirements are installed before copying source code
3. **Security** - Runs as non-root user
4. **Health checks** - Built-in health monitoring
5. **Environment variables** - Configurable via environment variables

## Production Deployment

For production deployment, consider:

1. **Environment Variables**: Use proper secrets management instead of `.env` files
2. **Resource Limits**: Configure appropriate CPU and memory limits
3. **Monitoring**: Set up proper logging and monitoring
4. **Load Balancing**: Use a reverse proxy like Nginx for multiple instances
5. **SSL/TLS**: Configure HTTPS termination

## Troubleshooting

### Common Issues:

1. **Port already in use**: Change the port in `docker-compose.yml` or stop other services using port 8000
2. **Environment variables not loaded**: Make sure your `.env` file is properly formatted
3. **Azure credentials invalid**: Verify your Azure AI Inference and Search credentials

### Debugging:

```bash
# Check container logs
docker-compose logs chainlit-app

# Execute commands in running container
docker-compose exec chainlit-app bash

# Check container status
docker-compose ps
```

## File Structure

```
.
├── Dockerfile              # Docker image configuration
├── docker-compose.yml      # Docker Compose configuration
├── .dockerignore           # Files to exclude from Docker build
├── .env.template           # Environment variables template
├── requirements.txt        # Python dependencies
├── app.py                  # Main Chainlit application
├── agent.py                # AI agent implementation
├── config.py               # Configuration settings
├── history_memory.py       # Memory management
└── vector_search_plugin.py # Vector search functionality
```
