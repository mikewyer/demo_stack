"""DemoStack Frontend - route request, block bad requests, etc"""
from re import M
from typing import Dict
from flask import Flask, request

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.trace import get_tracer_provider, set_tracer_provider

from opentelemetry.metrics import set_meter_provider, get_meter, Instrument
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    ConsoleMetricExporter,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from prometheus_client import start_http_server


app = Flask(__name__)

METRICS: Dict[str, Instrument] = {}


def configure_otel() -> None:
    if METRICS:
        return
    FlaskInstrumentor().instrument_app(app, excluded_urls="/health")
    # Otel setup
    # Hard-coded for now, but this would come from the args/environment
    resource = Resource(attributes={SERVICE_NAME: "demostack-frontend"})
    console_metrics = PeriodicExportingMetricReader(ConsoleMetricExporter())
    prom_metrics = PrometheusMetricReader()
    # Start prometheus client
    set_meter_provider(
        MeterProvider(resource=resource, metric_readers=[console_metrics, prom_metrics])
    )
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    set_tracer_provider(tracer_provider)

    meter = get_meter(__name__)
    METRICS["health_count"] = meter.create_counter(
        "health.counter", unit="1", description="Counts the number of health checks"
    )


@app.route("/health")
def health_check():
    """Returns "ok" if healthy, undefined otherwise."""
    if counter := METRICS.get("health_count", None):
        counter.add(1)
    return "ok"


@app.route("/")
def server_request():
    """Handles all non-health-check requests for now."""
    print(request.args.get("param"))
    return "served"


def run():
    """Sets up otel and starts the server"""
    configure_otel()
    start_http_server(port=9000, addr="localhost")
    app.run(port=8082)


if __name__ == "__main__":
    run()
