import os
import logging
import yaml
from agno.storage.sqlite import SqliteStorage

logger = logging.getLogger(__name__)

def get_storage_handler(db_path: str) -> SqliteStorage:
    """
    Initializes and returns the Agno SqliteStorage handler.

    Configures SqliteStorage to use the specified database file path.

    Args:
        db_path: The path to the SQLite database file.

    Returns:
        An initialized SqliteStorage instance.
    """
    if not db_path:
        raise ValueError("Database path for storage is required.")

    logger.info(f"Initializing SqliteStorage at: {db_path}")
    try:
        storage_handler = SqliteStorage(table_name="agent_sessions", db_file=db_path)
        logger.info("SqliteStorage initialized successfully.")
        return storage_handler
    except Exception as e:
        logger.error(f"Failed to initialize SqliteStorage: {e}")
        raise

# Example usage (for testing purposes)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Load configuration (replace with actual config loading logic if needed elsewhere)
    try:
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        db_path_from_config = config.get("storage", {}).get("db_path", "default_agent_state.db")

        print(f"\n--- Testing Storage Initialization (DB Path: {db_path_from_config}) ---")
        storage = get_storage_handler(db_path=db_path_from_config)
        print(f"Storage Handler Type: {type(storage)}")
        # SqliteStorage does not have an 'adapter' attribute

        # Example: Test storing and retrieving a simple session (optional)
        session_id = "test_session_123"
        print(f"\n--- Testing basic storage operations (Session ID: {session_id}) ---")

        # Helper to check if a session exists
        def session_exists(storage, session_id):
            try:
                return storage.load(session_id) is not None
            except Exception:
                return False

        try:
            # Clear previous test data if any
            if session_exists(storage, session_id):
                print(f"Deleting existing test session: {session_id}")
                storage.delete(session_id)

            print("Saving initial state...")
            storage.save(session_id, {"history": [{"role": "user", "content": "Hello"}]})
            print("State saved.")

            print("Loading state...")
            loaded_state = storage.load(session_id)
            print(f"Loaded state: {loaded_state}")

            print("Updating state...")
            loaded_state["history"].append({"role": "assistant", "content": "Hi there!"})
            storage.save(session_id, loaded_state)
            print("State updated.")

            print("Loading updated state...")
            updated_state = storage.load(session_id)
            print(f"Updated state: {updated_state}")

            print("Checking if session exists...")
            exists = session_exists(storage, session_id)
            print(f"Session exists: {exists}")

            print("Deleting session...")
            storage.delete(session_id)
            print("Session deleted.")

            print("Checking if session exists after deletion...")
            exists_after_delete = session_exists(storage, session_id)
            print(f"Session exists: {exists_after_delete}")

        except Exception as e:
            print(f"An error occurred during storage operations test: {e}")

    except FileNotFoundError:
        print("Error: config.yaml not found. Cannot determine DB path.")
    except Exception as e:
        print(f"An error occurred during testing: {e}")