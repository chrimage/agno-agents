#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "agno>=0.1.0",
#   "groq>=0.9.0", # Using groq library
#   "rich>=13.7.0",
#   "firecrawl-py>=0.1.0",
#   "python-dotenv>=1.0.0",
#   "pydantic>=2.0.0", # Often needed by agno/tools
# ]
# ///

"""
    Example Usage:
        # Ensure GROQ_API_KEY and FIRECRAWL_API_KEY are set in your environment or .env file
        # The URL should be included within the prompt itself.
        uv run sfa_scrapper_agent_groq_v1.py \
            --prompt "Scrape https://agenticengineer.com/principled-ai-coding and extract the names and descriptions of each lesson, formatted as a markdown list." \
            --output-file-path paic-lessons-groq.md

        uv run sfa_scrapper_agent_groq_v1.py -p "Summarize the main points from https://example.com" -o "summary.md"
"""

import os
import sys
import argparse
import asyncio
import traceback
from typing import Annotated # For tool type hinting
from textwrap import dedent

# Third-party imports
from agno.agent import Agent
from agno.models.groq import Groq # Using Groq model
from agno.tools import tool # For custom tool
from agno.tools.firecrawl import FirecrawlTools # Using Firecrawl tool
from pydantic import BaseModel, Field, ValidationError
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv
from groq import Groq as GroqClient # Import the client for API key check

# --- Globals ---
console = Console()

# --- Argument Parsing ---
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Web scraper agent (Groq) that filters content based on user query using Agno framework. The URL should be provided within the prompt."
    )
    # Removed --url argument
    parser.add_argument(
        "--output-file-path",
        "-o",
        default=None, # Changed default to None
        help="Optional suggested path to save the final processed content. Agent decides based on prompt.",
    )
    parser.add_argument(
        "--prompt", "-p", required=True, help="The prompt to filter/process the content with"
    )
    parser.add_argument(
        "--model",
        "-m",
        default="meta-llama/llama-4-scout-17b-16e-instruct", # Corrected default model for Groq
        help="Groq model ID to use",
    )
    # Removed --compute-limit as Agno's Agent doesn't directly expose max_loops in this way
    return parser.parse_args()

# --- Environment Setup ---
def load_environment():
    load_dotenv()
    groq_api_key = os.getenv("GROQ_API_KEY")
    firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")

    if not groq_api_key:
        console.print("[bold red]Error: GROQ_API_KEY environment variable not set.[/bold red]")
        console.print("Please create a .env file in the root directory with your key or export it.")
        sys.exit(1)
    if not firecrawl_api_key:
        console.print("[bold red]Error: FIRECRAWL_API_KEY environment variable not set.[/bold red]")
        sys.exit(1)

    # Optional: Validate Groq key connectivity (can add overhead)
    try:
        client = GroqClient(api_key=groq_api_key)
        client.models.list() # Simple API call to check key validity
        console.log("GROQ API key validated.")
    except Exception as e:
        console.print(f"[bold red]Error validating GROQ_API_KEY: {e}[/bold red]")
        sys.exit(1)

    return groq_api_key, firecrawl_api_key

# --- Custom Tool Definition ---
class WriteFileOutputArgs(BaseModel):
    reasoning: Annotated[str, Field(description="Explanation for why we are writing this content to the file.")]
    file_path: Annotated[str, Field(description="The path where the final processed content should be saved.")]
    content: Annotated[str, Field(description="The final processed markdown content to write.")]

@tool() # Removed args_schema
def write_final_output(reasoning: str, file_path: str, content: str) -> str:
    """
    Writes the final processed content to the specified local file path.
    This should be called only *after* the content has been scraped and processed
    according to the user's prompt.
    """
    console.log(f"[cyan]Executing Tool:[/cyan] write_final_output")
    console.log(f"  [dim]Reasoning:[/dim] {reasoning}")
    console.log(f"  [dim]File Path:[/dim] {file_path}")
    console.log(f"  [dim]Content Length:[/dim] {len(content)}")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        result = f"Successfully wrote {len(content)} characters to {file_path}."
        console.log(f"[green]Tool Result:[/green] {result}")
        return result
    except Exception as e:
        error_msg = f"Error writing to file {file_path}: {str(e)}"
        console.print(f"[bold red]Tool Error:[/bold red] {error_msg}")
        console.print(traceback.format_exc())
        return f"Error: {error_msg}"

# --- Agent Prompt Components ---
AGENT_DESCRIPTION = """You are a world-class web scraping and content processing expert using Groq and Firecrawl.
Your goal is to scrape web content based on a URL found within the user's prompt, process it according to the user's instructions, and save the final result to a file."""

AGENT_INSTRUCTIONS = [
    "1. **Identify URL:** Carefully read the user's request to identify the target URL to scrape.",
    "2. **Scrape Content:** Use the 'firecrawl_scrape_url' tool to get the content from the identified URL. **Do not proceed without scraped content.**",
    "3. **Analyze:** Carefully analyze the *scraped content* and the user's *full request/prompt*.",
    "4. **Process:** Process the scraped content to extract or summarize the information exactly as requested by the user. Format the processed content as markdown.",
    "5. **Decide to Save (Only if Requested):** Re-analyze the user's *exact* request. **Only** if the request *explicitly* asks to save the result (e.g., contains phrases like 'save the results', 'create a report named...', 'output to file X.md', 'save it'), then proceed to step 5a. Otherwise, skip to step 6.",
    "5a. **Determine Filename & Save:** If saving was requested, determine an appropriate filename. Use the suggested path if provided and relevant, otherwise create a descriptive filename based on the prompt content (e.g., 'summary-of-topic.md'). Use the 'write_final_output' tool to save the processed markdown content to this path. Provide clear reasoning for the filename and the save action.",
    "6. **Final Output:** If saving was *not* requested (you skipped step 5a), conclude by providing the final processed markdown content directly in your response. If you *did* save the file in step 5a, confirm the save action and the filename used.",
    "Provide clear reasoning when calling tools.",
    "Do not call 'write_final_output' with the raw scraped content; only call it with the final, processed result.",
]

# --- Main Execution ---
async def main():
    args = parse_arguments()
    groq_api_key, firecrawl_api_key = load_environment()

    # Prepare the initial prompt for the agent
    prompt_lines = [f"User Request: {args.prompt}"]
    if args.output_file_path:
        prompt_lines.append(f"Suggested Output File Path (optional): {args.output_file_path}")
    prompt_lines.append("\nPlease follow your instructions: identify the URL in my request, scrape it, process the content based on my full request, decide whether to save the final markdown result based on the request, and act accordingly.")

    initial_user_prompt = dedent("\n".join(prompt_lines)).strip()

    # Log the details, including the optional suggested path
    log_panel_content = f"User Prompt (contains URL): {args.prompt}"
    if args.output_file_path:
        log_panel_content += f"\nSuggested Output File Path: {args.output_file_path}"
    console.print(Panel(log_panel_content, title="Agent Task Details", expand=False, border_style="blue"))

    # Initialize FirecrawlTools
    # We only need the scrape functionality for a single URL here.
    firecrawl_tools = FirecrawlTools(api_key=firecrawl_api_key, scrape=True, crawl=False) # Corrected crawl=False

    # Initialize Agno Agent
    try:
        agent = Agent(
            model=Groq(api_key=groq_api_key, id=args.model),
            tools=[
                firecrawl_tools, # Provide Firecrawl scraping tool
                write_final_output # Provide custom file writing tool directly
            ],
            description=AGENT_DESCRIPTION,
            instructions=AGENT_INSTRUCTIONS,
            show_tool_calls=True,
            markdown=True, # Enable markdown output from the agent
        )
        console.log(f"Agno Agent initialized with model '{args.model}'.")
    except Exception as e:
        console.print(f"[bold red]Error initializing Agno Agent: {e}[/bold red]")
        console.print(traceback.format_exc())
        sys.exit(1)

    console.print(Panel("Starting Agent Interaction...", title="Agent Status", style="green"))

    # Run the agent interaction asynchronously
    try:
        # Use stream=True for potentially better responsiveness in logs
        await agent.aprint_response(initial_user_prompt, stream=True)
    except Exception as e:
        console.print(f"[bold red]An error occurred during agent execution:[/bold red]")
        console.print(traceback.format_exc())
    finally:
        console.print(Panel("Agent Interaction Finished.", title="Agent Status", style="blue"))

if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Agent execution interrupted by user.[/bold yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]An unexpected error occurred:[/bold red]")
        console.print(traceback.format_exc())
        sys.exit(1)
