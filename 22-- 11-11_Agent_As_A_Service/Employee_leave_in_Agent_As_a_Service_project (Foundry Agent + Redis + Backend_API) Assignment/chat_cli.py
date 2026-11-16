"""
chat_cli.py: chat with EmployeeLeaveAgent from the PyCharm terminal
===================================================================

Run it:  python chat_cli.py      (or right-click the file in PyCharm > Run)

Commands while chatting:
  new   -> start a fresh conversation (the agent forgets the earlier chat)
  exit  -> quit (also: quit, or Ctrl+C)
"""

from agent_service import LeaveAgentService


def main() -> None:
    print("Connecting to EmployeeLeaveAgent...")

    # "with" closes the connection to Foundry automatically when we leave the block.
    with LeaveAgentService() as service:
        # One conversation = one chat with memory. Create it up front.
        conversation_id = service.start_conversation()
        print(f"Connected to '{service.agent_name}'. Conversation: {conversation_id}")
        print("Ask a leave question. Type 'new' for a fresh chat, 'exit' to quit.\n")

        try:
            while True:
                question = input("You: ").strip()

                # Skip empty lines instead of sending them to the agent.
                if not question:
                    continue

                # Quit the loop.
                if question.lower() in ("exit", "quit"):
                    break

                # Start over: delete the old conversation and create a new one.
                if question.lower() == "new":
                    service.end_conversation(conversation_id)
                    conversation_id = service.start_conversation()
                    print(f"(Started a new conversation: {conversation_id})\n")
                    continue

                # Send the question into the SAME conversation, so the agent
                # remembers earlier messages in this chat.
                reply = service.ask(question, conversation_id)

                # Mark replies that a Foundry guardrail blocked.
                label = "Agent [blocked by guardrail]" if reply.blocked else "Agent"
                print(f"{label}: {reply.text}\n")

        except (KeyboardInterrupt, EOFError):
            # Ctrl+C or end of input: leave quietly instead of showing a traceback.
            print()

        finally:
            # Tidy up: remove this chat's conversation from Foundry.
            try:
                service.end_conversation(conversation_id)
            except Exception:
                pass   # not important if cleanup fails (e.g. no network)
            print("Goodbye!")


# Only run main() when this file is started directly (not when imported).
if __name__ == "__main__":
    main()
