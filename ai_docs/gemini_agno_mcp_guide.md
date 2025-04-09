# Building an Agent with Google Gemini, Agno, and MCP

This guide walks you through building a basic AI agent using Google's Gemini models, the Agno framework, and integrating tools via the Model Context Protocol (MCP).

## Introduction

*   **Google Gemini**: A family of powerful multimodal large language models developed by Google.
*   **Agno**: A lightweight, model-agnostic Python library for building AI agents quickly. It provides abstractions for models, tools, memory, and knowledge.
*   **MCP (Model Context Protocol)**: A standard protocol allowing AI models/agents to interact with external tools and resources (like local file systems, APIs, web scrapers, etc.) running in separate server processes.

By combining these technologies, you can create agents that leverage Gemini's reasoning capabilities, Agno's agent framework, and MCP's extensibility for diverse tasks.

## Prerequisites

*   Python 3.8+ installed.
*   Access to Google Gemini:
    *   **Option 1 (Simpler): Google AI Studio API Key**. Get one from [Google AI Studio](https://ai.google.dev/aistudio).
    *   **Option 2 (Advanced): Google Cloud Vertex AI**. Requires `gcloud` CLI setup and a Google Cloud project. See [Agno Gemini Docs](https://docs.agno.com/models/google#vertex-ai) for details.
*   Basic understanding of MCP concepts (servers, tools). You'll need an MCP server that can be started via a command-line command.
*   `pip` for installing Python packages.
*   The `mcp` library for MCP interactions.

## Step 1: Install Libraries

Install Agno, the necessary Google library, and the MCP library:

```bash
pip install -U agno google-generativeai mcp
```

## Step 2: Set Up Authentication (Google AI Studio)

Export your Google AI Studio API key as an environment variable. Replace `***` with your actual key.

```bash
export GOOGLE_API_KEY='***'
```

*(If using Vertex AI, follow the setup steps in the [Agno Gemini Docs](https://docs.agno.com/models/google#vertex-ai).)*

## Step 3: Create a Basic Agno Agent with Gemini

This example creates a simple agent using the `gemini-1.5-flash` model.

```python
# basic_gemini_agent.py
from agno.agent import Agent
from agno.models.google import Gemini

# Ensure your GOOGLE_API_KEY is set in your environment
agent = Agent(
    model=Gemini(id="gemini-1.5-flash"),
    description="You are a helpful assistant.",
    markdown=True, # Format output as Markdown
)

# Interact with the agent
agent.print_response("Explain the concept of quantum entanglement in simple terms.", stream=True)
```

Run this script: `python basic_gemini_agent.py`

## Step 4: Integrating MCP Tools with Agno using `MCPTools`

Agno provides a convenient way to integrate with MCP servers using the `agno.tools.mcp.MCPTools` class. This class handles the lifecycle of the MCP server process (started via stdio) and automatically discovers and exposes the server's tools to the Agno agent.

**Key Components:**

1.  **`mcp.StdioServerParameters`**: This class from the `mcp` library is used to define how to start the MCP server. You provide the command and arguments needed to launch the server process.
2.  **`agno.tools.mcp.MCPTools`**: This class acts as a tool provider for the Agno agent. You initialize it with the `StdioServerParameters`. It's best used as an asynchronous context manager (`async with`) to ensure the server process is properly managed.

**Example Setup:**

```python
# mcp_integration_example.py
import asyncio
import os
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters # From the 'mcp' library

# Assume GOOGLE_API_KEY is set in the environment

async def run_agent_with_mcp(user_prompt: str, mcp_command: str):
    # 1. Prepare MCP Server Parameters
    # Basic command splitting (adjust if needed for complex commands)
    command_parts = mcp_command.split()
    server_params = StdioServerParameters(
        command=command_parts[0],
        args=command_parts[1:],
        # env=os.environ # Optionally pass environment variables
    )

    print(f"Attempting to connect to MCP server via: {server_params.command} {' '.join(server_params.args)}")

    # 2. Use MCPTools as an async context manager
    try:
        async with MCPTools(server_params=server_params) as mcp_tools:
            print("MCPTools session started. Discovering tools...")

            # 3. Initialize Agno Agent, passing MCPTools instance
            agent = Agent(
                model=Gemini(id="gemini-1.5-flash"),
                tools=[mcp_tools], # Pass the MCPTools instance directly
                description="You are an AI assistant interacting with an MCP server.",
                instructions=[
                    "Use the available tools provided by the MCP server to fulfill the user request.",
                    "Clearly state the results or any errors encountered."
                ],
                show_tool_calls=True,
                markdown=True,
            )
            print("Agno Agent initialized.")

            # 4. Interact with the agent
            print(f"\nProcessing prompt: {user_prompt}")
            await agent.aprint_response(user_prompt, stream=True)

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

# --- Example Usage ---
# Define the command to start your MCP server
# Example: Using the MCP filesystem server
mcp_server_start_command = "npx -y @modelcontextprotocol/server-filesystem /tmp" # Adjust path as needed

# Define the user's request
prompt = "List the files in the /tmp directory."

# Run the async function
# asyncio.run(run_agent_with_mcp(prompt, mcp_server_start_command))
```

**Explanation:**

1.  We define how to start the MCP server using `StdioServerParameters`.
2.  We create an instance of `MCPTools` within an `async with` block, passing the server parameters. This starts the server process and establishes communication.
3.  Crucially, we pass the `mcp_tools` instance directly into the `tools` list when creating the `Agent`. Agno automatically introspects `mcp_tools` to find the available tools from the connected server and makes them available to the Gemini model.
4.  The agent interaction (`agent.aprint_response`) happens within the `async with` block, ensuring the MCP connection is active. When the block exits, `MCPTools` automatically shuts down the server process.

This approach eliminates the need to manually define `Tool` subclasses for each MCP tool you want to use.

## Step 5: Running the Agent with `MCPTools`

1.  **Ensure MCP Server is Runnable**: Make sure the command you provide (`mcp_server_start_command` in the example) correctly starts your target MCP server. For Node.js based servers, `npx` is often used.
2.  **Set Environment Variables**: Ensure `GOOGLE_API_KEY` is set. If your MCP server requires specific environment variables, you might need to pass them via `StdioServerParameters(..., env=...)`.
3.  **Run the Python Script**: Execute the script (e.g., `python mcp_integration_example.py`).

The script will:
*   Start the MCP server using the provided command.
*   Connect `MCPTools` to the server.
*   Initialize the Agno `Agent` with Gemini and the discovered MCP tools.
*   Pass the user prompt to the agent.
*   Gemini will analyze the prompt and the available tools (discovered via `MCPTools`).
*   If a suitable tool is found, the agent will call it through `MCPTools`, which handles the communication with the server process.
*   The result (or error) from the MCP tool is returned to the agent.
*   Gemini formulates the final response based on the tool's output.
*   Upon completion or error, the `async with` block ensures the MCP server process is terminated.

## Conclusion

You've learned how to create an Agno agent using Google Gemini and seamlessly integrate external tools via MCP using the `agno.tools.mcp.MCPTools` class. This significantly simplifies the process compared to manually creating tool wrappers, allowing you to build powerful, extensible agents capable of leveraging both advanced language models and specialized external functionalities provided by MCP servers.

## Conclusion

You've learned the basics of creating an Agno agent using Google Gemini and how to conceptually integrate custom tools for interacting with MCP servers. This combination allows you to build powerful, extensible agents capable of leveraging both advanced language models and specialized external functionalities.

**Next Steps:**

*   Explore other Gemini models (`gemini-1.5-pro`, etc.).
*   Implement robust communication and error handling for your custom MCP tools.
*   Investigate Agno's features for memory, knowledge bases, and multi-agent teams.
*   Build or find specific MCP servers for the tools your agent needs (e.g., web scraping, database access, API interaction).
