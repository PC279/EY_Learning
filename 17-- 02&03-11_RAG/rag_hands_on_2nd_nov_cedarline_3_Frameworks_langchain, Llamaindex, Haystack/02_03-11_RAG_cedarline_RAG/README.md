# Cedarline Systems - Simple Python RAG

A small RAG (Retrieval-Augmented Generation) app built for the
"Hands-on Exercise: Simple Python RAG". It reads two company documents,
stores their chunks in ChromaDB, retrieves matching text and asks an AI
model to answer questions using only that text.

## Project structure

```
cedarline_rag/
├── Documents/
│   ├── Employee_Workplace_Policy.txt
│   └── IT_Help_Desk_Guide.txt
├── chroma_db/                      <- created when you run Task 3 (keep it for submission)
├── config.py                       <- all settings (chunk size, model names, test questions)
├── rag_helpers.py                  <- shared functions: read, tokenize, chunk, embed, store, search
├── ai_client.py                    <- sends question + chunks to Gemini / OpenAI / Claude
├── task1_read_and_tokenize.py      <- Task 1
├── task2_chunk_and_embed.py        <- Task 2
├── task3_store_and_search.py       <- Task 3
├── task4_ai_answer.py              <- Task 4
├── requirements.txt
├── .env.example                    <- copy to .env and paste your API key
└── README.md
```

## Setup (one time)

1. Install Python 3.11 or 3.12 from python.org (tick "Add python.exe to PATH" on Windows).
2. Open this folder in PyCharm: File > Open > select `cedarline_rag`.
3. Create a virtual environment: File > Settings > Project: cedarline_rag >
   Python Interpreter > Add Interpreter > Add Local Interpreter > Virtualenv (New).
4. Open PyCharm's Terminal (bottom bar) and run:
   ```
   pip install -r requirements.txt
   ```
   This takes several minutes the first time (it downloads PyTorch).
5. Get an API key. Free option: Google Gemini at https://aistudio.google.com/apikey
6. Copy `.env.example`, name the copy `.env`, and paste your key:
   ```
   AI_PROVIDER=gemini
   GEMINI_API_KEY=your-real-key
   ```

## Run the tasks (in order)

Right-click each file > Run, or type in the Terminal:

```
python task1_read_and_tokenize.py
python task2_chunk_and_embed.py
python task3_store_and_search.py
python task4_ai_answer.py
```

- Task 2 downloads the all-MiniLM-L6-v2 model (about 90 MB) the first time.
- Task 3 builds the `chroma_db` folder, then asks for a question. Press Enter for the default.
- Task 4 needs Task 3 to have run once. Press Enter to answer all 5 test questions.

## Screenshots for submission

| Screenshot | Take it from |
| --- | --- |
| Chunks | Task 2 output (chunk counts, chunk list, sample chunk, vector size 384) |
| ChromaDB search results | Task 3 output (top 2 chunks with cosine distances) |
| 2 AI answers | Task 4 output (any two answered questions) |

When you submit, include the `chroma_db` folder. Do NOT include `.env` (it has your secret key) or `.venv`.
