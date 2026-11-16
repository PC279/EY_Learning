"""1.1 Ask a model about Nimbus without and with the policy text.
Run from the project root:  python part1_foundations/01_call_llm.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENROUTER_API_KEY, base_url=config.OPENROUTER_BASE_URL)
question = "How many days of annual leave do employees in India get?"

no_context = client.chat.completions.create(
    model=config.CHAT_MODEL, temperature=0,
    messages=[{"role": "system", "content": "You are Nimbus Corp's HR assistant."},
              {"role": "user", "content": question}],
)
print("WITHOUT the policy:\n", no_context.choices[0].message.content, "\n", no_context.usage)

policy = (config.DATA_DIR / "leave_policy_india.md").read_text(encoding="utf-8")
with_context = client.chat.completions.create(
    model=config.CHAT_MODEL, temperature=0,
    messages=[{"role": "system", "content": "Answer only from the policy text provided."},
              {"role": "user", "content": f"Policy:\n{policy}\n\nQuestion: {question}"}],
)
print("\nWITH the policy:\n", with_context.choices[0].message.content)
