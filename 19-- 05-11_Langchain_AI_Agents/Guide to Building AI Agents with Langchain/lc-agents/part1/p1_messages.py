"""Part 1.2: messages. Run: python -m part1.p1_messages"""
from langchain.messages import AIMessage, HumanMessage, SystemMessage

from nimbus.model import get_model

model = get_model()

conversation = [
    SystemMessage("You are a concise HR assistant for Nimbus Corp."),
    HumanMessage("I'm Priya, I work in the Bengaluru office."),
    AIMessage("Hi Priya, how can I help?"),
    HumanMessage("Which office did I say I work in?"),
]
print(model.invoke(conversation).content)        # the model only "remembers" what you send

# The same thing with plain dicts (OpenAI style) - LangChain accepts both
print(model.invoke([{"role": "user", "content": "Reply with the single word: ready"}]).content)

# Standard content blocks: provider-independent view of what came back
reply = model.invoke("What is 2 + 2? Answer briefly.")
for block in reply.content_blocks:               # e.g. {'type': 'text', 'text': '4'} or reasoning blocks
    print(block["type"], "->", str(block)[:80])
