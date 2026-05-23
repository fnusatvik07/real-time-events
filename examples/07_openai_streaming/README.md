# 07 - Restaurant recommender agent (REAL OpenAI streaming)

Realistic scenario: a food-delivery app has an AI agent that helps customers pick dishes. The agent receives a system prompt (its persona and rules) and a user prompt (the request), then streams the response back word-by-word - the typewriter effect you know from ChatGPT.

This is the **aha** example. Everything you saw in example 05 (toy SSE server) is **exactly** what's happening when you set `stream=True` on the OpenAI API. The wire format is identical. The mental model carries over with zero gaps.

No server to run for this one - we hit OpenAI directly.

## Run

```bash
cd examples/07_openai_streaming
python client.py
```

Requires `OPENAI_API_KEY` in `../../.env` (already set up for the workshop).

## What you'll see

The client shows the system prompt (the agent's persona), the user prompt (Raj's question), and then the response streams in word by word in green:

```
==> Demo 1: What the agent receives

  SYSTEM    (the role we've assigned the LLM)
            You are the restaurant recommendation agent for LiveOrder...

  USER      I'm in Bengaluru and want vegetarian Indian dinner under 500 INR.
            Something spicy and filling. Suggest 3 dishes.
----------------------------------------------------------------------------

==> Demo 2: Stream the response (each chunk is one SSE event from OpenAI)

  AGENT     Here are 3 great spicy vegetarian options under 500 INR:

            1. Andhra Veg Meals (~250 INR) - traditional thali with spicy
               curries, sambar, and rasam. Try Nagarjuna Restaurant.
            2. Chettinad Mushroom Curry (~350 INR) - bold pepper-and-fennel
               heat, served with parottas. Try Anjappar or Junior Kuppanna.
            3. ...
----------------------------------------------------------------------------

==> Demo 3: What just happened on the wire

  Model                       gpt-4o-mini
  Chunks received (SSE events) 87
  Time to first token         412 ms
  Total stream duration       2.31 s
  Avg ms between chunks       27 ms
```

## Talking points

- **"You just watched SSE."** Every chunk in that 87-event stream was an SSE event from `api.openai.com`. The openai SDK is a thin parser on top.
- **`Time to first token` is the metric that matters for chat UX.** If it's >2 seconds, the chat feels broken regardless of how fast the rest is.
- **System prompt = agent persona.** The `system` role shapes how the model behaves. Combined with tools, this is how you build "agents."
- **For real production agents** you'd add function calling, retrieval (RAG), and memory. The streaming protocol stays the same.

## See the raw SSE with curl

If you want to prove there's no SDK magic:

```bash
OPENAI_API_KEY=$(grep ^OPENAI_API_KEY ../../.env | cut -d= -f2-)

curl -N https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "content-type: application/json" \
  -d '{
    "model":"gpt-4o-mini",
    "stream":true,
    "messages":[{"role":"user","content":"count to 5"}]
  }'
```

Each line is `data: {"choices":[{"delta":{"content":"<some text>"}}]}`. The stream ends with `data: [DONE]`. That's the entire OpenAI streaming protocol.

## Where this pattern shows up

This IS how every modern AI app streams:

- ChatGPT / Claude.ai / Gemini chat UIs
- Cursor, GitHub Copilot Chat, Continue.dev
- Every LLM SDK with `stream=True` (OpenAI, Anthropic, Mistral, Groq, ...)
- Vercel AI SDK, LangChain `astream()`, LlamaIndex streaming
- MCP server tool responses (same wire format)

When you read documentation for any of these and see `stream=true`, you now know what's happening byte-by-byte underneath.
