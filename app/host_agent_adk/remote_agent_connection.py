from typing import Callable

import httpx
from a2a.types import (
    AgentCard,
    SendMessageRequest,
    SendMessageResponse,
)
from dotenv import load_dotenv

load_dotenv()

class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self, agent_card: AgentCard, agent_url: str):
        print(f"agent_card: {agent_card}")
        print(f"agent_url: {agent_url}")
        self._httpx_client = httpx.AsyncClient(timeout=30)
        self.agent_url = agent_url
        self.card = agent_card
        self.conversation_name = None
        self.conversation = None
        self.pending_tasks = set()

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_message(
        self, message_request: SendMessageRequest
    ) -> SendMessageResponse:
        response = await self._httpx_client.post(
            f"{self.agent_url}/",
            json=message_request.model_dump(exclude_none=True),
        )
        response.raise_for_status()
        return SendMessageResponse.model_validate(response.json())
