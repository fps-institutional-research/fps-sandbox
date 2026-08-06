import os
import sys
from dotenv import load_dotenv
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

from google.genai import types
from adk_utils.plugins import LabExUtils
from google.adk.models import Gemini
from google.genai.types import HttpRetryOptions
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, \
                    StdioServerParameters, StdioConnectionParams

load_dotenv()

# IMPORTANT: Replace this with the ABSOLUTE path to your adk_server.py script
PATH_TO_YOUR_MCP_SERVER_SCRIPT = "/home/student_01_1712a763b8b6/adk_mcp_tools/adk_mcp_server/adk_server.py"

# Retry options help avoid the occasional error from popular models
# receiving too many requests at once.
RETRY_OPTIONS = types.HttpRetryOptions(initial_delay=1, max_delay=3, attempts=30)
plugins = [LabExUtils()]

if PATH_TO_YOUR_MCP_SERVER_SCRIPT == "None":
    print("WARNING: PATH_TO_YOUR_MCP_SERVER_SCRIPT is not set. Please update it in agent.py.")
    # Optionally, raise an error if the path is critical

root_agent = LlmAgent(
    model=Gemini(model=os.getenv("MODEL"), retry_options=RETRY_OPTIONS),
    # name: A unique name for the agent.
    name='web_reader_mcp_client_agent',
    # description: A short description of the agent's purpose, so
    # other agents in a multi-agent system know when to call it.
    description="Use an mcp server with your agent to read web pages.",
    # instruction: Instructions (or the prompt) for the agent.
    instruction="""
        Use the 'load_web_page' tool to fetch content from a URL
        provided by the user.
     """,
    # tools: functions to enhance the model's capabilities.
    # Add the MCPToolset below:
    tools=[
    MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python3", # Command to run your MCP server script
            args=[PATH_TO_YOUR_MCP_SERVER_SCRIPT], # Argument is the path to the script
        ),
        timeout=15,
        ),
        tool_filter=['load_web_page'] # Optional: ensure only specific tools are loaded
    )
],
)

app = App(
    name="adk_mcp_server",
    root_agent=root_agent,
    plugins=plugins
)
# UNCOMMENT THE LINE BELOW TO TEST FAILOVER:
### Is there a way to add something here for testing purpose.