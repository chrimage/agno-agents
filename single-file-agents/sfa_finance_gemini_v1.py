
#!/usr/bin/env python
# Removed the /// script block to rely on pre-installed dependencies via uv pip install

"""
sfa_finance_gemini_v1.py

A Single File Agent (SFA) using Google Gemini and the Agno framework
with built-in DuckDuckGo and YFinance tools for stock market analysis tasks.

Usage:
    # Get current price and news for Apple
    uv run single-file-agents/sfa_finance_gemini_v1.py -p "What's the latest stock price and news for AAPL?"

    # Get historical data for Microsoft
    uv run single-file-agents/sfa_finance_gemini_v1.py -p "Show me the last 3 months of daily historical data for MSFT."

    # Research a company
    uv run single-file-agents/sfa_finance_gemini_v1.py -p "Give me a summary of Tesla (TSLA) and recent news about them."
"""

import os
import argparse
import asyncio
import sys
import traceback
from typing import List
from textwrap import dedent

# Third-party imports
from agno.agent import Agent
from agno.models.google import Gemini # Restore model import
from agno.tools.duckduckgo import DuckDuckGoTools # Correct import from dev.to example
from agno.tools.yfinance import YFinanceTools     # Correct import from dev.to example
from pydantic import Field, BaseModel, ValidationError, validate_call
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv
import google.generativeai as genai # Restore genai import

# --- Globals ---
console = Console()

# --- Argument Parsing ---
def parse_arguments():
    parser = argparse.ArgumentParser(description="SFA using Gemini with DuckDuckGo and YFinance tools.")
    parser.add_argument("-p", "--prompt", required=True, help="The user's financial analysis request.")
    # Add other finance-specific arguments if needed later
    return parser.parse_args()

# --- Environment Setup ---
def load_environment():
    load_dotenv() # Load variables from .env file in the root
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[bold red]Error: GOOGLE_API_KEY environment variable not set.[/bold red]")
        console.print("Please create a .env file in the root directory with your key or export it.")
        sys.exit(1)
    genai.configure(api_key=api_key) # Restore genai configure
    return api_key

# --- Agent Prompt Components ---
AGENT_DESCRIPTION = """You are an AI assistant specialized in financial and stock market analysis, powered by Google Gemini. You have access to tools for searching the web (DuckDuckGo) and retrieving stock market data (YFinance)."""

AGENT_INSTRUCTIONS = [
    "Carefully analyze the user's financial request.",
    "Determine whether you need current stock data, historical data, company information, news, analyst recommendations, fundamentals, financial ratios, or technical indicators.",
    "Use the `YFinanceTools` for specific stock data (current price, historical data, company info, fundamentals, ratios, recommendations, technicals). You'll need a valid ticker symbol.",
    "Use the `DuckDuckGoSearch` tool for recent news, broader company research, or finding ticker symbols if not provided.",
    "If asked for analysis, opinions, or recommendations (which you cannot directly provide):",
    "  - First, state clearly that you cannot provide financial advice or direct recommendations.",
    "  - If the request is broad (e.g., 'what should I buy?', 'recommend a stock'):",
    "    - Ask the user to specify a particular stock or sector they are interested in.",
    "    - Alternatively, offer to analyze a major index (like SPY) or a well-known stock (like MSFT or AAPL) as an example, using the available tools.",
    "  - If the request *does* specify a stock/sector:",
    "    - Use tools like `get_analyst_recommendations`, `get_stock_fundamentals`, `get_key_financial_ratios`, `get_company_news`, etc., to gather relevant data points.",
    "    - Synthesize this information from multiple tool calls.",
    "When presenting data returned by tools (especially JSON data):",
    "  - Summarize the key information.",
    "  - Format your response using markdown.",
    "  - Use tables to display structured data like historical prices, recommendations, or key ratios where practical. If the data is too long for a table, provide a summary and mention that the full data was returned by the tool.",
    "Explicitly state that you cannot provide financial advice or direct buy/sell recommendations, but you can present the data you gathered.",
    "If a tool call fails (e.g., invalid ticker), report the error message accurately.",
    "If a ticker symbol is needed but not provided, use DuckDuckGoSearch to try and find it first.",
]

# --- Main Execution ---
async def main():
    args = parse_arguments()
    load_environment()

    console.print(Panel(f"User Prompt: {args.prompt}", title="Agent Task: Finance Analysis", expand=False))

    # Instantiate the tools
    try:
        # Use the correct class names from dev.to example
        # Enable a wider range of analytical tools
        duckduckgo_tool = DuckDuckGoTools()
        yfinance_tool = YFinanceTools(
            stock_price=True,               # Default
            company_info=True,              # Enabled
            company_news=True,              # Enabled
            historical_prices=True,         # Enabled
            analyst_recommendations=True,   # Enable analyst views
            stock_fundamentals=True,        # Enable fundamentals
            key_financial_ratios=True,      # Enable ratios
            technical_indicators=True       # Enable technicals
        )
        tools = [duckduckgo_tool, yfinance_tool] # List of tool instances
        console.log("Initialized DuckDuckGo and YFinance tools (with extended analysis tools enabled).")
    except Exception as e:
        console.print(f"[bold red]Error initializing tools: {e}[/bold red]")
        console.print(traceback.format_exc())
        sys.exit(1)


    # Initialize Agno Agent
    try:
        agent = Agent(
            # Revert to the working standard model ID due to API errors with the preview model
            model=Gemini(id="gemini-2.5-pro-preview-03-25"),
            tools=tools, # Pass the list of tool instances
            description=AGENT_DESCRIPTION,
            instructions=AGENT_INSTRUCTIONS,
            show_tool_calls=True,
            markdown=True,
        )
        console.log("Agno Finance Agent initialized.")
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
    finally:
        console.print(Panel("Agent Interaction Finished.", title="Agent Status", style="blue"))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Agent execution interrupted by user.[/bold yellow]")
        sys.exit(1)
