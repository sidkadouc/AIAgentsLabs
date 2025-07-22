"""
Basic telemetry/monitoring module for the Chainlit application.
This module provides manual telemetry collection that can be extended with OpenTelemetry and Azure Application Insights.

For production use with Azure Application Insights:
1. Install: pip install opentelemetry-api opentelemetry-sdk azure-monitor-opentelemetry
2. Set APPLICATIONINSIGHTS_CONNECTION_STRING environment variable
3. Uncomment the Azure Monitor configuration in this file
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, Any

# Uncomment these imports when OpenTelemetry packages are installed:
# from opentelemetry import trace, metrics
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.metrics import MeterProvider
# from opentelemetry.sdk.resources import Resource
# from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
# from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter

# Check for Azure Monitor availability
AZURE_MONITOR_AVAILABLE = False
try:
    # Uncomment when azure-monitor-opentelemetry is installed:
    # from azure.monitor.opentelemetry import configure_azure_monitor
    # AZURE_MONITOR_AVAILABLE = True
    pass
except ImportError:
    logging.info("Azure Monitor OpenTelemetry not available. Install 'azure-monitor-opentelemetry' for production use.")


class BasicTelemetry:
    """Basic telemetry implementation for development and demonstration."""
    
    def __init__(self):
        self.metrics = {
            'message_count': 0,
            'agent_interactions': 0,
            'function_calls': 0,
            'active_sessions': 0,
            'total_processing_time': 0.0
        }
        self.traces = []
        
    def start_span(self, name: str):
        """Start a basic span for tracing."""
        return BasicSpan(name, self)
    
    def record_metric(self, name: str, value: float, attributes: Dict[str, Any] = None):
        """Record a metric value."""
        timestamp = datetime.now().isoformat()
        if name in self.metrics:
            if 'counter' in name or 'total' in name:
                self.metrics[name] += value
            else:
                self.metrics[name] = value
                
        logging.info(f"📊 METRIC [{timestamp}] {name}: {value} {attributes or {}}")
    
    def get_metrics(self):
        """Get current metrics."""
        return self.metrics.copy()


class BasicSpan:
    """Basic span implementation for tracing."""
    
    def __init__(self, name: str, telemetry: BasicTelemetry):
        self.name = name
        self.telemetry = telemetry
        self.start_time = time.time()
        self.attributes = {}
        self.active = False
        
    def __enter__(self):
        self.active = True
        timestamp = datetime.now().isoformat()
        logging.info(f"🔍 TRACE START [{timestamp}] {self.name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.active = False
        end_time = time.time()
        duration = (end_time - self.start_time) * 1000  # Convert to milliseconds
        timestamp = datetime.now().isoformat()
        
        status = "ERROR" if exc_type else "OK"
        logging.info(f"🔍 TRACE END [{timestamp}] {self.name} - Duration: {duration:.2f}ms - Status: {status} - Attributes: {self.attributes}")
        
        self.telemetry.traces.append({
            'name': self.name,
            'start_time': self.start_time,
            'end_time': end_time,
            'duration_ms': duration,
            'attributes': self.attributes.copy(),
            'status': status
        })
        
    def set_attribute(self, key: str, value: Any):
        """Set an attribute on the span."""
        self.attributes[key] = value


def setup_telemetry():
    """Initialize telemetry system."""
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    if connection_string and AZURE_MONITOR_AVAILABLE:
        # TODO: Uncomment when OpenTelemetry packages are installed
        # try:
        #     configure_azure_monitor(connection_string=connection_string)
        #     logging.info("✅ OpenTelemetry configured with Azure Application Insights")
        #     tracer = trace.get_tracer(__name__)
        #     meter = metrics.get_meter(__name__)
        #     return tracer, meter
        # except Exception as e:
        #     logging.warning(f"⚠️  Failed to configure Azure Monitor: {e}. Using basic telemetry.")
        pass
    
    if not connection_string:
        logging.info("ℹ️  APPLICATIONINSIGHTS_CONNECTION_STRING not found. Using basic telemetry for development.")
    
    # Return basic telemetry implementation
    basic_telemetry = BasicTelemetry()
    return basic_telemetry, basic_telemetry


def create_custom_metrics(meter):
    """Create custom metrics (basic implementation)."""
    if hasattr(meter, 'record_metric'):
        # Using basic telemetry
        return {
            'message_counter': lambda value, attrs=None: meter.record_metric('message_count', value, attrs),
            'agent_interaction_counter': lambda value, attrs=None: meter.record_metric('agent_interactions', value, attrs),
            'function_call_counter': lambda value, attrs=None: meter.record_metric('function_calls', value, attrs),
            'message_duration': lambda value, attrs=None: meter.record_metric('total_processing_time', value, attrs),
            'active_sessions': lambda value, attrs=None: meter.record_metric('active_sessions', value, attrs)
        }
    else:
        # TODO: Implement with real OpenTelemetry metrics when available
        return {}


# Global variables to store telemetry objects
_tracer = None
_meter = None
_custom_metrics = None


def get_tracer():
    """Get the configured tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer, _ = setup_telemetry()
    return _tracer


def get_meter():
    """Get the configured meter instance.""" 
    global _meter
    if _meter is None:
        _, _meter = setup_telemetry()
    return _meter


def get_custom_metrics():
    """Get the custom metrics instances."""
    global _custom_metrics
    if _custom_metrics is None:
        meter = get_meter()
        _custom_metrics = create_custom_metrics(meter)
    return _custom_metrics