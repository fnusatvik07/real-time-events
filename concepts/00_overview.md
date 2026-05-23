# Workshop: How Systems Talk in Real Time

## The Big Picture

Modern apps are constantly moving data between systems: a chat bubble updates the moment your friend types, a payment confirmation pops up seconds after the transaction, a dashboard refreshes itself without you clicking anything, an AI chatbot's reply appears word-by-word.

All of that "real-time" feeling comes from **four communication patterns**:

| Pattern | Mental Model | One-line definition |
|---------|--------------|---------------------|
| **Polling** | "Are we there yet? Are we there yet?" | Client repeatedly asks the server if anything changed |
| **Webhooks** | "Don't call us, we'll call you" | One server POSTs to another the moment something happens |
| **SSE** | "Open a faucet from server to client" | Server pushes a stream of events over one long HTTP connection |
| **WebSockets** | "Open a phone line" | Both sides can talk anytime over one persistent connection |

The goal of this workshop is not just to know what they are - it's to know **when to reach for which** and **why the wrong choice will hurt you**.

---

## Why these patterns matter for AI applications

These four patterns are the hidden plumbing of every AI app you've ever used:

- **ChatGPT's "typing" animation** → SSE streaming tokens from the LLM
- **An agent that runs a 5-minute research task** → polling or webhook callback when done
- **Cursor/Copilot ghost-text suggestions** → WebSocket or SSE
- **MCP servers exposing tools to Claude** → SSE / Streamable HTTP
- **A GitHub bot that reviews PRs** → webhook receiver triggering an agent

If you don't know these patterns, you'll either:
- Burn money on idle WebSocket connections that should have been polling
- Build flaky webhook receivers that drop events
- Reach for WebSockets when SSE would have been simpler and cheaper
- Build a chat UI that feels laggy because you used polling instead of streaming

---

## Workshop Structure

This workshop is organized in 4 layers - start at the top, work down:

```
1. CONCEPTS  (concepts/*.md)           ← Read these first or alongside class
2. DIAGRAMS  (diagrams/*.drawio)       ← Visual reference for each concept
3. NOTEBOOK  (notebook/walkthrough...) ← Hands-on intro, runnable cells
4. PROJECTS  (projects/project_1, _2)  ← Two full apps to walk through end-to-end
```

### Recommended teaching order (60-90 min session)

1. **(5 min)** Overview - Why we're here, what changes for each pattern
2. **(10 min)** HTTP fundamentals - set the baseline
3. **(10 min)** Polling - start simple, show short vs long polling
4. **(10 min)** Webhooks - flip the direction
5. **(10 min)** SSE - introduce streaming
6. **(10 min)** WebSockets - full duplex
7. **(10 min)** Decision matrix - when to pick what
8. **(15 min)** Project 1 walkthrough - same chat across 3 patterns
9. **(10 min)** Project 2 walkthrough - webhook → dashboard pipeline
10. **(5 min)** Q&A on participants' own use cases

---

## How to use this material

- **Self-study:** read concept docs in order, then run the notebook, then explore projects
- **Workshop instructor:** project the diagrams while talking through concept docs; do the notebook live; demo projects in browser
- **Reference:** come back to specific concept docs when you need to make an architecture decision

---

## Concept Files

1. [HTTP fundamentals](01_http_fundamentals.md) - request/response, stateless vs stateful, persistent connections
2. [Polling](02_polling.md) - short vs long polling, trade-offs
3. [Webhooks](03_webhooks.md) - callbacks, retries, idempotency, security
4. [Server-Sent Events](04_sse.md) - one-way streaming, EventSource API
5. [WebSockets](05_websockets.md) - full duplex, handshake, scaling
6. [Decision matrix](06_decision_matrix.md) - when to use which
7. [AI agents & MCP](07_ai_agents_mcp.md) - how these patterns power modern AI apps
