# InsureEngine

An automated bot that monitors a community forum for insurance-related posts and replies with AI-generated answers using RAG (Retrieval-Augmented Generation).

## How It Works

1. **Post Fetcher** — Polls Supabase for new posts every 10 seconds
2. **Insurance Filter** — Filters posts by Hebrew insurance keywords (ביטוח, פוליסה, תביעה, etc.)
3. **RAG Engine** — Generates a relevant answer using OpenAI embeddings + Supabase pgvector semantic search
4. **Comment Publisher** — Posts the generated answer as a comment on the original post

## Project Structure

```
insure-engine/
├── main.py                        # Entry point — polling loop
├── insure_engine/
│   ├── post_fetcher.py            # Fetches & filters new posts
│   ├── comments.py                # Handles RAG call & publishes replies
│   └── supabase_rag.py            # Semantic search & answer generation
├── .env                           # API keys (not committed)
├── last_seen.txt                  # Tracks last processed post timestamp
├── requirements.txt
└── tests/
```

## Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/efrat-stinberg/InsureEngine.git
   cd InsureEngine
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with the following keys:
   ```
   SUPABASE_URL=
   SUPABASE_ANON_KEY=
   SUPABASE_SERVICE_ROLE_KEY=
   SUPABASE_KEY=
   OPENAI_API_KEY=
   BOT_USER_ID=
   ```

4. Run:
   ```bash
   python main.py
   ```

## Deployment (Render)

Deploy as a **Background Worker** on Render:

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python main.py`
- Add all `.env` variables in Render's Environment settings

## Tech Stack

- **Supabase** — Database (posts, comments) + pgvector for embeddings
- **OpenAI** — Embeddings (`text-embedding-3-small`) + GPT-4 for answer generation
- **Python** — Runtime
