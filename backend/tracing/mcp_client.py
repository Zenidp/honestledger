"""Phoenix trace client.

Two modes:
  1. REST  — programmatic, used by the automated judge loop.
  2. MCP subprocess — demonstrates meaningful MCP use for the demo.
"""

import json
import os
import subprocess
import httpx
from typing import Any


# ── REST client (primary, used in automated loop) ──────────────────────────

class PhoenixRestClient:
    """Query Phoenix Cloud via REST API."""

    def __init__(self):
        base = os.environ["PHOENIX_COLLECTOR_ENDPOINT"].rstrip("/")
        # base is like https://app.phoenix.arize.com/s/duhaperbangga
        self.base_url = base
        self.api_key = os.environ["PHOENIX_API_KEY"]
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def get_spans(self, project_name: str = "honestledger", limit: int = 100) -> list[dict]:
        """Fetch recent LLM spans for a project via Phoenix REST API."""
        # Try POST /v1/spans/query first (Phoenix Cloud format)
        for url, method, kwargs in [
            (f"{self.base_url}/v1/spans/query", "POST",
             {"json": {"project_name": project_name, "limit": limit}}),
            (f"{self.base_url}/v1/spans", "GET",
             {"params": {"project_name": project_name, "limit": limit}}),
            # Try without space prefix
            ("https://app.phoenix.arize.com/v1/spans", "GET",
             {"params": {"project_name": project_name, "limit": limit}}),
        ]:
            try:
                resp = httpx.request(method, url, headers=self.headers, timeout=15, **kwargs)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("data", data) if isinstance(data, dict) else data
            except Exception:
                continue
        raise RuntimeError("Could not fetch spans from Phoenix (tried multiple endpoints)")

    def get_span_summary(self, project_name: str = "honestledger", limit: int = 50) -> str:
        """Return a human-readable summary of recent spans for the judge."""
        spans = self.get_spans(project_name, limit)
        if not spans:
            return "No spans found."

        lines = [f"Retrieved {len(spans)} spans from Phoenix project '{project_name}':\n"]
        for span in spans[:limit]:
            attrs = span.get("attributes", {}) or {}
            name = span.get("name", "?")
            status = span.get("status", {})
            status_code = status.get("statusCode", "?") if isinstance(status, dict) else str(status)

            # Extract input/output from OpenInference attributes
            llm_input = attrs.get("llm.input_messages", attrs.get("input.value", ""))
            llm_output = attrs.get("llm.output_messages", attrs.get("output.value", ""))

            lines.append(f"  [{name}] status={status_code}")
            if llm_input:
                preview = str(llm_input)[:120].replace("\n", " ")
                lines.append(f"    input:  {preview}")
            if llm_output:
                preview = str(llm_output)[:120].replace("\n", " ")
                lines.append(f"    output: {preview}")

        return "\n".join(lines)


# ── MCP subprocess client (meaningful MCP use for demo) ────────────────────

class PhoenixMCPClient:
    """Call Phoenix MCP server via npx subprocess (JSON-RPC over stdio).

    Usage:
        client = PhoenixMCPClient()
        result = client.call_tool("list_projects")
        result = client.call_tool("get_spans", {"project_name": "honestledger", "limit": 10})
    """

    def __init__(self):
        self.api_key = os.environ["PHOENIX_API_KEY"]
        base = os.environ["PHOENIX_COLLECTOR_ENDPOINT"].rstrip("/")
        # Extract the base host for the MCP server
        # e.g. https://app.phoenix.arize.com/s/duhaperbangga → https://app.phoenix.arize.com
        self.phoenix_base = base.split("/s/")[0] if "/s/" in base else base

    def call_tool(self, tool_name: str, arguments: dict = None) -> Any:
        """Invoke a Phoenix MCP tool and return the result."""
        if arguments is None:
            arguments = {}

        # Initialize request (MCP handshake)
        init_request = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "honestledger", "version": "0.1.0"},
            },
        }
        tool_request = {
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        env = {
            **os.environ,
            "PHOENIX_API_KEY": self.api_key,
            "PHOENIX_BASE_URL": self.phoenix_base,
        }

        proc = subprocess.Popen(
            ["npx", "-y", "@arizeai/phoenix-mcp@latest", "--phoenix-base-url", self.phoenix_base],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=env,
        )

        try:
            # Send initialize then tool call, separated by newlines
            stdin_data = json.dumps(init_request) + "\n" + json.dumps(tool_request) + "\n"
            stdout, stderr = proc.communicate(input=stdin_data, timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            raise RuntimeError("Phoenix MCP server timed out")

        # Parse responses (one JSON object per line)
        results = []
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        # Return the result of the tool call (second response)
        for r in results:
            if r.get("id") == 2:
                if "error" in r:
                    raise RuntimeError(f"MCP error: {r['error']}")
                return r.get("result", {})

        return {"raw_output": stdout[:500], "stderr": stderr[:200]}


def get_phoenix_client() -> PhoenixRestClient:
    """Return the REST client (used in automated loop)."""
    return PhoenixRestClient()
