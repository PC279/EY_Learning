"""Part 1.1: chat models. Run: python -m part1.p1_models"""
import asyncio

from nimbus.model import get_model

model = get_model()

# 1. invoke: one request, one full reply (an AIMessage)
reply = model.invoke("In one sentence, what is an AI agent?")
print(reply.content)
print(reply.usage_metadata)          # {'input_tokens': ..., 'output_tokens': ..., 'total_tokens': ...}

# 2. stream: the reply arrives in chunks as it is generated
for chunk in model.stream("Name three HR tasks an agent could automate."):
    print(chunk.content, end="", flush=True)
print()

# 3. batch: several independent requests in parallel
replies = model.batch(["Translate 'leave policy' to German.", "Translate 'leave policy' to Hindi."])
print([r.content for r in replies])


# 4. async: the same methods with an 'a' prefix, for web servers
async def main():
    r = await model.ainvoke("Say hello in Kannada.")
    print(r.content)

asyncio.run(main())
