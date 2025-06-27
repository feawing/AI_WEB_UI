from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

model = LiteLlm(
    model=os.getenv("GEMINI_MODEL"),
    api_key=os.getenv("GOOGLE_API_KEY"),
)

root_agent = LlmAgent(
    # A unique name for the agent.
    name="jarvis",
    model=model,    
    description="coder-assistant agent.",
    instruction=f"""
    You are Jarvis, a helpful assistant that can help developper with any question relative to coding.
    
    You are able to answer any question relative to syntax and/or good practices relative to coding in Python, Javascript, SQL, etc. 

    Important:
    - Unless asked otherwise, give context to your answers.
    
    Today's date is {datetime.now().strftime("%Y-%m-%d")}.
    """,
    tools=[
    ],
)
