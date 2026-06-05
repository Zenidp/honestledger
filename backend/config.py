"""Central config: loads env vars and initialises the Vertex AI Gemini client."""

import os
import socket
from pathlib import Path

from dotenv import load_dotenv

# WSL fix: IPv6 connectivity to googleapis.com is broken — SSL handshake hangs
# and token-refresh keep-alive connections get RST by the peer.
# Three-layer patch so every outbound connection uses IPv4:
#   1. socket.getaddrinfo  — used by httpx/httpcore (Gemini SDK)
#   2. socket.create_connection — used directly by urllib3/requests (auth refresh)
#   3. urllib3 HAS_IPV6 flag — prevents urllib3 from queuing IPv6 candidates

_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only

_orig_create_connection = socket.create_connection
def _ipv4_create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    host, port = address
    addrs = _orig_getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    if addrs:
        host = addrs[0][4][0]
    return _orig_create_connection((host, port), timeout, source_address)
socket.create_connection = _ipv4_create_connection

try:
    import urllib3.util.connection as _u3conn
    _u3conn.HAS_IPV6 = False
    # Also patch urllib3's create_connection directly
    _orig_u3_create = _u3conn.create_connection
    def _u3_ipv4_create(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None, socket_options=None):
        host, port = address
        addrs = _orig_getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        if addrs:
            host = addrs[0][4][0]
        return _orig_u3_create((host, port), timeout, source_address, socket_options)
    _u3conn.create_connection = _u3_ipv4_create
except Exception:
    pass

# Load .env from project root (works whether we run from root or backend/)
load_dotenv(Path(__file__).parent.parent / ".env")

GOOGLE_CLOUD_PROJECT: str = os.environ["GOOGLE_CLOUD_PROJECT"]
GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

PHOENIX_API_KEY: str = os.environ["PHOENIX_API_KEY"]
PHOENIX_COLLECTOR_ENDPOINT: str = os.environ["PHOENIX_COLLECTOR_ENDPOINT"]


_gemini_client = None

def get_gemini_client():
    """Return a shared Vertex AI Gemini client (singleton).

    Creating a client per call forces a new credential + token refresh on every request.
    A singleton means the token is obtained once and refreshed only when it actually expires
    (~1 hour), not on every call — eliminates the flaky token-refresh errors at scale.
    """
    global _gemini_client
    if _gemini_client is None:
        import google.genai as genai
        from google.genai import types
        _gemini_client = genai.Client(
            vertexai=True,
            project=GOOGLE_CLOUD_PROJECT,
            location=GOOGLE_CLOUD_LOCATION,
            http_options=types.HttpOptions(timeout=180_000),  # SDK uses ms; 180_000 = 180s
        )
    return _gemini_client

