# FinGenius — AI Personal Finance & Expense Intelligence Assistant

FinGenius is a working college AI-agent project: it stores transactions in SQLite, calculates financial insights in Python/Pandas, retrieves finance knowledge through local Sentence Transformer embeddings and FAISS, and coordinates AI responses through a conditional LangGraph workflow.

> It provides educational financial guidance only—not investment, tax, legal, or professional financial advice.

## Run locally

```bash
cd FinGenius
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
python3 -m pip install -r requirements.txt
cp .env.example .env
# add GEMINI_API_KEY or CLAUDE_API_KEY and configure LLM_PROVIDER / LLM_MODEL
python3 -m streamlit run app.py
```

Open `http://localhost:8501`. The first model download (Sentence Transformer) may take a few minutes.

## Deploy on Render

Push the complete folder to GitHub. In Render set the Root Directory to `FinGenius`, Build Command to `pip install -r requirements.txt`, and Start Command to:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

Add `GEMINI_API_KEY`, `LLM_PROVIDER`, and `LLM_MODEL` as Render environment variables. Do **not** use `uvicorn`; this is a Streamlit app. `render.yaml` contains the same configuration.

## Architecture

```text
Streamlit dashboard
 ├─ Expense Manager ──> validated SQLite expenses / budgets
 ├─ Analytics ────────> Pandas totals, trends, category and budget calculations ──> Plotly
 ├─ Knowledge Base ───> PDFs → PyPDF → chunks → MiniLM embeddings → FAISS
 └─ AI Advisor ───────> LangGraph intent router
                         ├─ expense management (parse; user confirms save)
                         ├─ financial calculation (programmatic evidence)
                         ├─ RAG retrieval (knowledge evidence)
                         └─ recommendation (actual spending evidence) → Gemini/Claude response
```

## Demonstrable tools

`tools/finance_tools.py` has working functions for `add_expense`, `update_expense`, `delete_expense`, `calculate_total_expenses`, `analyze_category_spending`, `generate_monthly_report`, `calculate_budget_usage`, `retrieve_financial_knowledge`, and `generate_savings_recommendations`.

- Natural-language entries such as “I spent 250 rupees on lunch” are parsed with a deterministic amount/category extractor and require confirmation before saving.
- SQLite prevents exact duplicate transaction records.
- The edit/delete interface requires confirmation before a destructive delete.
- Totals and category figures come from Pandas/SQLite, never the LLM.

## RAG, embeddings and FAISS

The Knowledge Base contains an embedded financial-literacy guide and accepts uploaded educational PDFs. PyPDF extracts page text, which is split into overlapping chunks. `all-MiniLM-L6-v2` converts chunks and questions into semantic vectors. FAISS indexes and retrieves nearest passages, which are then presented to the LLM as its evidence. This is genuine retrieval, not hardcoded Q&A.

## LangGraph workflow

`graph/workflow.py` defines these nodes: User Input → Intent Classification → Expense Management / Financial Calculation / RAG Retrieval / AI Recommendation → Response Generation. Conditional edges select the correct node. The shared state carries the query, intent, knowledge store, evidence, and final answer.

## Quick test workflow

1. Add expenses manually: Food ₹250, Travel ₹100, Entertainment ₹500.
2. Add a budget limit for Food; inspect the budget alert on Overview.
3. Use natural-language entry and confirm before saving.
4. Ask the Advisor “Where am I spending the most?”; verify it matches Overview.
5. Ask “How can I reduce my spending?”; it uses calculated category evidence.
6. Ask “What is the 50/30/20 rule?” in Knowledge Base and inspect retrieved text.
7. Upload a finance PDF, index it, then ask a question about it.

## 15 viva questions with answers

1. **What makes it an AI agent?** LangGraph routes intents to specialized retrieval, calculation, expense, and recommendation tools.
2. **Why SQLite?** It persists validated transactions locally without an external database server.
3. **Why Pandas?** It reliably calculates totals, date aggregates, and category spending from real rows.
4. **Why not let the LLM calculate?** Programmatic calculations prevent invented financial figures.
5. **What is RAG?** Retrieving relevant documents and passing them as evidence to an LLM.
6. **What is an embedding?** A numeric semantic representation of text.
7. **Why Sentence Transformers?** They produce local semantic vectors for similarity search.
8. **Why FAISS?** It efficiently locates the most similar vectors/chunks.
9. **How is PDF provenance retained?** Every extraction includes the uploaded filename and page label.
10. **What is chunk overlap for?** It preserves context across chunk boundaries.
11. **What is LangGraph state?** The shared structured data passed between workflow nodes.
12. **How does conditional routing work?** Intent classification chooses a matching specialist node.
13. **How is destructive action protected?** Delete buttons require explicit UI confirmation.
14. **How are keys protected?** They stay in `.env` or host environment variables, not source code.
15. **Normal tracker vs AI agent?** A tracker records entries; this agent routes requests, performs tool-backed analysis, retrieves knowledge, and explains evidence.

## Three-minute live demo script

“FinGenius is an AI personal-finance agent rather than only an expense tracker. I first add transactions; they persist in SQLite. The Overview uses Pandas to calculate my actual monthly total, category breakdown, daily average, and budget use, then Plotly visualizes it. Natural-language entry extracts an amount and category but waits for confirmation, keeping the user in control. Next I ask the AI Advisor where I spend most. LangGraph classifies this as a calculation, calls the financial-calculation node, creates evidence from real SQLite data, and sends that evidence to Gemini or Claude. For a literacy question, the graph selects RAG retrieval: PDF text is chunked, embedded by MiniLM, indexed in FAISS, and relevant chunks are provided to the model. Thus the app demonstrates persistence, tool calling, RAG, embeddings, FAISS, LangGraph orchestration, and a polished finance dashboard.”
