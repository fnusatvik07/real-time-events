# 07 - Real-World: OpenAI Streaming is SSE

This is the "aha" example. Everything you learned in example 05 (SSE) is exactly what powers ChatGPT, Claude, the OpenAI Python SDK's `stream=True`, and every LLM chat UI you've used.

No server to start - we connect to OpenAI directly.

## Run

```bash
cd examples/07_openai_streaming
python client.py
```

> Requires `OPENAI_API_KEY` in `../../.env` (already populated for the workshop).

## Expected output

```
Asking the LLM to count from one to ten.

Streamed response (each chunk is one SSE event):

One
Two
Three
Four
Five
Six
Seven
Eight
Nine
Ten

first token: 350ms
total      : 980ms
chunks     : 11

Under the hood OpenAI's server sent SSE events like:
  data: {"choices":[{"delta":{"content":"One"}}]}
  ...
```

## See the raw SSE yourself

Set `OPENAI_LOG=debug` for verbose output, or use plain curl:

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

You'll see the raw SSE stream - `data: {...}` lines separated by blank lines, ending in `data: [DONE]`.

## What to point out

- The `openai` SDK is **just an SSE client** with JSON parsing on top.
- This is also how Anthropic, Mistral, Groq, and every other LLM provider streams.
- MCP servers use SSE (or its successor "Streamable HTTP") for the same reason: server emits many events for one request.
