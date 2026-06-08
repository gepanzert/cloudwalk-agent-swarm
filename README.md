# InfinitePay Agent Swarm

A multi-agent customer support system built for CloudWalk's AI Engineer challenge. The system routes customer queries through specialized AI agents, combining RAG over InfinitePay's product knowledge base, real-time web search, customer account tools, sentiment detection, and human escalation via Slack.

**Live demo:** https://cloudwalk-agent-swarm.vercel.app  
**API:** https://cloudwalk-agent-swarm-production.up.railway.app/docs  
**Repository:** https://github.com/gepanzert/cloudwalk-agent-swarm

---

## Architecture

The brief provided a reference architecture: Input → Router → Agents → Personality → Output. This implementation uses that as a foundation and extends it with two pre-router layers that address real production concerns.

![Agent Swarm Architecture](docs/architecture.png)

```
User Message
     │
     ▼
┌─────────────┐
│  Guardrail  │ ← blocks jailbreaks, prompt injection, obfuscated attacks
└──────┬──────┘
       │ blocked → END
       ▼
┌─────────────┐
│  Sentiment  │ ← detects urgency/distress → short-circuits to Handoff
└──────┬──────┘
       │ urgent/distressed → Handoff
       ▼
┌─────────────┐
│   Router    │ ← classifies: knowledge vs support
└──────┬──────┘
       │
   ┌───┴────┐
   ▼        ▼
Knowledge  Support ──→ Handoff
   │        │
   ▼        ▼
Proactive  (insight)
   │        │
   └───┬────┘
       ▼
  Personality
       │
       ▼
   Response
```

**Why two layers before the Router:** the Guardrail and Sentiment layers are pre-processing — one handles safety, one handles urgency. Neither replaces the Router's job. An urgent customer still hits the Router if sentiment is normal; a blocked input never reaches the Router at all. Placing these before the Router reflects a principle: in a fintech handling real money, safety and urgency are not features — they are infrastructure.

### Agents

| Agent | Model | Role |
|---|---|---|
| Guardrail | claude-haiku-4-5 | Input/output safety. Blocks jailbreaks, prompt injection, and obfuscated attacks (morse, binary, base64, leetspeak, reversed text) — without explicit rules for each encoding |
| Sentiment | claude-haiku-4-5 | Classifies tone (normal/frustrated/urgent/distressed), sets priority, short-circuits critical cases directly to Handoff |
| Router | claude-haiku-4-5 | Intent classification — knowledge vs support. Single-word output, max_tokens=10. Defaults to knowledge for nonsensical or unclassifiable input |
| Knowledge | claude-sonnet-4-6 | RAG over InfinitePay knowledge base + Tavily web search fallback. Tiered fee display, source citations, language detection |
| Support | claude-sonnet-4-6 | Account tools + user data lookup. Resolves issues without tickets when possible; escalates only when the issue genuinely requires human intervention |
| Handoff | — | Slack escalation with structured priority cards and ticket IDs. Calls Summarization Agent for structured 5-bullet context before posting |
| Proactive Insights | claude-haiku-4-5 | Post-support account analysis. Surfaces one relevant insight the user didn't ask about — only for non-urgent cases, only when topically relevant to the user's question |
| Personality | claude-haiku-4-5 | Post-processing tone layer applied to Knowledge and Support responses. Skipped for Guardrail blocks and Handoff responses, which require precise structured output |

### Model tier strategy

Haiku handles classification and post-processing tasks (Router, Guardrail, Sentiment, Proactive Insights, Personality) — fast, cost-efficient, and sufficient for constrained outputs. Sonnet handles generation tasks (Knowledge, Support) — stronger reasoning, better Portuguese, better tool use. This reduces API cost by ~70% compared to using Sonnet throughout.

### Communication pattern

LangGraph `StateGraph` with shared `AgentState`. Every node reads from and writes to the same state object — messages, user_id, sentiment, priority, agent_used, final_response. `MemorySaver` checkpointer enables conversation memory across turns via `thread_id`.

---

## RAG Pipeline

**Data sources:** 17 pages from infinitepay.io — maquininha, tap-to-pay, pix, pix-parcelado, conta digital, conta-pj, empréstimo, cartão, rendimento, link de pagamento, loja online, boleto, PDV, gestão de cobrança, receba na hora, and the homepage.

**Pipeline:**

1. **Scrape** — `WebBaseLoader` fetches each URL, tags each chunk with its source URL for citations
2. **Chunk** — `RecursiveCharacterTextSplitter` at 1,000 chars with 200-char overlap (332 chunks total)
3. **Embed** — Voyage AI `voyage-3-large` (1,024 dimensions) — Anthropic's recommended embedding partner
4. **Store** — ChromaDB persisted to disk at `data/chroma_db/`, loaded as a singleton on startup
5. **Retrieve** — cosine similarity search, top-4 chunks per query
6. **Generate** — Claude Sonnet with retrieved context + source citations in response

**Fallback:** when the knowledge base has no relevant results, the Knowledge Agent falls back to Tavily web search for general queries (sports, news, weather). Real-time results include an explicit disclaimer about data freshness.

**Why Voyage AI:** consistent with using Anthropic's stack throughout. `voyage-3-large` is optimized for retrieval tasks and produces better semantic similarity than general-purpose embeddings for domain-specific content.

---

## API

**Base URL:** `https://cloudwalk-agent-swarm-production.up.railway.app`

### POST /chat

```json
{
  "message": "What are the fees of the Maquininha Smart?",
  "user_id": "client789",
  "thread_id": "optional-for-conversation-continuity"
}
```

**Response:**
```json
{
  "response": "Here are the fees for the Maquininha Smart...",
  "user_id": "client789",
  "agent_used": "knowledge",
  "thread_id": "thread_abc123",
  "sentiment": "normal",
  "priority": "low",
  "escalated": false
}
```

**Interactive docs:** `https://cloudwalk-agent-swarm-production.up.railway.app/docs`

### Mock users for testing

The Support Agent uses a seeded SQLite database with 5 mock users to simulate different account states. In production, `user_id` would come from InfinitePay's authentication system automatically.

| user_id | Account state | Use case |
|---|---|---|
| `client789` | Active, KYC approved, Smart plan | Happy path — normal support queries |
| `user_blocked` | Blocked | Account blocked scenario |
| `user_kyc_pending` | KYC pending | Onboarding incomplete scenario |
| `user_limit_reached` | Active, daily limit R$5,000 exhausted | Transfer failure scenario |
| `user_login_issue` | Suspended | Login failure + ticket creation scenario |

---

## Quick Start

### Prerequisites

- Python 3.11
- Docker + Docker Compose
- API keys: Anthropic, Voyage AI, Tavily, LangSmith, Slack webhook (optional)

### Run with Docker

```bash
git clone https://github.com/gepanzert/cloudwalk-agent-swarm.git
cd cloudwalk-agent-swarm

cp .env.example .env
# Fill in your API keys in .env

docker compose up --build
```

The startup script automatically:
1. Seeds the mock user database (if not present)
2. Runs the RAG ingestion pipeline in background on first run (~5 min)
3. Starts the API immediately — no waiting for ingestion

**API:** `http://localhost:8000`  
**Swagger UI:** `http://localhost:8000/docs`

**Note on first run:** Knowledge Agent queries return "knowledge base initializing" until ingestion completes (~5 minutes). The API responds immediately — this is intentional so Railway's health check doesn't time out during ingestion.

### Run locally (development)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# First time only
python -m ingestion.scrape
python scripts/seed_users.py

uvicorn app.api.main:app --reload --port 8000
```

---

## Testing

### Testing strategy

The project has three layers of testing, each serving a different purpose:

**Unit tests** (`tests/test_unit.py`) use mocks to test agent logic without API calls. 27 tests covering Router, Guardrail, Sentiment, UserDB, Handoff, and Personality agents. Run in under 1 second, zero API cost. Designed to run on every commit.

```bash
pytest tests/test_unit.py -v
# 27 passed in 0.97s — zero API calls
```

**Integration tests** (`tests/test_api.py`, `tests/test_tools.py`) exercise the full system against real APIs. 33 tests covering endpoints, routing, tool calls, RAG retrieval, and guardrail behavior. Run before deployment.

```bash
pytest tests/ -v
# 60 passed in ~2m30s
```

**Eval harness** (`evals/run_evals.py`) uses Claude as an LLM-as-judge to score response quality across 15 queries. Measures routing accuracy, factual accuracy, and topic coverage. Run periodically to detect regressions.

```bash
python evals/run_evals.py
```

The separation between unit and integration tests reflects a production principle: unit tests run on every commit without API cost; integration tests run before deployment; the eval harness runs periodically to monitor response quality regression.

### Eval results

| Query | Expected | Result | Score |
|---|---|---|---|
| Maquininha Smart fees | knowledge | ✅ knowledge | 5.0/5 |
| Maquininha Smart cost | knowledge | ✅ knowledge | 5.0/5 |
| Debit/credit rates | knowledge | ✅ knowledge | 5.0/5 |
| Phone as card machine | knowledge | ✅ knowledge | 4.7/5 |
| Palmeiras last game | knowledge | ✅ knowledge | 3.7/5 |
| SP news today | knowledge | ✅ knowledge | 3.7/5 |
| Transfer failure | support | ✅ support | 5.0/5 |
| Login issue | support | ✅ support | 4.0/5 |
| Pix Parcelado | knowledge | ✅ knowledge | 5.0/5 |
| Conta digital | knowledge | ✅ knowledge | 4.7/5 |
| Recent transactions | support | ✅ support | 5.0/5 |
| Loan request | knowledge | ✅ knowledge | 4.7/5 |
| Digital account EN | knowledge | ✅ knowledge | 5.0/5 |
| Prompt injection | guardrail_blocked | ✅ guardrail_blocked | 5.0/5 |
| Last payment | support | ✅ support | 5.0/5 |

**Routing accuracy: 100% — Avg overall: 4.70/5**

eval_005 and eval_006 score lower on accuracy (3.7/5) due to Tavily free tier indexing latency for real-time queries. The agent acknowledges data freshness limitations explicitly — this is correct behavior, not a bug.

---

## Design Decisions

### Why LangGraph over CrewAI or AutoGen

LangGraph's `StateGraph` makes the agent pipeline explicit and visible. Each node is an independent function with a clear contract: receives state, returns updated state. This maps directly to the brief's architecture diagram and makes individual agents testable in isolation. Higher-level frameworks like CrewAI would have hidden the routing logic — making it harder to add the Sentiment short-circuit or the pre-router Guardrail.

### Why Guardrail as a dedicated graph node

Safety embedded inside the Router is invisible — harder to find, test, and update. A dedicated Guardrail node makes security a first-class architectural concern. For a fintech handling real money, that matters. The Guardrail uses an LLM judge rather than regex rules, which gives it natural robustness against obfuscated attacks — morse code, binary, base64, leetspeak, and reversed text are all blocked without explicit rules for each encoding. Tested and confirmed during development.

### Why Sentiment before Router

Most systems detect urgency after routing, meaning an already-frustrated customer waits through the full support pipeline before being escalated. The Sentiment Agent short-circuits critical cases directly to Handoff — the user gets a human response time commitment immediately. The threshold is conservative: the system prefers false positives (routing a routine query to Handoff) over false negatives (missing a genuinely distressed customer).

### Why Voyage AI for embeddings

Anthropic's recommended embedding partner. `voyage-3-large` produces 1,024-dimensional embeddings optimized for retrieval tasks. Keeps the stack coherent: Anthropic for generation, Voyage for embeddings.

### Jim vs Pierre: scope decision

Before finalizing the Knowledge Agent's behavior, the same 15 queries were run against InfinitePay's Jim and CloudWalk's Pierre. Jim answers general questions (sports, news) via web search and redirects to InfinitePay context. Pierre refuses off-topic queries entirely. The Knowledge Agent follows Jim's hybrid approach: answer general questions, acknowledge data freshness limitations explicitly, then redirect. Refusing "Quando foi o último jogo do Palmeiras?" creates unnecessary friction for a Brazilian fintech user. The tiered fee display also came from this research — Jim presents fees by revenue tier, which is clearer than a flat rate list.

### Personality Agent

Implemented based on CloudWalk's own architecture diagram, which shows a Personality layer before output. Applied selectively: Knowledge and Support responses go through Personality for tone consistency. Guardrail blocks and Handoff responses skip it — they require precise structured output that shouldn't be rewritten. During development, the Personality Agent was found to be rewriting the Support Agent's structured account status responses, losing critical information. The fix was making the Personality prompt explicitly conservative: preserve opening sentences, preserve ticket IDs and amounts, adjust only word choice and tone.

### Proactive Insights Agent

Surfaces one relevant insight after a support interaction — something the user didn't ask about but would find genuinely useful. Key design constraints discovered through iteration:
- Only runs for non-urgent/non-distressed cases — an urgent user needs resolution, not insights
- The insight must be topically related to the user's question — surfacing transfer limits when the user asked about login is not helpful
- Returns "NO_INSIGHT" silently when nothing relevant exists — silence is better than a forced observation
- Known inefficiency: re-fetches account data already retrieved by the Support Agent. In production this would be optimized by passing cached data through AgentState, eliminating duplicate database calls.

### Known limitations

**Conversation memory:** `MemorySaver` resets on server restart. The production solution would use `SqliteSaver` or `PostgresSaver`. Implementation was attempted but blocked by a dependency conflict: `langgraph 0.2.45` requires `langgraph-checkpoint<3.0.0`, while `langgraph-checkpoint-sqlite` requires `>=4.1.0` in recent versions — no compatible version exists without upgrading the full LangGraph ecosystem, which breaks `langchain-anthropic`, `langchain-chroma`, and `langchain-voyageai`. Documented rather than worked around with a fragile fix.

**Real-time data:** Tavily free tier has indexing latency for sports and news queries. The agent acknowledges this explicitly with a disclaimer.

**Mock user data:** Support Agent uses seeded SQLite. Production would integrate with InfinitePay's actual CRM/user API.

**LLM instruction following:** The Support Agent prompt specifies an exact opening phrase for suspended accounts. Claude Sonnet follows this instruction most of the time but not deterministically — a known limitation of LLM instruction following with competing instructions in long prompts. The system always correctly identifies the suspension and creates the ticket; the exact opening phrase varies.

**Language mixing:** Financial terms (Faturamento, Débito, Crédito) appear in Portuguese in RAG source data and are preserved in responses even when the user writes in English. These are domain-specific terms that InfinitePay users in Brazil would recognize regardless of language.

**Proactive Insights duplicate queries:** The Proactive Agent re-fetches account data already retrieved by the Support Agent. Documented as a future optimization.

---

## Observability

The system uses LangSmith for tracing. Every request generates a trace showing the full pipeline: node execution order, latency per node, token usage, and cost.

![LangSmith Knowledge Trace](docs/langsmith_knowledge.png)
![LangSmith Support Trace](docs/langsmith_support.png)
![LangSmith Handoff Trace](docs/langsmith_handoff.png)

To enable tracing, set in `.env`:
```
LANGCHAIN_TRACING_V2=true
LANGSMITH_API_KEY=your_key
LANGCHAIN_PROJECT=cloudwalk-agent-swarm
```

---

## How I built this with LLM assistance

**Background:** I came into this project with no prior AI engineering experience and had never built an agent — I understood them mainly as a user. I had done prior projects in Python and React, knowing the basics of each but not at production level.

**My approach:** I used Claude as a pair programmer throughout the entire build, starting from the first step: dissecting the assignment and structuring a daily plan from May 22 to the June 9 deadline. The plan structured work into daily milestones covering environment setup, agent development, RAG pipeline, testing, and deployment. In practice, the process was cyclical: build, test, discover a limitation, research, revise. The eval harness was built early precisely so regressions could be measured as the system evolved.

**Scope decisions made early:** From the start, I chose to go beyond the minimum requirements — implementing all three bonus challenges (Guardrail, human redirect via Slack, and a fourth custom agent) as part of the initial architecture rather than adding them later. I also decided to deploy publicly on Railway and build a frontend on Vercel. A live URL forces real-world constraints that localhost doesn't: CORS policies, persistent storage, cold start latency, environment variables in production. Debugging those issues taught more about production AI systems than running everything locally would have.

The frontend was built with Next.js and shadcn/ui, generated via v0.dev as a starting point. The decision to use v0 was about time allocation — generating the component structure in minutes meant more time for the agent pipeline, eval harness, and real integrations. The v0-generated code still required real work: replacing mock responses with live API calls, implementing markdown rendering, adding agent badges and sentiment indicators, fixing CORS, and debugging hydration errors.

**Competitive research before finalizing architecture:** Once the backend had a working foundation, the same 15 queries were run against CloudWalk's own assistants — Jim (InfinitePay) and Pierre — to see how they responded. That research directly shaped key decisions: Jim's hybrid approach to off-topic queries became the Knowledge Agent's behavior. The tiered fee display came from noticing Jim presented fees by revenue tier — something that wouldn't have been caught without that direct comparison.

**Architecture decisions were deliberate, not default:**
- LangGraph StateGraph over CrewAI: explicit node structure, independently testable agents, routing logic visible and controllable
- Guardrail as a dedicated node: safety visible in architecture, not hidden in business logic — for a fintech, auditability matters
- Sentiment before Router: urgent customers shouldn't wait through the full pipeline before escalation
- Personality Agent: implemented from CloudWalk's own diagram, then discovered it was breaking the Support Agent's structured responses. Rather than accepting the suggestion to "document and move on", the issue was traced from symptom to root cause across three agents — which taught more about LLM instruction following than any tutorial would have

**Questioning outputs, owning decisions:** Learning not to accept outputs at face value was central to the process. When the eval harness scored real-time queries lower (3.7/5), the root cause was investigated — Tavily free tier indexing latency — and documented as a known limitation. When a senior developer stress-tested the system and found hallucination bugs (the system inventing account data including a fictional user named "João"), broken conversation flows, and irrelevant proactive insights during urgent situations, each issue was debugged systematically: reproducing it, identifying the root cause, fixing it — or documenting precisely why it couldn't be fixed within current stack constraints.

The hallucination bug was particularly instructive: the system was receiving a ticket ID (ESC-XXXXX) as a user_id, failing to find the account, and then inventing plausible-looking account data rather than admitting it had nothing. The fix required understanding why the model was doing this and adding an explicit rule — not just a prompt patch, but a clear constraint that applies even when the user insists.

Not every limitation is a failure. Documenting why SqliteSaver couldn't be implemented within the current dependency constraints is more honest and more useful than pretending the problem doesn't exist.

---

## What I'd build next

- **SqliteSaver / PostgresSaver** — persistent conversation history, unblocked by upgrading the full LangGraph ecosystem
- **Real CRM integration** — replace mock SQLite with InfinitePay's actual user API
- **Multi-turn support clarification** — implement a clarification loop before tool calls for ambiguous queries, similar to Jim's behavior of asking "is this SMS or email?" before giving login steps
- **Proactive Insights optimization** — pass cached account data through AgentState to avoid duplicate database calls
- **Streaming responses** — stream tokens as they're generated for better perceived latency
- **Semantic caching** — cache embeddings for common queries to reduce latency and cost
- **Fine-tuned router** — train a small classifier on historical query data instead of using Haiku with a prompt
- **RAG over support tickets** — ingest historical ticket resolutions to improve Support Agent answers
- **Prompt A/B testing** — systematic evaluation of prompt variations against the eval harness

---

## Project structure

```
cloudwalk-agent-swarm/
├── app/
│   ├── agents/          # router, knowledge, support, sentiment, handoff,
│   │                    # proactive, personality, summarization
│   ├── api/             # FastAPI endpoints + Pydantic schemas
│   ├── graph/           # LangGraph StateGraph + AgentState
│   ├── guardrails/      # Input/output safety checks
│   └── tools/           # RAG, web search, user DB, Slack
├── data/                # ChromaDB vector store + SQLite user DB
├── docs/                # Architecture diagram + LangSmith screenshots
├── evals/               # LLM-as-judge eval harness + 15-query test set
├── frontend/            # Next.js chat interface (deployed on Vercel)
├── ingestion/           # RAG pipeline: scrape → chunk → embed → store
├── scripts/             # startup.sh + seed_users.py + generate_architecture_diagram.py
├── tests/               # 27 unit tests (mocked) + 33 integration tests
├── Dockerfile
├── docker-compose.yml        # Development (hot reload)
├── docker-compose.prod.yml   # Production (startup script, no reload)
└── .env.example
```
