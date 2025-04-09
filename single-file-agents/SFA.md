# SFA.md - Single File Agent Style Guide

This document outlines the conventions and best practices for creating Single File Agents (SFAs) within this repository. SFAs are self-contained Python scripts designed for specific tasks, managing their dependencies and execution environment via `uv`.

## 1. Purpose

Single File Agents (SFAs) are designed to perform focused tasks, often involving interaction with external APIs (LLMs, databases, web services) or local system resources (files, shell commands). They encapsulate logic, dependencies, and execution instructions within a single Python file.

## 2. Execution

SFAs are executed using `uv run`:

```bash
uv run <agent_filename.py> [arguments...]
```

Ensure `uv` is installed (`pip install uv`).

## 3. Environment Setup

-   **API Keys:** Agents requiring API access rely on environment variables. Set these before running:
    ```bash
    export OPENAI_API_KEY='your-key'
    export ANTHROPIC_API_KEY='your-key'
    export GEMINI_API_KEY='your-key'
    export FIRECRAWL_API_KEY='your-key'
    # Add others as needed
    ```
-   **`.env` Files:** For Gemini agents (and potentially others), `python-dotenv` is used. Create a `.env` file in the repository root to store keys locally (ensure `.env` is in `.gitignore`).

## 4. File Structure & Naming

-   **Single File:** All agent logic resides in one `.py` file.
-   **Naming Convention:** Follow the pattern `sfa_<capability>_<provider>_v<version>.py`.
    -   `<capability>`: e.g., `bash_editor`, `sqlite`, `polars_csv`, `scrapper`.
    -   `<provider>`: e.g., `anthropic`, `gemini`, `openai`.
    -   `<version>`: e.g., `v1`, `v2`, `v3`.

## 5. Dependencies

-   Specify all external dependencies within a `/// script` block at the top of the file.
-   `uv` uses this block to manage a virtual environment for the script.

    ```python
    # /// script
    # dependencies = [
    #   "anthropic>=0.45.2",
    #   "rich>=13.7.0",
    # ]
    # ///
    ```

## 6. Core Components

Each SFA typically includes the following components:

-   **Shebang:** Start the file with `#!/usr/bin/env -S uv run --script` to make it directly executable with `uv`.
-   **Imports:** Import necessary standard library modules and declared dependencies.
-   **Console:** Initialize `rich.console.Console` for styled output and logging:
    ```python
    from rich.console import Console
    console = Console()
    ```
-   **Argument Parsing:** Use the `argparse` module to handle command-line arguments. Common arguments include:
    -   `--prompt` / `-p`: The main user request.
    -   `--compute` / `-c`: Maximum agent loop iterations.
    -   Input specifiers: `--db`, `--input`, etc.
-   **API Client Initialization:** Initialize the required API client (Anthropic, Gemini, OpenAI) using keys sourced from environment variables (`os.getenv`). Include checks and user-friendly error messages if keys are missing.
-   **Agent Prompt (`AGENT_PROMPT`):**
    -   Define a multi-line string constant holding the system prompt.
    *   Use clear sections, often with XML-like tags (e.g., `<purpose>`, `<instructions>`, `<tools_description>`, `<user-request>`).
    *   Include placeholders like `{{user_request}}` or `{{csv_file_path}}` to be replaced at runtime.
    *   Clearly list and describe the available tools and their purpose.
    *   Provide instructions on the expected workflow (e.g., "Start by listing tables...").
-   **Tool Definitions:**
    *   Define the structure and parameters of tools the agent can use. The format depends on the LLM provider:
        *   **Anthropic:** A list of dictionaries, each with `name`, `description`, and `input_schema` (JSON Schema).
        *   **Gemini:** Use `google.genai.types.FunctionDeclaration` for each tool and group them in a `google.genai.types.Tool` object.
        *   **OpenAI:** Define Pydantic models for arguments and use `openai.pydantic_function_tool` to generate the schema list.
    *   Ensure tool descriptions are clear and accurately reflect their function.
    *   Require a `reasoning` parameter in tools where appropriate to encourage the agent to explain its actions.
-   **Tool Implementation:**
    *   Implement each tool as a Python function.
    *   Functions should accept arguments as defined in the schema.
    *   Include robust error handling using `try...except` blocks.
    *   Log tool execution, arguments, results, and errors using `rich` (e.g., `console.log`, `console.print(Panel(...))`).
    *   Handle file paths carefully. If using a placeholder like `/repo`, replace it with `os.getcwd()`.
    *   Return results in the format expected by the agent loop (often strings, sometimes lists or specific structures). Error conditions should be clearly indicated in the return value (e.g., prefixing with "Error:").
-   **Main Agent Loop:**
    *   Control flow is typically a `while` loop limited by `args.compute`.
    *   Maintain conversation history (`messages`) in the format required by the specific LLM API.
    *   **API Call:** Send the current `messages` to the LLM API.
    *   **Response Processing:** Parse the LLM response, extracting any text output and tool call requests. Handle potential errors, blocked responses, or unexpected finish reasons.
    *   **Tool Execution:** If a tool is called:
        *   Identify the function and arguments.
        *   Validate arguments if using Pydantic (OpenAI).
        *   Call the corresponding Python tool function.
        *   Log the call and the result/error.
    *   **History Update:** Append the assistant's response (text/tool calls) and the user/tool results (tool execution output/error) back to the `messages` list before the next iteration.
    *   **Completion:** Implement a mechanism to break the loop when the task is finished (e.g., a `complete_task` tool, a `run_final_...` tool call, or detecting a natural stop from the LLM).

## 7. Documentation

-   **File Docstring:** Include comprehensive usage examples at the beginning of the file docstring.
-   **Tool Docstrings:** Add docstrings to tool implementation functions explaining their purpose, arguments (`Args:`), return value (`Returns:`), and potentially an example. Follow PEP 257 conventions.
-   **Type Hinting:** Use Python type hints for all function signatures (arguments and return types) and important variables.

## 8. Error Handling

-   Wrap tool logic and API calls in `try...except` blocks.
-   Catch specific exceptions where possible, falling back to a general `Exception`.
-   Log errors clearly using `console.print` with `[red]` tags or `Panel`. Include tracebacks (`traceback.format_exc()`) in detailed logs if helpful.
-   Return informative error messages from tools back to the agent loop, often prefixed with "Error:", so the agent can potentially react to the failure.
-   Handle API errors gracefully (e.g., missing keys, rate limits, blocked responses).

## 9. Logging

-   Use `rich.console.Console` for all output.
-   Use `console.log()` for detailed debugging information.
-   Use `console.print()` with `Panel` for visually distinct logging of tool calls, results, errors, and agent thoughts/responses.
-   Use color tags (e.g., `[blue]`, `[green]`, `[red]`, `[yellow]`, `[dim]`) to differentiate log types.

## 10. Specific Agent Patterns

-   **Database Agents (SQLite/DuckDB):**
    -   Common Tool Flow: `list_tables` -> `describe_table` -> `sample_table` -> `run_test_sql_query` -> `run_final_sql_query`.
    -   Execution: DuckDB often uses `subprocess.run('duckdb ...')`. SQLite uses the `sqlite3` standard library module.
-   **Code Execution Agents (Polars):**
    -   Common Tool Flow: `list_columns` -> `sample_csv` -> `run_test_polars_code` -> `run_final_polars_code`.
    -   Execution: Test/Final code is written to a temporary `.py` file and executed using `subprocess.run(['uv', 'run', '--with', 'polars', 'temp_file.py'])`. Remember to clean up the temporary file.
-   **Bash/File Editor Agents:**
    -   Tools typically include `view_file`, `create_file`, `str_replace`, `insert_line`, `execute_bash`.
    -   Path Handling: Be mindful of relative vs. absolute paths. Using a placeholder like `/repo` replaced by `os.getcwd()` is a common pattern.
    -   Bash Execution: Use `subprocess.run(..., shell=True, capture_output=True, text=True)`. Handle `stdout`, `stderr`, and `returncode`.
