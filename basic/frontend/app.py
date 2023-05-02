"""DemoStack Frontend - route request, block bad requests, etc"""
import threading
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Dict, Optional, TypedDict, Union
from time import sleep, time

from flask import Flask, request
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.metrics import (
    Counter,
    Histogram,
    ObservableGauge,
    Observation,
    get_meter,
    set_meter_provider,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import set_tracer_provider
from prometheus_client import start_http_server as start_prom_server
from pymongo import MongoClient

app = Flask(__name__)

# Keep all metrics for this module in one place.
# They will be initialized in configure_otel() at runtime
FrontendMetrics = TypedDict(
    "FrontendMetrics",
    {
        "health_count": Counter,
        "cart_count": ObservableGauge,
        "cart_value": ObservableGauge,
        "cart_scan_time": Histogram,
        "cart_scan_count": Counter,
    },
    total=False,  # Allow an empty dict to still be valid
)
METRICS: FrontendMetrics = {}

# Async store of cart count and total value.
# Only one thread will write this, but if we're concerned about
# read races, then we can wrap a semaphore or condition around this
CART_STATS: Dict[str, Union[int, float]] = {"count": 0, "value": 0.0}


class Error(Exception):
    """Base class for all custom exceptions in this app"""


class MongoDBConnectionError(Error):
    """Some problem connected to the DB."""


class CartValueChecker(threading.Thread):
    """Updates the cart metrics on a regular schedule."""

    # This is just a fun implementation of a random idea.
    ### ADR
    ## Goal: Be able to display the current total value of
    # all items in Carts but not checked-out, as well as
    # the average cart value.
    #
    ## Design: Every minute, do a full table-scan of the
    # CartsDB and store cart count and total value in
    # Gauge metrics. This is handled as a background
    # thread in the main serving job.
    #
    ## Scaling / alternatives considered:
    # For bigger data sets, this could be a map/reduce job
    # Or have a listener on "cart updated" messages / events
    # and calculate a rough running total that way.
    #
    # If the table scan overloads the frontend, or starts
    # taking longer than 60s to complete, the work should be
    # distributed using another mechanism.

    def __init__(
        self,
        group: None = None,
        target: Callable[..., object] | None = None,
        name: str | None = None,
        args: Iterable[Any] = ...,  # type: ignore[assignment]
        kwargs: Mapping[str, Any] | None = None,
        *,
        daemon: bool | None = None,
        period_s: float = 60.0,
    ) -> None:
        """Initializes loop schedule"""
        # This thread class has only two persistent attributes:
        # next_run (the system time of the next scheduled run)
        # mongodb (mongodb client)
        # Ensure the code runs immediately:
        self.next_run: float = time() - 1.0
        self.mongodb: Optional[MongoClient] = None
        self.period_s: float = period_s
        # Check our metrics have been initialized
        for metric_name in ["cart_count", "cart_value", "cart_scan_time"]:
            assert metric_name in METRICS
        super().__init__(group, target, name, args, kwargs, daemon=daemon)

    def _connect(self) -> MongoClient:
        """Connects to backend DB or raises an error."""
        if not self.mongodb:
            self.mongodb = MongoClient(host="carts-db.sock-shop", port=27017)
        return self.mongodb

    # Cart example:
    # {
    #   "_id": {
    #     "$oid": "64501f1b9411170007dff59b"
    #   },
    #   "_class": "works.weave.socks.cart.entities.Cart",
    #   "customerId": "64501f1b34fcc200017530ad",
    #   "items": [
    #     {
    #       "$ref": "item",
    #       "$id": {
    #         "$oid": "64501f0b9411170007dff59a"
    #       }
    #     }
    #   ]
    # }

    # Item example:
    # {
    #   "_id": {
    #     "$oid": "64501f0b9411170007dff59a"
    #   },
    #   "_class": "works.weave.socks.cart.entities.Item",
    #   "itemId": "510a0d7e-8e83-4193-b483-e27e09ddc34d",
    #   "quantity": 5,
    #   "unitPrice": 15
    # }

    def run(self) -> None:
        """Queries current cart values"""
        while True:
            while time() < self.next_run:
                sleep(1.0)
            now = time()
            METRICS["cart_scan_count"].add(1)
            self.next_run = now + self.period_s
            cart_count = 0
            total_value = 0.0
            carts = self._connect().data.cart
            items = self._connect().data.item
            for _ in carts.find():
                cart_count += 1
            # Assume items are deleted from the table when no longer needed
            # If this is a bad assumption, iterate through items in each cart.
            for item in items.find():
                total_value += item["quantity"] * float(item["unitPrice"])
            CART_STATS["count"] = cart_count
            CART_STATS["value"] = total_value
            scan_hist: Histogram = METRICS["cart_scan_time"]
            scan_hist.record(time() - now)


def configure_otel() -> None:
    """Registers metrics and default labels for OpenTelemetry."""
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

    METRICS["cart_value"] = meter.create_observable_gauge(
        "cart.value_total",
        unit="GBP",
        description="Value of the contents of all the current carts in the DB",
        callbacks=[lambda *_: [Observation(CART_STATS["value"])]],
    )
    METRICS["cart_count"] = meter.create_observable_gauge(
        "cart.count",
        unit="1",
        description="Number of carts in the DB",
        callbacks=[lambda *_: [Observation(CART_STATS["count"])]],
    )
    METRICS["cart_scan_count"] = meter.create_counter(
        "cart.scount_count", "1", "Number of cart scans started"
    )
    METRICS["cart_scan_time"] = meter.create_histogram(
        "cart.scan_time",
        unit="s",
        description="Time take to scan the carts-db tables",
    )


@app.route("/health")
def health_check() -> str:
    """Returns "ok" if healthy, undefined otherwise."""
    if counter := METRICS.get("health_count", None):
        counter.add(1)
    return "ok"


@app.route("/")
def server_request() -> str:
    """Handles all non-health-check requests for now."""
    print(request.args.get("param"))
    return "served"


def run():
    """Sets up otel and starts the server"""
    configure_otel()
    # Start *prometheus* server:
    start_prom_server(port=9000, addr="localhost")
    CartValueChecker().start()
    # Start main app
    app.run(port=8082)


if __name__ == "__main__":
    run()
