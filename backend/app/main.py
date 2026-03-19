"""Vintality AI Layer — FastAPI Application.

This is the API server that sits between the React frontend
and the Claude agent. It handles:
- Chat requests (sync and streaming)
- CORS for the React dev server
- Health checks
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.chat import router as chat_router
from app.routes.dashboard import router as dashboard_router

app = FastAPI(
    title="Vintality AI Layer",
    description="LLM-powered agronomic interpretation for vineyard management",
    version="0.1.0",
)

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(chat_router)
app.include_router(dashboard_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "vintality-ai"}
