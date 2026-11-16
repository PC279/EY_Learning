"""
agent_service.py: EmployeeLeaveAgent as a service
=================================================

This file is the ONLY place in the project that talks to Microsoft Foundry.
Everything else (the terminal chat, the test script, and later the FastAPI app)
uses the LeaveAgentService class below instead of calling Foundry directly.

Why wrap the agent in a class ("agent as a service")?
- One place to change if the connection details or SDK ever change.
- Every caller gets the same behaviour, e.g. friendly handling of guardrail blocks.
- FastAPI can reuse it as-is in the next step.

How the conversation memory works:
- A Foundry "conversation" stores every message on Microsoft's side.
- We create a conversation once, keep its ID, and pass that ID with every
  question. The agent then remembers what was said earlier in that chat.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv                      # reads settings from the .env file
from azure.identity import DefaultAzureCredential   # signs in using your "az login"
from azure.ai.projects import AIProjectClient       # connects to your Foundry project
from openai import BadRequestError                  # the error raised when a guardrail blocks a message


# Load FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_AGENT_NAME from .env into the environment.
load_dotenv()

# What the user sees when a Foundry guardrail blocks their message or the agent's reply.
GUARDRAIL_MESSAGE = (
    "Sorry, I can't help with that message because it was blocked by our safety "
    "guardrails. Please ask a question about Contoso employee leave."
)


@dataclass
class AgentReply:
    """The result of one question to the agent.

    conversation_id: the Foundry conversation this message belongs to.
                     Send it back with the next question to continue the same chat.
    text:            the agent's answer (or GUARDRAIL_MESSAGE if blocked).
    blocked:         True when a Foundry guardrail blocked the message or reply.
    """
    conversation_id: str
    text: str
    blocked: bool = False


def _is_guardrail_block(error: BadRequestError) -> bool:
    """Return True if a 400 error was caused by a Foundry guardrail.

    When a guardrail blocks the user's input (or the agent's output), Foundry
    answers with HTTP 400 and the error code "content_filter". Any other 400
    error is a real problem (bad request, wrong agent, etc.) and is not hidden.
    """
    # The openai library copies the error code from the response into .code.
    # The string check is a fallback in case the code sits deeper in the body.
    return getattr(error, "code", None) == "content_filter" or "content_filter" in str(error)


class LeaveAgentService:
    """A reusable connection to the EmployeeLeaveAgent in Microsoft Foundry.

    Typical use:
        with LeaveAgentService() as service:
            reply = service.ask("How many casual leave days do I get?")
            print(reply.text)
            reply = service.ask("And sick leave?", reply.conversation_id)   # same chat
    """

    def __init__(self, endpoint: str | None = None, agent_name: str | None = None):
        # Settings: use the values passed in, otherwise read them from .env.
        # os.environ[...] (not getenv) makes the endpoint mandatory: if it's missing
        # we fail immediately with a clear KeyError instead of a confusing error later.
        self.endpoint = endpoint or os.environ["FOUNDRY_PROJECT_ENDPOINT"]
        self.agent_name = agent_name or os.getenv("FOUNDRY_AGENT_NAME", "EmployeeLeaveAgent")

        # Who we are: DefaultAzureCredential uses your "az login" when run locally.
        self._credential = DefaultAzureCredential()

        # Which Foundry project to talk to.
        self._project = AIProjectClient(
            endpoint=self.endpoint,
            credential=self._credential,
            allow_preview=True,   # same setting as the Retail Support Agent project
        )

        # An OpenAI-style client whose replies come from our named agent.
        # The agent's instructions, policy and guardrails all live in Foundry,
        # so nothing about the leave policy is hard-coded here.
        self._client = self._project.get_openai_client(agent_name=self.agent_name)

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------
    def start_conversation(self) -> str:
        """Create a new, empty conversation in Foundry and return its ID."""
        conversation = self._client.conversations.create()
        return conversation.id

    def end_conversation(self, conversation_id: str) -> None:
        """Delete a conversation from Foundry when the chat is finished."""
        self._client.conversations.delete(conversation_id=conversation_id)

    # ------------------------------------------------------------------
    # Asking questions
    # ------------------------------------------------------------------
    def ask(self, message: str, conversation_id: str | None = None) -> AgentReply:
        """Send one message to the agent and return its reply.

        message:         the employee's question.
        conversation_id: pass the ID from an earlier reply to continue that chat,
                         or leave it out to start a brand-new conversation.
        """
        message = message.strip()
        if not message:
            raise ValueError("The message must not be empty.")

        # No conversation yet? Create one, so follow-up questions can reuse it.
        if conversation_id is None:
            conversation_id = self.start_conversation()

        try:
            # Send the message into the conversation. The agent reads its
            # instructions plus all earlier messages in this conversation,
            # then writes its answer.
            response = self._client.responses.create(
                conversation=conversation_id,
                input=message,
            )
        except BadRequestError as error:
            # A guardrail block is expected behaviour, not a crash:
            # return a friendly message instead of raising.
            if _is_guardrail_block(error):
                return AgentReply(conversation_id, GUARDRAIL_MESSAGE, blocked=True)
            raise   # any other error is a real problem, so let it surface

        # output_text joins all the text parts of the reply into one string.
        # "or ''" makes sure we always return a string, never None.
        return AgentReply(conversation_id, response.output_text or "")

    # ------------------------------------------------------------------
    # Cleanup: lets you write "with LeaveAgentService() as service:"
    # so network connections are closed automatically at the end.
    # ------------------------------------------------------------------
    def close(self) -> None:
        self._client.close()
        self._project.close()
        self._credential.close()

    def __enter__(self) -> "LeaveAgentService":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
