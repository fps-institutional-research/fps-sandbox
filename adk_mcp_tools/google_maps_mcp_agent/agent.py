import os
from dotenv import load_dotenv
import sys
from google.adk.agents import LlmAgent
from google.adk.apps.app import App

# Add the parent directory to sys.path to allow importing from adk_utils
# Note: this is from genAI104 and the directory is not the same. So may need to tweak.
# Get the absolute path of the directory containing agent.py
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (adk_mcp_tools)
parent_dir = os.path.dirname(current_dir)

# Insert it at the beginning of the path list
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Debug: Print the path so you can see it in the terminal logs
print(f"DEBUG: Searching for modules in: {parent_dir}")

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, \
                StdioServerParameters, StdioConnectionParams
from google.genai import types
from adk_utils.plugins import LabExUtils
from google.adk.models import Gemini
from google.genai.types import HttpRetryOptions

load_dotenv()
google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")

if not google_maps_api_key:
    print("WARNING: GOOGLE_MAPS_API_KEY is not set. Please set it as an environment variable or update it in the script.")

# Retry options help avoid the occasional error from popular models
# receiving too many requests at once.
RETRY_OPTIONS = types.HttpRetryOptions(initial_delay=1, max_delay=3, attempts=30)
plugins = [LabExUtils()]

root_agent = LlmAgent(
    # name: A unique name for the agent.
    name='maps_assistant_agent',
    # description: A short description of the agent's purpose, so
    # other agents in a multi-agent system know when to call it.
    description="Use google maps to find directions.",
    # model: The LLM model that the agent will use:
    model=Gemini(model=os.getenv("MODEL"), retry_options=RETRY_OPTIONS),
     # instruction: Instructions (or the prompt) for the agent.
    instruction="""
        Help the user with mapping, directions, and finding places
        using Google Maps tools.
    """,
    # tools: functions to enhance the model's capabilities.
    # Add the MCPToolset, by adding the google_search tool below.
    tools=[
    MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=[
                "-y",
                "@modelcontextprotocol/server-google-maps",
            ],
            env={
                "GOOGLE_MAPS_API_KEY": google_maps_api_key
            }
        ),
        timeout=15,
        ),
    )
],
)

app = App(
    name="google_maps_mcp_agent",
    root_agent=root_agent,
    plugins=plugins
)
# UNCOMMENT THE LINE BELOW TO TEST FAILOVER:
### Is there a way to add something here for testing purpose.