import os
import yaml
import logging
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv  # For loading .env files

# Agno core components
from agno.agent import Agent
# Model imports are now handled conditionally below based on provider

# Project-specific components
from client import AgentMailToolkit
from storage import get_storage_handler

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Loads configuration from YAML file and environment variables."""
    config = {}
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
    except FileNotFoundError:
        logger.warning(f"Configuration file {config_path} not found. Relying on environment variables.")
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file {config_path}: {e}")
        raise

    # Allow environment variables to override YAML config
    # AgentMail Config
    config.setdefault("agentmail", {})
    config["agentmail"]["api_key"] = os.getenv("AGENTMAIL_API_KEY", config["agentmail"].get("api_key"))
    config["agentmail"]["inbox_id"] = os.getenv("INBOX_ID", config["agentmail"].get("inbox_id"))
    config["agentmail"]["webhook_url"] = os.getenv("WEBHOOK_URL", config["agentmail"].get("webhook_url"))

    # Agno Config
    config.setdefault("agno", {})
    config["agno"]["model"] = os.getenv("AGNO_MODEL_PROVIDER", config["agno"].get("model", "openai")) # Default to openai if not set
    config["agno"]["model_name"] = os.getenv("AGNO_MODEL_NAME", config["agno"].get("model_name"))
    # API keys often handled by model libraries directly via env vars (OPENAI_API_KEY, GOOGLE_API_KEY, etc.)
    # but we can load it if specified explicitly
    config["agno"]["api_key"] = os.getenv(f"{config['agno']['model'].upper()}_API_KEY", config["agno"].get("api_key"))

    # Storage Config
    config.setdefault("storage", {})
    config["storage"]["db_path"] = os.getenv("STORAGE_DB_PATH", config["storage"].get("db_path", "agno_agentmail_state.db"))

    # Basic validation
    if not config.get("agentmail", {}).get("api_key") or config["agentmail"]["api_key"] == "YOUR_AGENTMAIL_API_KEY":
        logger.warning("AgentMail API key is not configured. Toolkit initialization might fail or use dummy values.")
    if not config.get("agentmail", {}).get("inbox_id") or config["agentmail"]["inbox_id"] == "YOUR_INBOX_ID":
        logger.warning("AgentMail Inbox ID is not configured. Toolkit initialization might fail or use dummy values.")
    if not config.get("agno", {}).get("model_name"):
        logger.warning("Agno model name is not configured. Agent initialization might fail.")

    return config

async def main():
    """Main execution function for the Email Agent."""
    logger.info("Starting Agno Email Agent...")

    # Load environment variables from .env file
    load_dotenv()

    # 1. Load Configuration
    config = load_config()

    # 2. Initialize Components
    try:
        agentmail_config = config.get("agentmail", {})
        storage_config = config.get("storage", {})
        agno_config = config.get("agno", {})

        toolkit = AgentMailToolkit(
            api_key=agentmail_config.get("api_key", "DUMMY_KEY"), # Provide dummy if missing for init
            inbox_id=agentmail_config.get("inbox_id", "DUMMY_INBOX") # Provide dummy if missing for init
        )
        storage = get_storage_handler(db_path=storage_config.get("db_path", "agno_agentmail_state.db"))

        # Define tools based on toolkit methods

        # 3. Initialize Agno Agent
        model_provider = agno_config.get("model")
        model_name = agno_config.get("model_name")
        api_key = agno_config.get("api_key") # May be None if handled by env var

        if not model_provider or not model_name:
             raise ValueError("Agno model provider and model name must be configured in config.yaml or environment variables.")

        logger.info(f"Initializing Agno Agent with model: {model_provider}/{model_name}")

        # Directly import and assign the model class based on provider
        if model_provider == "openai":
            from agno.models.openai import OpenAIChat
            model_cls = OpenAIChat
        elif model_provider == "anthropic":
            from agno.models.anthropic import Claude
            model_cls = Claude
        elif model_provider == "groq":
            from agno.models.groq import Groq
            model_cls = Groq
        elif model_provider == "google":
            from agno.models.google import Gemini
            model_cls = Gemini
        else:
            raise ValueError(f"Unsupported model provider specified: {model_provider}")

        # Prepare model arguments
        model_args = {"id": model_name}
        if api_key:
            model_args["api_key"] = api_key

        model_instance = model_cls(**model_args)

        # Prepare model arguments (handle potential API key)
        model_args = {"model": model_name}
        if api_key:
            model_args["api_key"] = api_key
        # Add other potential model args from config if needed

        model_instance = model_cls(**model_args)

        # Define system prompt/instructions for the agent
        system_prompt = """
        You are an AI assistant designed to manage emails via the AgentMail API.
        Use the available tools to list inboxes, get messages, send new emails, and reply to existing ones.
        Process incoming requests and respond appropriately based on the email content.
        Keep track of processed messages using the state storage.
        Be concise and professional in your email communications.
        """
        # TODO: Refine system prompt based on specific agent tasks

        agent = Agent(
            model=model_instance,
            storage=storage,
            tools=toolkit,
            system_prompt=system_prompt,
            # session_id="default_email_agent_session" # Optional: Define a default session ID
        )
        logger.info("Agno Agent initialized successfully.")

        # 4. Agent Execution Logic (Placeholder)
        logger.info("Agent setup complete. Starting main loop (placeholder)...")
        # TODO: Implement the core agent logic here.
        # This could involve:
        # - Starting a web server to listen for AgentMail webhooks.
        # - Periodically polling for new messages using toolkit.get_messages().
        # - Processing messages using agent.run().
        # - Storing processed message IDs in the state.

        # Example placeholder loop (replace with actual logic)
        print("\n--- Agent Ready ---")
        print("Placeholder: Agent would now enter its main operational loop.")
        print("e.g., listening for webhooks or polling for emails.")
        # Keep running indefinitely for a server/poller
        # await asyncio.Event().wait() # Uncomment to keep running

        # Example: Run a single interaction for testing
        # response = await agent.run("Check for new emails and summarize the first unread one.")
        # print(f"Agent Response: {response}")


    except ValueError as ve:
        logger.error(f"Configuration Error: {ve}")
    except ImportError as ie:
        logger.error(f"Import Error: {ie}. Make sure all dependencies are installed (`uv pip install -r requirements.txt`)")
    except Exception as e:
        logger.error(f"An unexpected error occurred during agent initialization or execution: {e}", exc_info=True)

if __name__ == "__main__":
    # Use asyncio.run() to execute the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agent stopped manually.")
    except Exception as e:
        logger.critical(f"Agent failed to run: {e}", exc_info=True)