"""Agent orchestrator — the agentic tool-use loop.

This is the core of the Vintality AI layer. It:
1. Sends the user's message to Claude with tool definitions
2. If Claude responds with tool_use, executes those tools
3. Sends tool results back to Claude
4. Repeats until Claude responds with text (end_turn)
5. Supports both streaming and non-streaming modes

The loop has a safety limit (MAX_TOOL_ROUNDS) to prevent
infinite loops if Claude keeps calling tools.
"""

import json
import logging
from typing import AsyncGenerator

import anthropic

from app.config import settings
from app.agent.prompts import build_full_system_prompt
from app.agent.validation import validate_response, add_validation_disclaimer
from app.tools import execute_tool, TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5  # Safety limit on tool-use loops


def get_client() -> anthropic.Anthropic:
    """Create an Anthropic client instance."""
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def run_agent(user_message: str, conversation_history: list | None = None) -> dict:
    """Run the agent loop synchronously (non-streaming).

    This is the simplest version of the loop. Good for understanding
    the flow before adding streaming complexity.

    Args:
        user_message: The user's natural language question
        conversation_history: Previous messages for multi-turn context

    Returns:
        dict with 'response' (text), 'tool_calls' (list of tools used),
        and 'messages' (full conversation for follow-ups)
    """
    client = get_client()
    system_prompt = build_full_system_prompt()

    # Build message history
    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    tool_calls_made = []
    all_tool_results = []  # Collect for hallucination validation

    for round_num in range(MAX_TOOL_ROUNDS):
        logger.info(f"Agent round {round_num + 1}, sending {len(messages)} messages")

        # --- STEP 1: Send to Claude ---
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=2048,
            system=system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        logger.info(f"Stop reason: {response.stop_reason}")

        # --- STEP 2: Check if Claude is done ---
        if response.stop_reason == "end_turn":
            # Claude responded with text — we're done
            final_text = ""
            for block in response.content:
                if block.type == "text":
                    final_text += block.text

            # Add assistant response to history
            messages.append({"role": "assistant", "content": response.content})

            # --- VALIDATION: Check response against tool data ---
            validation = validate_response(final_text, all_tool_results)
            final_text = add_validation_disclaimer(final_text, validation)

            return {
                "response": final_text,
                "tool_calls": tool_calls_made,
                "messages": messages,
                "validation": {
                    "is_valid": validation.is_valid,
                    "confidence": validation.confidence,
                    "flagged_claims": validation.flagged_claims,
                },
            }

        # --- STEP 3: Claude wants to call tools ---
        if response.stop_reason == "tool_use":
            # Add Claude's response (with tool_use blocks) to history
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool call
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"Executing tool: {block.name}({block.input})")

                    try:
                        result = execute_tool(block.name, block.input)
                        tool_calls_made.append({
                            "tool": block.name,
                            "input": block.input,
                            "success": True,
                        })
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        result = json.dumps({"error": str(e)})
                        tool_calls_made.append({
                            "tool": block.name,
                            "input": block.input,
                            "success": False,
                            "error": str(e),
                        })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # --- STEP 4: Send tool results back to Claude ---
            messages.append({"role": "user", "content": tool_results})
            all_tool_results.extend(
                r["content"] for r in tool_results
            )

            # Loop continues — Claude will either call more tools or respond

    # Safety: if we hit MAX_TOOL_ROUNDS, return what we have
    logger.warning(f"Hit max tool rounds ({MAX_TOOL_ROUNDS})")
    return {
        "response": "I gathered data but reached my processing limit. Here's what I found so far based on the tools I called.",
        "tool_calls": tool_calls_made,
        "messages": messages,
    }


async def run_agent_streaming(
    user_message: str,
    conversation_history: list | None = None,
) -> AsyncGenerator[str, None]:
    """Run the agent loop with streaming output.

    Yields text chunks as Claude generates them. Tool calls are
    executed between streaming rounds (the user sees a brief pause
    while data is fetched, then streaming resumes).

    This is what the SSE endpoint uses for real-time chat feel.

    Yields:
        JSON-encoded event strings for the SSE endpoint:
        - {"type": "text", "content": "..."} — streamed text chunk
        - {"type": "tool_call", "tool": "...", "input": {...}} — tool being called
        - {"type": "tool_result", "tool": "...", "success": true} — tool completed
        - {"type": "done"} — agent finished
        - {"type": "error", "message": "..."} — something went wrong
    """
    client = get_client()
    system_prompt = build_full_system_prompt()

    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    for round_num in range(MAX_TOOL_ROUNDS):

        # Use streaming API
        with client.messages.stream(
            model=settings.claude_model,
            max_tokens=2048,
            system=system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        ) as stream:
            # Collect the full response while streaming text chunks
            collected_content = []
            current_tool_uses = []

            for event in stream:
                # Stream text chunks to the client immediately
                if hasattr(event, "type"):
                    if event.type == "content_block_start":
                        if event.content_block.type == "text":
                            pass  # Text block starting
                        elif event.content_block.type == "tool_use":
                            current_tool_uses.append({
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input_json": "",
                            })
                            yield json.dumps({
                                "type": "tool_call",
                                "tool": event.content_block.name,
                            })

                    elif event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            yield json.dumps({
                                "type": "text",
                                "content": event.delta.text,
                            })
                        elif hasattr(event.delta, "partial_json"):
                            if current_tool_uses:
                                current_tool_uses[-1]["input_json"] += event.delta.partial_json

            # Get the complete response
            final_response = stream.get_final_message()

        # Add assistant response to history
        messages.append({"role": "assistant", "content": final_response.content})

        # Check if done
        if final_response.stop_reason == "end_turn":
            yield json.dumps({"type": "done"})
            return

        # Execute tools
        if final_response.stop_reason == "tool_use":
            tool_results = []

            for block in final_response.content:
                if block.type == "tool_use":
                    try:
                        result = execute_tool(block.name, block.input)
                        yield json.dumps({
                            "type": "tool_result",
                            "tool": block.name,
                            "success": True,
                        })
                    except Exception as e:
                        result = json.dumps({"error": str(e)})
                        yield json.dumps({
                            "type": "tool_result",
                            "tool": block.name,
                            "success": False,
                            "error": str(e),
                        })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})

    yield json.dumps({"type": "error", "message": "Reached maximum reasoning depth"})
