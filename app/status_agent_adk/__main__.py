import logging
import os


import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from starlette.routing import Mount
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from agent import create_agent
from agent_executor import StatusAgentExecutor
from dotenv import load_dotenv
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""

    pass


def main():
    """Starts the agent server."""
    host = "localhost"
    port = int(os.getenv("PORT_STATUS_AGENT"))
    url_path = os.getenv("URL_PATH_STATUS_AGENT")
    statusAgentUrl = f"http://{host}:{port}/{url_path}"
    cardUrl = f"/.well-known/agent.json"
    starletteAppRoute = f"/{url_path}"
    print(f"Status Agent URL: {statusAgentUrl}")
    print(f"Card URL: {cardUrl}")
    print(f"Starlette App Route: {starletteAppRoute}")
    try:
        # Check for API key only if Vertex AI is not configured
        if not os.getenv("GOOGLE_GENAI_USE_VERTEXAI") == "TRUE":
            if not os.getenv("GOOGLE_API_KEY"):
                raise MissingAPIKeyError(
                    "GOOGLE_API_KEY environment variable not set and GOOGLE_GENAI_USE_VERTEXAI is not TRUE."
                )

        capabilities = AgentCapabilities(streaming=False)
        list_available_relocations_skill = AgentSkill(
            id="list_available_relocations",
            name="List all available relocations",
            description="Returns a list of all currently available relocations.",
            tags=["relocation", "status"],
            examples=["What are the available relocations?"],
        )
        get_relocation_status_skill = AgentSkill(
            id="get_relocation_status",
            name="Get the status of a relocation",
            description="Returns the status of a relocation.",
            tags=["relocation", "status"],
            examples=["What is the status of relocation for John?"],
        )
        agent_card = AgentCard(
            name="Status Agent",
            description="An agent grant access to relocation status informations",
            url=statusAgentUrl,
            version="1.0.0",
            defaultInputModes=["text/plain"],
            defaultOutputModes=["text/plain"],
            capabilities=capabilities,
            skills=[list_available_relocations_skill, get_relocation_status_skill],
        )

        adk_agent = create_agent()
        runner = Runner(
            app_name=agent_card.name,
            agent=adk_agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        agent_executor = StatusAgentExecutor(runner)

        request_handler = DefaultRequestHandler(
            agent_executor=agent_executor,
            task_store=InMemoryTaskStore(),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        uvicorn.run(Mount(starletteAppRoute, server.build(agent_card_url=cardUrl)), host=host, port=port)
        # uvicorn.run(server.build(), host=host, port=port) 
    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)


if __name__ == "__main__":
    main()
