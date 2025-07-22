# Azure Application Insights Monitoring for Chainlit Hotel Concierge

This document explains how to set up Azure Application Insights monitoring for the Chainlit hotel concierge application using OpenTelemetry.

## Overview

The application has been instrumented with OpenTelemetry to provide comprehensive monitoring including:

- **Distributed Tracing**: Track request flows through the multi-agent conversation system
- **Metrics**: Monitor performance indicators like response times, message counts, and active sessions
- **Custom Events**: Track specific business events like agent interactions and function calls
- **Error Monitoring**: Automatic collection of exceptions and errors

## Monitored Components

### Key Metrics Collected:
- `chainlit_messages_total`: Total number of user messages processed
- `agent_interactions_total`: Number of interactions between agents (FrontDesk, Concierge, Weather)
- `function_calls_total`: Number of function/tool calls (e.g., weather requests)
- `message_processing_duration_ms`: Time taken to process messages
- `active_sessions`: Number of concurrent user sessions

### Traced Operations:
- Chat session lifecycle (start/end)
- Message processing pipeline
- Agent group chat coordination
- Weather plugin function calls
- Individual agent responses

## Setup Instructions

### 1. Create Azure Application Insights Resource

1. Log into the [Azure Portal](https://portal.azure.com)
2. Create a new Application Insights resource:
   - Go to "Create a resource" > "Application Insights"
   - Choose your subscription and resource group
   - Set the resource name (e.g., `chainlit-hotel-concierge-insights`)
   - Select your preferred region
   - Create the resource

3. Copy the **Connection String** from the resource overview page

### 2. Install Required Packages

Install the additional OpenTelemetry packages for Azure Application Insights:

```bash
pip install opentelemetry-api opentelemetry-sdk azure-monitor-opentelemetry
```

### 3. Configure Environment Variables

Add your Application Insights connection string to your `.env` file:

```env
APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=your-key;IngestionEndpoint=https://your-region.in.applicationinsights.azure.com/;LiveEndpoint=https://your-region.livediagnostics.monitor.azure.com/"
```

### 4. Enable Azure Monitor (Optional Configuration)

The application automatically detects the connection string and configures Azure Monitor. To enable the full OpenTelemetry instrumentation, uncomment the relevant lines in `telemetry.py`:

1. Uncomment the OpenTelemetry imports at the top of the file
2. Uncomment the Azure Monitor configuration in the `setup_telemetry()` function

### 5. Test the Configuration

Run the Chainlit application and verify telemetry is being sent:

```bash
chainlit run app.py
```

Check the Application Insights resource in Azure Portal for incoming telemetry data.

## Viewing Telemetry Data

### In Azure Portal:

1. **Live Metrics**: Real-time monitoring of the application
   - Go to Application Insights > Live metrics
   - See active sessions, request rates, and response times in real-time

2. **Application Map**: Visual representation of application components
   - View the flow between different agents and dependencies

3. **Performance**: Analyze response times and identify bottlenecks
   - Look at operation duration trends
   - Identify slow message processing

4. **Failures**: Monitor errors and exceptions
   - Track failure rates across different operations
   - View detailed exception information

5. **Custom Queries**: Use KQL (Kusto Query Language) for detailed analysis

### Sample KQL Queries:

```kql
// Average message processing time
customMetrics
| where name == "message_processing_duration_ms"
| summarize avg(value) by bin(timestamp, 5m)

// Agent interaction patterns
customMetrics
| where name == "agent_interactions_total"
| extend agent_name = tostring(customDimensions.agent_name)
| summarize count() by agent_name

// Active sessions over time
customMetrics
| where name == "active_sessions"
| summarize max(value) by bin(timestamp, 1m)
```

## Development Mode

When the Azure connection string is not configured, the application uses console-based telemetry for development. You'll see telemetry output in the console logs:

```
INFO:root:🔍 TRACE START [timestamp] operation_name
INFO:root:📊 METRIC [timestamp] metric_name: value {attributes}
INFO:root:🔍 TRACE END [timestamp] operation_name - Duration: Xms - Status: OK
```

## Troubleshooting

### Common Issues:

1. **No data in Application Insights**:
   - Verify the connection string is correct
   - Check that the Azure Monitor packages are installed
   - Ensure the Application Insights resource is in the same region as your application

2. **Import errors**:
   - Install missing packages: `pip install azure-monitor-opentelemetry`
   - Verify Python version compatibility

3. **High telemetry volume**:
   - Configure sampling in the Azure Monitor configuration
   - Adjust metric collection intervals

### Support:

For issues specific to this implementation, check the application logs. For Azure Application Insights issues, refer to the [official documentation](https://docs.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview).

## Extending Monitoring

To add more custom metrics or traces:

1. Import telemetry functions: `from telemetry import get_tracer, get_custom_metrics`
2. Create spans for new operations: `with tracer.start_span("operation_name"):`
3. Record custom metrics: `custom_metrics['metric_name'](value, attributes)`

Example:
```python
# Add custom metric for conversation quality
custom_metrics['conversation_rating'](rating, {"user_satisfaction": "high"})

# Add custom tracing for new features
with tracer.start_span("custom_operation") as span:
    span.set_attribute("custom_attribute", value)
    # Your code here
```