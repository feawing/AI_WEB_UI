import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, AsyncIterable, List
import os

import httpx
import nest_asyncio
from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
)
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import Client
from google.genai import types





from .remote_agent_connection import RemoteAgentConnections
from .models import Relocation

load_dotenv()
nest_asyncio.apply()

#Hard coded agent urls for now
# was in _get_initialized_host_agent_sync() 
friend_agent_urls = [
            "http://localhost:10001/aisofimestatus",  # Status agent
#            "http://localhost:10003",  # Nate's Agent
#            "http://localhost:10004",  # Kaitlynn's Agent
]

#api_key=os.getenv("GEMINI_API_KEY"),
#model=os.getenv("GEMINIMODEL")

class HostAgent:
    """The Host agent."""
    sub_agents: List[Any] = []

    def __init__(
        self,
    ):
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ""
        self._agent = self.create_agent()
        self._user_id = "host_agent"
        # This should be filled in (probably in _async_init_components()) if the host agent use non-A2A subagents (OR TOOLS ! )
        self._runner = Runner(
            app_name="Host_Agent",
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        

    async def _async_init_components(self, remote_agent_addresses: List[str]):
        async with httpx.AsyncClient(timeout=30) as client:
            for address in remote_agent_addresses:
                card_resolver = A2ACardResolver(client, address)
                try:
                    card = await card_resolver.get_agent_card()
                    remote_connection = RemoteAgentConnections(
                        agent_card=card, agent_url=address
                    )
                    self.remote_agent_connections[card.name] = remote_connection
                    self.cards[card.name] = card
                except httpx.ConnectError as e:
                    print(f"ERROR: Failed to get agent card from {address}: {e}")
                except Exception as e:
                    print(f"ERROR: Failed to initialize connection for {address}: {e}")
        
        # We modify the class attribute here
        HostAgent.sub_agents = []
        agent_info = [
            json.dumps({"name": card.name, "description": card.description})
            for card in self.cards.values()
        ]
        print("agent_info:", agent_info)
        self.agents = "\n".join(agent_info) if agent_info else "No friends found"

    @classmethod
    async def create(
        cls,
        remote_agent_addresses: List[str],
    ):
        instance = cls()
        await instance._async_init_components(remote_agent_addresses)
        return instance

    def create_agent(self) -> LlmAgent:
        return LlmAgent(
            model=os.getenv("GEMINICLIENTMODEL"),
            name="Host_Agent",
            instruction=self.root_instruction(None),
            tools=[
                self.send_message,
            ],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        return f"""
        **Role:** You are the Host Agent, an expert communicator. Your primary function is to coordinate with Sofime (a relocation agency) to get information about the user's relocation.

        **Context:**
            * A relocation is a mission to move a person or a family from one place to another. this person or family is called an "expat". So whenever the user asks anything about a "relocation", a "relo" or an "expat", you should understand that they are asking about a relocation.
            * A relocation can be open, closed, or cancelled. An open relocation is a relocation that is currently in progress. A closed relocation is a relocation that has been completed. A cancelled relocation is a relocation that has been cancelled.
            * A relocation is identified by the expat's complete name, the expat's email adress or a unique technical ID. 

        **Core Directives:**

        *   **Initiate Planning:** When asked to access relocation information, first determine which of relocation agents you should contact.
        *   **Task Delegation:** Use the `send_message` tool to ask any information to the relocation agency agent.
            *   Frame your request clearly (e.g., "what are the currently open relocations?" or "what is the status of the relocation for John Doe?").
            *   Make sure you pass in the official name of the relocation agent for each message request.
        *   **Analyze Responses:** Once you have responses from relocation agency agents, analyze the responses to gather the answer to the user's question.
            *   Agents responses can be a pydantic model or a list of pydantic models for the Relocation type.
            *   If the status agent returns a long list of relocations (more than 10), you should notify the user of the total number of relocations and present them with the 10 most recently modified relocations based on the relocation last update date and time
        *   **Propose and Confirm:** Present the answer to the user question to the user in a concise and easy to read format (bullet points are good).
        *   **Transparent Communication:** If the user request was to modify an information, gives an confirmation that the information has been modified, after it's done
        *   **Tool Reliance:** Strictly rely on available tools to address user requests. Do not generate responses based on assumptions.
        *   **Readability:** Make sure to respond in a concise and easy to read format (bullet points are good).
        *   When asked for which agents are available, you should return the names of the available relocation agency agents (aka the agents that are active).
        

        **Today's Date (YYYY-MM-DD):** {datetime.now().strftime("%Y-%m-%d")}

        <Available Agents>
        {self.agents}
        </Available Agents>
        """

    async def stream(
        self, query: str, session_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        """
        Streams the agent's response to a given query.
        """
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        content = types.Content(role="user", parts=[types.Part.from_text(text=query)])
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                response = ""
                if (
                    event.content
                    and event.content.parts
                    and event.content.parts[0].text
                ):
                    response = "\n".join(
                        [p.text for p in event.content.parts if p.text]
                    )
                yield {
                    "is_task_complete": True,
                    "content": response,
                }
            else:
                yield {
                    "is_task_complete": False,
                    "updates": "The host agent is thinking...",
                }

    async def send_message(self, agent_name: str, task: str, tool_context: ToolContext):
        """Sends a task to a remote friend agent."""
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f"Agent {agent_name} not found")
        client = self.remote_agent_connections[agent_name]

        if not client:
            raise ValueError(f"Client not available for {agent_name}")

        # Simplified task and context ID management
        state = tool_context.state
        task_id = state.get("task_id", str(uuid.uuid4()))
        context_id = state.get("context_id", str(uuid.uuid4()))
        message_id = str(uuid.uuid4())

        payload = {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": task}],
                "messageId": message_id,
                "taskId": task_id,
                "contextId": context_id,
            },
        }

        message_request = SendMessageRequest(
            id=message_id, params=MessageSendParams.model_validate(payload)
        )
        send_response: SendMessageResponse = await client.send_message(message_request)
        print("send_response", send_response)

        if not isinstance(
            send_response.root, SendMessageSuccessResponse
        ) or not isinstance(send_response.root.result, Task):
            print("Received a non-success or non-task response. Cannot proceed.")
            return

        response_content = send_response.root.model_dump_json(exclude_none=True)
        json_content = json.loads(response_content)

        resp = []
        if json_content.get("result", {}).get("artifacts"):
            for artifact in json_content["result"]["artifacts"]:
                if artifact.get("parts"):
                    resp.extend(artifact["parts"])
        return resp


def _get_initialized_host_agent_sync():
    """Synchronously creates and initializes the HostAgent."""

    async def _async_main():
        print("initializing host agent")
        hosting_agent_instance = await HostAgent.create(
            remote_agent_addresses=friend_agent_urls
        )
        print("HostAgent initialized")
        return hosting_agent_instance.create_agent()

    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            print(
                f"Warning: Could not initialize HostAgent with asyncio.run(): {e}. "
                "This can happen if an event loop is already running (e.g., in Jupyter). "
                "Consider initializing HostAgent within an async function in your application."
            )
        else:
            raise


root_agent = _get_initialized_host_agent_sync()

def create_agent():
    return HostAgent().create_agent()
