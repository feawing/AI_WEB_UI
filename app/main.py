import asyncio
# import base64
import json
import os
from pathlib import Path
# from typing import AsyncIterable

# from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
# from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from jarvis.agent import root_agent

#
# ADK Configuration
#

# load_dotenv()

APP_NAME = "ADK webUI"
session_service = InMemorySessionService()


# The following functions were used for the 'live' streaming mode.
# They are kept here for future reference on how to implement a
# real-time, bidirectional, streaming communication with an agent.
"""
def start_agent_session(session_id):
    \"\"\"Starts an agent session for live streaming.\"\"\"

    # Create a Session
    session = session_service.create_session(
        app_name=APP_NAME,
        user_id=session_id,
        session_id=session_id,
    )

    # Create a Runner
    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
    )

    # Set response modality
    modality = "TEXT"

    # Create run config with basic settings
    config = {
        "response_modalities": [modality],
        "streaming_mode": StreamingMode.NONE,
    }

    # Add output_audio_transcription when audio is enabled to get both audio and text
    run_config = RunConfig(**config)

    # Create a LiveRequestQueue for this session
    live_request_queue = LiveRequestQueue()

    # Start agent session
    live_events = runner.run_live(
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )
    return live_events, live_request_queue


async def agent_to_client_messaging(
    websocket: WebSocket, live_events: AsyncIterable[Event | None]
):
    \"\"\"Agent to client communication for live streaming.\"\"\"
    print(f"INFO: Agent-to-client messaging task started for {websocket.client}.")
    while True:
        async for event in live_events:
            if event is None:
                continue

            print(f"INFO: Received event from agent: {event.type}")

            # If the turn complete or interrupted, send it
            if event.turn_complete or event.interrupted:
                message = {
                    "turn_complete": event.turn_complete,
                    "interrupted": event.interrupted,
                }
                await websocket.send_text(json.dumps(message))
                print(f"INFO: [AGENT TO CLIENT] Sent turn status: {message}")
                continue

            # Read the Content and its first Part
            part = event.content and event.content.parts and event.content.parts[0]
            if not part:
                continue

            # Make sure we have a valid Part
            if not isinstance(part, types.Part):
                continue

            # Only send text if it's a partial response (streaming)
            # Skip the final complete message to avoid duplication
            if part.text and event.partial:
                message = {
                    "mime_type": "text/plain",
                    "data": part.text,
                    "role": "model",
                }
                await websocket.send_text(json.dumps(message))
                print(f"[AGENT TO CLIENT]: text/plain: {part.text}")


async def client_to_agent_messaging(
    websocket: WebSocket, live_request_queue: LiveRequestQueue
):
    \"\"\"Client to agent communication for live streaming.\"\"\"
    print(f"INFO: Client-to-agent messaging task started for {websocket.client}.")
    while True:
        # Decode JSON message
        print(f"INFO: Waiting for message from client {websocket.client}...")
        message_json = await websocket.receive_text()
        print(
            "INFO: Received message from client "
            f"{websocket.client}: {message_json[:100]}..."
        )
        message = json.loads(message_json)
        mime_type = message["mime_type"]
        data = message["data"]
        role = message.get(
            "role", "user"
        )  # Default to 'user' if role is not provided

        # Send the message to the agent
        if mime_type == "text/plain":
            # Send a text message
            content = types.Content(role=role, parts=[types.Part.from_text(text=data)])
            live_request_queue.send_content(content=content)
            print(f"INFO: [CLIENT TO AGENT] Sent to agent: {data}")
        else:
            print(f"ERROR: Mime type not supported: {mime_type}")
            raise ValueError(f"Mime type not supported: {mime_type}")
"""

#
# FastAPI web app
#

app = FastAPI()

STATIC_DIR = Path("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/aisofime/")
async def root():
    """Serves the index.html"""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
):
    """Client websocket endpoint using a simple request-response loop."""

    # Wait for client connection
    await websocket.accept()
    print(f"INFO: Client #{session_id} connected.")

    # Create a Session and Runner for this client
    try:
        session = session_service.create_session(
            app_name=APP_NAME,
            user_id=session_id,
            session_id=session_id,
        )
        runner = Runner(
            app_name=APP_NAME,
            agent=root_agent,
            session_service=session_service,
        )
        print(f"INFO: Agent session created for client #{session_id}.")
    except Exception as e:
        print(f"ERROR: Failed to create agent session for client #{session_id}: {e}")
        await websocket.close(
            code=1011, reason=f"Failed to create agent session: {e}"
        )
        return

    try:
        while True:
            # Wait for a message from the client
            message_json = await websocket.receive_text()
            message = json.loads(message_json)
            data = message["data"]
            role = message.get("role", "user")

            print(f"INFO: [CLIENT TO AGENT] Received: {data}")

            # Send the message to the agent using a loop for requests and responses run_async
            content = types.Content(role=role, parts=[types.Part.from_text(text=data)])
            
            final_response_text = ""
            async for event in runner.run_async(
                user_id=session.user_id, session_id=session.id, new_message=content
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    part = event.content.parts[0]
                    if part.text:
                        final_response_text = part.text
                        break

            

            # Extract the text from the response
            if final_response_text:
                    # Send the agent's response back to the client
                    response_message = {
                        "mime_type": "text/plain",
                        "data": final_response_text,
                        "role": "model",
                    }
                    await websocket.send_text(json.dumps(response_message))
                    print(f"INFO: [AGENT TO CLIENT] Sent: {final_response_text}")

                # The frontend expects a turn_complete message to unlock the UI
                    turn_complete_message = {"turn_complete": True, "interrupted": False}
                    await websocket.send_text(json.dumps(turn_complete_message))
                    print(f"INFO: [AGENT TO CLIENT] Sent turn_complete message")
            else:
                print("WARN: Agent response was empty or malformed.")


    except WebSocketDisconnect:
        print(f"INFO: Client #{session_id} disconnected.")
    except Exception as e:
        print(f"ERROR: An error occurred for client #{session_id}: {e}")
        # Optionally, send an error to the client
        await websocket.send_text(json.dumps({"error": str(e)}))
