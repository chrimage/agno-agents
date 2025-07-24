import os
import logging
from typing import List, Dict, Any, Optional

from agentmail import AgentMail
from agentmail.core.api_error import ApiError

logger = logging.getLogger(__name__)

class AgentMailToolkit:
    """
    A toolkit for interacting with the AgentMail API.

    Wraps the agentmail SDK to provide methods for managing
    email inboxes and messages within the Agno framework.
    """
    def __init__(self, api_key: str, inbox_id: str):
        """
        Initializes the AgentMailToolkit.

        Args:
            api_key: The API key for AgentMail authentication.
            inbox_id: The default inbox ID to operate on.
        """
        if not api_key:
            raise ValueError("AgentMail API key is required.")
        if not inbox_id:
            raise ValueError("AgentMail Inbox ID is required.")

        self.api_key = api_key
        self.inbox_id = inbox_id
        self.client = self._initialize_client()

    def _initialize_client(self) -> Any:
        """
        Initializes and returns the AgentMail SDK client instance.
        Handles authentication.
        """
        logger.info("Initializing AgentMail client...")
        try:
            client = AgentMail(api_key=self.api_key)
            logger.info("AgentMail client initialized successfully.")
            return client
        except Exception as e:
            logger.error(f"Failed to initialize AgentMail client: {e}")
            raise

    def list_inboxes(self, limit: Optional[int] = None, last_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists available inboxes.

        Args:
            limit: Optional; maximum number of inboxes to return.
            last_key: Optional; key of the last item for pagination.

        Returns:
            A list of inbox objects.
        """
        logger.info("Listing AgentMail inboxes...")
        try:
            inboxes = self.client.inboxes.list(
                limit=limit,
                last_key=last_key
            )
            return inboxes
        except ApiError as e:
            logger.error(f"AgentMail API error while listing inboxes: {e.status_code} {e.body}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while listing inboxes: {e}")
            raise

    def get_messages(
        self,
        inbox_id: Optional[str] = None,
        limit: Optional[int] = None,
        last_key: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves messages from the specified inbox.

        Args:
            inbox_id: The ID of the inbox to retrieve messages from. Defaults to self.inbox_id if not provided.
            limit: Optional; maximum number of messages to retrieve.
            last_key: Optional; key of the last item for pagination.
            labels: Optional; list of labels to filter messages by.

        Returns:
            A list of message objects.
        """
        if inbox_id is None:
            inbox_id = self.inbox_id
        logger.info(f"Getting messages for inbox {inbox_id} (limit={limit}, last_key={last_key}, labels={labels})...")
        try:
            messages = self.client.messages.list(
                inbox_id=inbox_id,
                limit=limit,
                last_key=last_key,
                labels=labels
            )
            return messages
        except ApiError as e:
            logger.error(f"AgentMail API error while getting messages: {e.status_code} {e.body}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while getting messages: {e}")
            raise

    def send_message(
        self,
        to: List[str],
        subject: str,
        text: Optional[str] = None,
        html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Sends an email message from the configured inbox.

        Args:
            to: List of recipient email addresses.
            subject: Email subject line.
            text: Optional; plain text body of the email.
            html: Optional; HTML body of the email.
            cc: Optional; list of CC recipient email addresses.
            bcc: Optional; list of BCC recipient email addresses.

        Returns:
            The sent message object or None if failed.
        """
        logger.info(f"Sending message from inbox {self.inbox_id} to {to}...")
        try:
            result = self.client.messages.send(
                inbox_id=self.inbox_id,
                to=to,
                cc=cc,
                bcc=bcc,
                subject=subject,
                text=text,
                html=html
            )
            return result
        except ApiError as e:
            logger.error(f"AgentMail API error while sending message: {e.status_code} {e.body}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while sending message: {e}")
            raise

    def reply(
        self,
        message_id: str,
        text: Optional[str] = None,
        html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Replies to a specific email message.

        Args:
            message_id: The ID of the message to reply to.
            text: Optional; plain text body of the reply.
            html: Optional; HTML body of the reply.
            cc: Optional; list of CC recipient email addresses.
            bcc: Optional; list of BCC recipient email addresses.

        Returns:
            The reply message object or None if failed.
        """
        logger.info(f"Replying to message {message_id} in inbox {self.inbox_id}...")
        try:
            result = self.client.messages.reply(
                inbox_id=self.inbox_id,
                message_id=message_id,
                text=text,
                html=html,
                cc=cc,
                bcc=bcc
            )
            return result
        except ApiError as e:
            logger.error(f"AgentMail API error while replying to message: {e.status_code} {e.body}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while replying to message: {e}")
            raise

# Example usage (for testing purposes)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Load configuration (replace with actual config loading logic)
    import yaml
    try:
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        api_key = os.getenv("AGENTMAIL_API_KEY", config.get("agentmail", {}).get("api_key"))
        inbox_id = os.getenv("INBOX_ID", config.get("agentmail", {}).get("inbox_id"))

        if not api_key or api_key == "YOUR_AGENTMAIL_API_KEY":
            print("Warning: AgentMail API key not configured in config.yaml or environment variable AGENTMAIL_API_KEY.")
            api_key = "DUMMY_KEY" # Use dummy for placeholder testing
        if not inbox_id or inbox_id == "YOUR_INBOX_ID":
            print("Warning: AgentMail Inbox ID not configured in config.yaml or environment variable INBOX_ID.")
            inbox_id = "DUMMY_INBOX" # Use dummy for placeholder testing

        toolkit = AgentMailToolkit(api_key=api_key, inbox_id=inbox_id)

        print("\n--- Testing list_inboxes ---")
        inboxes = toolkit.list_inboxes()
        print(f"Inboxes: {inboxes}")

        print("\n--- Testing get_messages ---")
        messages = toolkit.get_messages(limit=5)
        print(f"Messages: {messages}")

        print("\n--- Testing send_message ---")
        sent = toolkit.send_message(to=["test@example.com"], subject="Test Email", text="Hello from Agno!")
        print(f"Sent message result: {sent}")

        print("\n--- Testing reply ---")
        replied = toolkit.reply(message_id="some_message_id", text="This is a reply.")
        print(f"Reply result: {replied}")

    except FileNotFoundError:
        print("Error: config.yaml not found. Please create it based on the template.")
    except Exception as e:
        print(f"An error occurred during testing: {e}")