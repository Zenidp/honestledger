"""Initialise Arize Phoenix tracing via OTEL + OpenInference auto-instrumentation."""

import os
import logging

logger = logging.getLogger(__name__)


def setup_phoenix_tracing() -> None:
    """Register Phoenix OTEL tracer with BatchSpanProcessor (non-blocking).

    Uses BatchSpanProcessor so trace export never blocks Gemini calls.
    Fails gracefully if Phoenix is unreachable — app still works without tracing.
    """
    try:
        from phoenix.otel import register
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        api_key = os.environ["PHOENIX_API_KEY"]
        endpoint = os.environ["PHOENIX_COLLECTOR_ENDPOINT"].rstrip("/")
        traces_endpoint = f"{endpoint}/v1/traces"

        # Register with auto_instrument but suppress the default SimpleSpanProcessor
        # by using batch=True if supported, otherwise configure manually
        try:
            # Newer arize-phoenix-otel supports batch kwarg
            tracer_provider = register(
                project_name="honestledger",
                endpoint=traces_endpoint,
                api_key=api_key,
                auto_instrument=True,
                batch=True,
            )
        except TypeError:
            # Older version — register normally then swap processor
            tracer_provider = register(
                project_name="honestledger",
                endpoint=traces_endpoint,
                api_key=api_key,
                auto_instrument=True,
            )
            # Replace SimpleSpanProcessor with BatchSpanProcessor
            exporter = OTLPSpanExporter(
                endpoint=traces_endpoint,
                headers={"authorization": f"Bearer {api_key}"},
            )
            tracer_provider.add_span_processor(
                BatchSpanProcessor(
                    exporter,
                    max_export_batch_size=10,
                    schedule_delay_millis=5000,   # export every 5s max
                    export_timeout_millis=8000,   # 8s timeout per batch
                )
            )

        print("      Phoenix tracing registered (batch mode).")
        return tracer_provider

    except Exception as e:
        logger.warning(f"Phoenix tracing unavailable: {e} — continuing without tracing.")
        return None
