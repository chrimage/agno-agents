# /// script
# dependencies = [
#   "agno>=0.1.0", # Replace with actual version if needed
#   "google-genai>=0.5.0",
#   "pydantic>=2.0.0",
#   "rich>=13.0.0",
#   "python-dotenv>=1.0.0",
#   "mcp>=0.1.0", # Correct PyPI package name
# ]
# ///

import os
import subprocess
import json
import argparse
import asyncio
import sys
import traceback
from typing import Optional, Dict, Any, List, Union
from textwrap import dedent
import signal

# Third-party imports
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.mcp import MCPTools
# Removed ToolSpec import as local tool is removed
from mcp import StdioServerParameters
from pydantic import Field, BaseModel, ValidationError, validate_call # Keep pydantic for potential future local tools if needed
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool as GeminiTool

# --- Globals ---
console = Console()
REPO_ROOT = os.getcwd() # Define repo root for path resolution

# --- Argument Parsing ---
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="SFA Builder Agent: Uses Gemini and MCP tools (filesystem & bash) to build other SFAs.",
        epilog=f"Example: uv run single-file-agents/sfa_bash_editor_builder_gemini_v1.py -p 'Create hello world SFA' --mcp-filesystem-command 'npx -y @modelcontextprotocol/server-filesystem {REPO_ROOT}' --mcp-bash-command 'node /home/chris/Documents/Cline/MCP/bash-mcp-server/build/index.js'"
    )
    parser.add_argument("-p", "--prompt", required=True, help="The user's request/prompt for the agent (e.g., 'Create an SFA that uses the finance MCP server').")
    parser.add_argument(
        "--mcp-filesystem-command",
        required=True,
        help=f"Command to start the MCP filesystem server. Recommended: 'npx -y @modelcontextprotocol/server-filesystem {REPO_ROOT}'"
    )
    parser.add_argument(
        "--mcp-bash-command",
        required=True,
        help="Command to start the MCP bash execution server. E.g., 'node /path/to/bash-mcp-server/build/index.js'"
    )
    return parser.parse_args()

# --- Environment Setup ---
def load_environment():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[bold red]Error: GOOGLE_API_KEY environment variable not set.[/bold red]")
        console.print("Please create a .env file in the root directory with your key or export it.")
        sys.exit(1)
    genai.configure(api_key=api_key)
    return api_key

# --- Agent Prompt Components ---
AGENT_DESCRIPTION = """You are a specialist AI assistant powered by Google Gemini. Your primary goal is to **build other Single File Agents (SFAs)** based on user requests. You follow the SFA style guide provided in the context.

You have access to tools provided by **two separate MCP servers**:
1.  **Filesystem Server:** Provides tools like `read_file`, `write_file`, `edit_file`, `list_directory`, etc. These are essential for creating and modifying the SFA Python scripts. Assume paths are relative to the repository root unless specified otherwise.
2.  **Bash Server:** Provides the `execute_bash` tool for running shell commands, primarily for testing the generated SFA scripts using `uv run`.
"""

AGENT_INSTRUCTIONS = [
    "Understand the requirements for the new SFA the user wants to build.",
    "Plan the structure of the new SFA script (`sfa_<capability>_<provider>_v<version>.py`) following the style guide.",
    "Use the **filesystem tools** (e.g., `write_file`, `edit_file` from the filesystem MCP server) to create and populate the Python script for the new SFA in the `single-file-agents/` directory.",
    "Ensure the script includes necessary imports, dependencies (`/// script` block), argument parsing, API client setup (if needed), agent prompts, tool definitions/implementations, and the main execution loop.",
    "Pay close attention to the required dependencies and list them correctly in the `/// script` block.",
    "Once the script is written or modified, use the **`execute_bash`** tool (from the bash MCP server) to test it, typically using `uv run single-file-agents/<new_agent_name.py> --prompt <test_prompt> [other_args...]`.",
    "Analyze the output (stdout/stderr) from the bash command.",
    "If the test fails or produces errors, use the **filesystem tools** (`edit_file`) to debug and correct the SFA script.",
    "Repeat the testing and editing cycle until the new SFA works as expected.",
    "If you need to see the contents of a directory or file, use the appropriate filesystem tool.",
    "Provide clear reasoning for each tool call.",
    "Inform the user upon successful creation and testing of the new SFA.",
    "**Note:** Your capabilities could be further enhanced if additional MCP servers were available, such as `@pydantic/mcp-run-python` for safer Python execution or `@modelcontextprotocol/server-brave-search` for researching APIs/libraries. If the user's request requires complex code generation or external knowledge, suggest that these tools would be helpful if provided."
]

# --- Main Execution ---
async def main():
    args = parse_arguments()
    load_environment()

    console.print(Panel(f"User Prompt: {args.prompt}", title="Agent Task: Build SFA", expand=False))
    console.print(f"MCP Filesystem Server Command: {args.mcp_filesystem_command}")
    console.print(f"MCP Bash Server Command: {args.mcp_bash_command}")

    # Prepare MCP Server connection parameters for Filesystem
    fs_command_parts = args.mcp_filesystem_command.split()
    fs_command_executable = fs_command_parts[0]
    fs_command_args = fs_command_parts[1:]
    fs_server_params = StdioServerParameters(
        command=fs_command_executable,
        args=fs_command_args,
    )

    # Prepare MCP Server connection parameters for Bash
    bash_command_parts = args.mcp_bash_command.split()
    bash_command_executable = bash_command_parts[0]
    bash_command_args = bash_command_parts[1:]
    bash_server_params = StdioServerParameters(
        command=bash_command_executable,
        args=bash_command_args,
    )

    console.print(f"Attempting to connect to MCP filesystem server via: {fs_server_params.command} {' '.join(fs_server_params.args)}")
    console.print(f"Attempting to connect to MCP bash server via: {bash_server_params.command} {' '.join(bash_server_params.args)}")

    try:
        # Nest MCPTools contexts: one for filesystem, one for bash
        async with MCPTools(server_params=fs_server_params) as mcp_filesystem_tools:
            console.log("MCPTools session for filesystem started.")
            async with MCPTools(server_params=bash_server_params) as mcp_bash_tools:
                console.log("MCPTools session for bash started.")

                # Initialize Agno Agent with BOTH MCP tool instances
                try:
                    agent = Agent(
                        model=Gemini(id="gemini-1.5-flash"), # Or "gemini-1.5-pro"
                        tools=[mcp_filesystem_tools, mcp_bash_tools], # Pass both MCP tool instances
                        description=AGENT_DESCRIPTION,
                        instructions=AGENT_INSTRUCTIONS,
                        show_tool_calls=True,
                        markdown=True,
                    )
                    console.log("Agno Agent initialized with Filesystem and Bash MCP tools.")
                except Exception as e:
                    console.print(f"[bold red]Error initializing Agno Agent: {e}[/bold red]")
                    console.print(traceback.format_exc())
                    sys.exit(1)

                console.print(Panel("Starting Agent Interaction...", title="Agent Status", style="green"))

                # Run the agent interaction asynchronously
                try:
                    await agent.aprint_response(args.prompt, stream=True)
                except Exception as e:
                    console.print(f"[bold red]An error occurred during agent execution:[/bold red]")
                    console.print(traceback.format_exc())

    except Exception as e:
        console.print(f"[bold red]Failed to establish or maintain MCP connection: {e}[/bold red]")
        console.print(traceback.format_exc())
    finally:
        console.print(Panel("Agent Interaction Finished.", title="Agent Status", style="blue"))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Agent execution interrupted by user.[/bold yellow]")
        sys.exit(1)
