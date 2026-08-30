"""Application-scoped HTTP client shared by caller-owned OpenAI adapters."""

from threading import Lock

import httpx
from fastapi import FastAPI


def configure_openai_http_client(application: FastAPI) -> None:
    """Install per-application construction state without creating a client."""
    application.state.openai_http_client_lock = Lock()
    application.state.openai_http_client_factory = httpx.AsyncClient


def get_openai_http_client(application: FastAPI) -> httpx.AsyncClient:
    client = getattr(application.state, "openai_http_client", None)
    if client is not None:
        return client

    lock = application.state.openai_http_client_lock
    with lock:
        client = getattr(application.state, "openai_http_client", None)
        if client is None:
            client = application.state.openai_http_client_factory()
            application.state.openai_http_client = client
        return client
