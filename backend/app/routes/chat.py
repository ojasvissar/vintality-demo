"""Chat API routes.

Two endpoints:
1. POST /api/chat — synchronous (for testing, returns full response)
2. POST /api/chat/stream — SSE streaming (for the React frontend)

Both accept a message and optional conversation history,
run the agent loop, and return Claude's grounded response.
"""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.agent import run_agent, run_agent_streaming

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    """Request body for chat endpoints."""
    message: str
    conversation_history: list | None = None


class ChatResponse(BaseModel):
    """Response body for synchronous chat."""
    response: str
    tool_calls: list
    messages: list


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Synchronous chat endpoint — returns full response at once.

    Good for testing and debugging. In production, use /chat/stream.
    """
    try:
        result = run_agent(
            user_message=request.message,
            conversation_history=request.conversation_history,
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE streaming chat endpoint — streams response token by token.

    The frontend opens an SSE connection and receives events:
    - event: text → partial response text
    - event: tool_call → Claude is calling a tool
    - event: tool_result → tool execution completed
    - event: done → response complete

    This gives the real-time chat feel that farm supervisors expect.
    """

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            async for chunk in run_agent_streaming(
                user_message=request.message,
                conversation_history=request.conversation_history,
            ):
                data = json.loads(chunk)
                yield {
                    "event": data["type"],
                    "data": chunk,
                }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"type": "error", "message": str(e)}),
            }

    return EventSourceResponse(event_generator())
