#!/usr/bin/env -S uv run --script

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
import asyncio # Added for async operation
import sys
import traceback
from typing import Optional, Dict, Any, List
from textwrap import dedent # For cleaner multiline strings
import signal # Needed for os.killpg

# Third-party imports
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.mcp import MCPTools # Correct MCP tool integration
from mcp import StdioServerParameters # Correct MCP parameter class
from pydantic import Field, BaseModel, ValidationError, validate_call
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv
import google.generativeai as genai

# --- Globals ---
console = Console()
# No longer need manual MCP process/client/thread globals

# --- Argument Parsing ---
def parse_arguments():
    parser = argparse.ArgumentParser(description="Generic SFA using Gemini to interact with any self-managed MCP server via stdio.")
    parser.add_argument("-p", "--prompt", required=True, help="The user's request/prompt for the agent.")
    parser.add_argument("--mcp-command", required=True, help="The full command to execute to start the target MCP server (e.g., 'npx -y @modelcontextprotocol/server-filesystem /path/to/root').")
    # Removed --compute as max_loops is not a direct Agent param in this structure
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
# Simplified, relying on MCPTools to expose tool details to the LLM
AGENT_DESCRIPTION = """You are an AI assistant powered by Google Gemini. You can interact with external tools provided by a connected Model Context Protocol (MCP) server."""

AGENT_INSTRUCTIONS = [
    "Carefully analyze the user's request.",
    "Determine which of the available tools is most appropriate to fulfill the request.",
    "Determine the correct arguments for the chosen tool based on its description.",
    "Call the tool with the arguments.",
    "Present the result from the tool back to the user.",
    "If the tool returns an error, report the error clearly.",
    "If the request requires multiple steps, perform them sequentially.",
]

# --- Main Execution ---
async def main(): # Changed to async
    args = parse_arguments()
    load_environment()

    console.print(Panel(f"User Prompt: {args.prompt}", title="Agent Task", expand=False))
    console.print(f"MCP Server Command: {args.mcp_command}")

    # Split the command string for StdioServerParameters
    # This is basic splitting; might need refinement for complex shell commands
    command_parts = args.mcp_command.split()
    command_executable = command_parts[0]
    command_args = command_parts[1:]

    server_params = StdioServerParameters(
        command=command_executable,
        args=command_args,
        # env=os.environ # Pass environment if needed by the server
    )

    console.print(f"Attempting to connect to MCP server via: {server_params.command} {' '.join(server_params.args)}")

    try:
        # Use MCPTools as an async context manager
        async with MCPTools(server_params=server_params) as mcp_tools:
            console.log("MCPTools session started. Tools should be discovered.")

            # Initialize Agno Agent
            try:
                agent = Agent(
                    model=Gemini(id="gemini-1.5-flash"), # Or "gemini-1.5-pro"
                    tools=[mcp_tools], # Pass the MCPTools instance
                    description=AGENT_DESCRIPTION,
                    instructions=AGENT_INSTRUCTIONS, # Pass base instructions
                    show_tool_calls=True,
                    markdown=True,
                )
                console.log("Agno Agent initialized.")
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
        # Cleanup is handled by the async context manager

if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Agent execution interrupted by user.[/bold yellow]")
        sys.exit(1)
