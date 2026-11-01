# InsureEngine

An automated bot that monitors a community forum, detects insurance-related posts (in Hebrew), and replies to them with an AI-generated answer using **RAG** (Retrieval-Augmented Generation) — an answer grounded in relevant information retrieved from a semantic knowledge base, rather than relying solely on the model's general knowledge.

## 🎯 What the project does (product overview)

Community forums (for example, car or housing forums) see a lot of insurance-related questions — car insurance, home insurance, claims, premiums, and so on. **InsureEngine** runs in the background, "reads" every new post, and determines whether it is insurance-related. If it is, the bot:

1. Builds a semantic search query from the post's content.
2. Retrieves relevant information from a knowledge base (embeddings) stored in the database.
3. Runs a language model (GPT) that generates a clear, friendly, and professional answer grounded in the retrieved information.
4. Publishes that answer as a comment on the original post.

The result: forum users get an informed, immediate response to insurance questions, without requiring a human to answer every single one.

## ⚙️ How it works (pipeline)

The bot runs an endless polling loop, checking every 10 seconds:

```
┌──────────────────┐     ┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
│   Post Fetcher    │ ──▶ │ Insurance Filter    │ ──▶ │    RAG Engine       │ ──▶ │ Comment Publisher   │
│ Fetches new posts  │     │ Filters by Hebrew   │     │ Embedding + semantic │     │ Publishes the reply  │
│ from Supabase      │     │ insurance keywords  │     │ search + GPT-4       │     │ back on the post      │
└──────────────────┘     └────────────────────┘     └────────────────────┘     └────────────────────┘
```

1. **Post Fetcher** (`insure_engine/post_fetcher.py`) — fetches new posts from Supabase (or from a local JSON file, depending on configuration) that were published since the last run (or within a configured time window), and saves the timestamp of the latest post seen to `last_seen.txt`, so no post gets processed twice.
2. **Insurance Filter** — out of the fetched posts, keeps only those containing at least one of a curated list of Hebrew insurance-related keywords (e.g. "ביטוח חובה" / mandatory insurance, "פוליסה" / policy, "תביעה" / claim, "השתתפות עצמית" / deductible, "ביטוח מבוסס שימוש" / usage-based insurance, and more).
3. **RAG Engine** (`insure_engine/supabase_rag.py`) —
   - Generates an embedding for the query using OpenAI's embeddings model (`text-embedding-3-small`).
   - Performs a vector similarity search (cosine similarity) against the embeddings table in Postgres/Supabase (pgvector), via an RPC function called `match_embeddings_cosine`.
   - Builds a prompt that combines the retrieved context with the user's question.
   - Sends the prompt to the GPT-4 model with a system prompt that defines a friendly, professional tone, a context-grounded answer, and additional reference links.
4. **Comment Publisher** (`insure_engine/comments.py`) — publishes the RAG-generated answer as a new row in the `comments` table in Supabase, on behalf of the bot's user account (`BOT_USER_ID`).

The whole cycle is orchestrated from `main.py`, which runs a `while True` loop with `time.sleep` between iterations and logs each step and any exceptions via `logging`.

## 🧰 Tech stack

| Component | Technology |
|---|---|
| Language | Python 3 |
| Database | Supabase (Postgres) |
| Semantic search | pgvector + a custom RPC function (`match_embeddings_cosine`) |
| Embeddings model | OpenAI `text-embedding-3-small` |
| Answer generation model | OpenAI `gpt-4` |
| Configuration | `.env` file (`python-dotenv`) + optional `config/config.yaml` (`pyyaml`) |
| Deployment | Render — as a Background Worker |

## 📁 Project structure

```
InsureEngine/
├── main.py                        # Entry point — the main polling loop
├── insure_engine/
│   ├── __init__.py
│   ├── post_fetcher.py            # Fetches and filters posts (Supabase / local JSON)
│   ├── comments.py                # Publishes comments and calls the RAG engine
│   └── supabase_rag.py            # Embedding, semantic search, and answer generation
├── tests/
│   └── __init__.py                # Test scaffolding (currently empty)
├── last_seen.txt                  # Timestamp of the last post processed (runtime state, gitignored)
├── requirements.txt                # Pinned dependencies
├── .env.example                    # Template for the required environment variables
├── .gitignore
└── README.md
```

## 🚀 Installation and running

### Prerequisites

- Python 3.10+
- An active Supabase project, with:
  - A `posts` table (with at least `id`, `title`, `content`, `created_at` columns)
  - A `comments` table (with `id`, `post_id`, `user_id`, `content`, `created_at` columns)
  - An embeddings table with `pgvector` support and an RPC function named `match_embeddings_cosine`
- An OpenAI API key

### Setup steps

1. Clone the repository:
   ```bash
   git clone https://github.com/efrat-stinberg/InsureEngine.git
   cd InsureEngine
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in real values:
   ```bash
   cp .env.example .env
   ```
   - `SUPABASE_URL` / `SUPABASE_ANON_KEY` — required for fetching posts (`post_fetcher.py`).
   - `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` — required for publishing comments (`comments.py`), since write access is needed.
   - `SUPABASE_URL` / `SUPABASE_KEY` — required by the RAG component (`supabase_rag.py`) to perform the semantic-search RPC call.
   - `OPENAI_API_KEY` — the OpenAI API key, used for generating embeddings and answers.
   - `BOT_USER_ID` — the UUID of the bot's user account, used as the author of published comments.

4. (Optional) Create a `config/config.yaml` file to override the Fetcher's default behavior (for example, switching from the Supabase source to a local JSON file source, or changing the time window used to look for new posts). Without such a file, the default configuration defined in `post_fetcher.py` is used.

5. Run the bot:
   ```bash
   python main.py
   ```

   The bot will start its loop, checking for new posts every 10 seconds (`POLL_INTERVAL` in `main.py`), and will publish replies to relevant insurance-related posts.

## ☁️ Deployment

The project is designed to be deployed as a **Background Worker** on [Render](https://render.com/):

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python main.py`
- All the environment variables listed above should be set in the service's Environment settings on Render.

## 🧪 Tests

The `tests/` directory currently exists only as scaffolding (`__init__.py` only, no actual tests yet). It's recommended to add unit tests for the filtering logic (`is_insurance_related`), timestamp loading/saving (`load_last_seen_timestamp`, `save_last_seen_timestamp`), and context prompt construction (`build_context_prompt`).

## 📌 Notes

- The environment variable names for Supabase keys are inconsistent across files (`SUPABASE_ANON_KEY`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`) — each component in the project reads a different variable, so all of them need to be set in `.env`. See `.env.example` for the full list.
- The `config/config.yaml` configuration file referenced in the code (`post_fetcher.py`) does not exist by default in the repo; the project works fine without it, falling back to the default configuration defined in the code.
- `last_seen.txt` is runtime state written by the bot while it runs (not project source), so it is gitignored rather than committed.
