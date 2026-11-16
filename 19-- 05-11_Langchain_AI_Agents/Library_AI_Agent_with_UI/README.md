# AI Library Assistant

An AI agent that searches a small library catalogue and reserves books. You talk to it in plain English. The AI model decides which Python tool to run, Python runs it, and the AI explains the result.

It can run two ways:

- **Terminal**: `agent.py`, chat in PyCharm or a terminal.
- **Web app**: a React chat page (`frontend/`) talking to a Python API (`server.py`).

Reservations always need a human "yes" before anything is saved.

For a full explanation of how everything works, with diagrams, read [WHAT_IS_THIS.md](WHAT_IS_THIS.md).

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer (web app only), from [nodejs.org](https://nodejs.org)
- An API key from [OpenRouter](https://openrouter.ai/keys) (free models) or OpenAI

## Setup (once)

1. Open the project folder in PyCharm and create a virtual environment
   (Settings → Project → Python Interpreter → Add Interpreter → Virtualenv).
2. Install the Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Open `.env` and paste your key after `OPENROUTER_API_KEY=` or `OPENAI_API_KEY=`.
4. Check the tools work (free, no API key used):
   ```bash
   python -m unittest test_tools
   ```
   You should see `Ran 8 tests ... OK`.

## Run the terminal version

```bash
python agent.py
```

Type a question, then `exit` to quit. Approve reservations by typing `y`.

## Run the web version

You need two terminals running at the same time.

**Terminal 1: the Python API**

```bash
python server.py
```

Wait for `Uvicorn running on http://127.0.0.1:8000`.

**Terminal 2: the React app**

```bash
cd frontend
npm install      # first time only
npm run dev
```

Open http://localhost:5173 and approve reservations with the **Confirm** button.

Press `Ctrl + C` in each terminal to stop.

## Try these

| Message | Expected tool |
|---|---|
| Find books related to Python programming. | `search_books` |
| Is Python Crash Course available? | `search_books` |
| Reserve Python Crash Course for Ahmed. | `search_books`, then `reserve_book` (asks for approval) |
| Show me books related to artificial intelligence. | `search_books` |
| Reserve Deep Learning for Priya. | `reserve_book`, refused: no copies |

The chosen tool is printed in the terminal as `[AGENT CHOSE TOOL] ...`.

## Project structure

```
Library_AI_Agent/
├── agent.py             Terminal agent: model setup, tool list, agent loop
├── server.py            Web API for the React app (reuses agent.py)
├── tools.py             The two tools: search_books, reserve_book
├── books.json           Book catalogue
├── reservations.json    Saved reservations (starts as [])
├── test_tools.py        Offline tests for tools.py
├── requirements.txt     Python packages
├── .env                 Your API key (never share or commit this)
├── README.md            This file
├── WHAT_IS_THIS.md      Full explanation with diagrams
└── frontend/            React chat app
    ├── index.html
    ├── package.json
    ├── vite.config.js   Forwards /api requests to server.py
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api.js
        ├── styles.css
        └── components/Message.jsx
```

## Choosing a model

| `.env` setting | Model used |
|---|---|
| `OPENROUTER_API_KEY` filled | `openrouter/free`, a free model with tool support |
| Only `OPENAI_API_KEY` filled | `gpt-4o-mini` |
| `MODEL=...` filled | That model, on whichever provider is active |

## Reset the sample data

Set `reservations.json` back to `[]`, and the `available_copies` in `books.json` back to 3, 2, 1, 2, 0, 1, 1 (IDs 101 to 107).

## Troubleshooting

| Problem | Fix |
|---|---|
| `No API key found` | Fill in a key in `.env` and save the file. |
| Chat shows "Can't reach the library server" | Start `server.py` and check terminal 1 for errors. |
| `npm` not found | Install Node.js, then restart PyCharm. |
| "The AI model is busy (rate limit)" | Free models have low limits. Wait a minute, or set `MODEL=` to a specific model. |
| `No endpoints found that support tool use` | Set `MODEL=` to a specific free model that supports tools, or use an OpenAI key. |
| Inconsistent answers | `openrouter/free` may pick a different model each time. Pin one with `MODEL=`. |
