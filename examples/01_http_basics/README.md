# 01 - HTTP Basics

A small but realistic backend, and a verbose client that walks through every endpoint with a clear lesson per demo. The goal is to teach exactly **what HTTP gives you and what it doesn't** before we move on to real-time patterns.

## What the server exposes

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/`                    | Friendly index listing all endpoints |
| `GET`  | `/time`                | Server clock - pure read, no state |
| `GET`  | `/counter`             | Bumps a SHARED global counter |
| `GET`  | `/me`                  | Requires an `Authorization: Bearer <user>` header |
| `GET`  | `/weather/{city}`      | **Calls a real external API** (wttr.in) and returns weather |
| `GET`  | `/notes`               | Lists all in-memory notes |
| `POST` | `/notes`               | Creates a note. Returns `201 Created` |
| `GET`  | `/notes/{id}`          | Fetches one note (`200`) or `404` if not found |

Together these cover GET vs POST, path parameters, query parameters, request headers, request bodies, status codes (200, 201, 401, 404, 502), in-memory state, and outbound HTTP calls.

## Run it

**Terminal 1** (start the server):

```bash
cd examples/01_http_basics
uvicorn server:app --port 8101
```

**Terminal 2** (run the walkthrough):

```bash
cd examples/01_http_basics
python client.py
```

## What you'll see

The client prints seven demos in this format:

```
==>  Demo N: <what we're showing>

  REQUEST   GET http://127.0.0.1:8101/time
  RESPONSE  200 OK   (application/json)
            {
              "server_time_iso": "...",
              "unix_seconds": ...,
              "timezone": "UTC"
            }

  LESSON    <one or two sentences making the point land>
```

So each demo shows: what was sent, what came back, and why it matters.

### The seven demos

1. **Plain GET** - no parameters, no auth. The simplest possible HTTP exchange.
2. **Path parameter + external API** - `/weather/Bengaluru` triggers a call from our server to wttr.in. Shows that real backends are mostly glue between other backends.
3. **The "stateless" point** - calls `/counter` three times. The counter goes up, but the server has no idea you're the same caller.
4. **Identifying yourself** - calls `/me` without an `Authorization` header (gets 401), then with one (gets 200). Drives home the "re-present yourself on every request" idea.
5. **POST creates** - creates a note. Server returns 201 with the created resource.
6. **GET the new resource** - fetches the note we just created. Shows that data persists on the server, but **the server didn't notify anyone** about the creation.
7. **404** - request a note that doesn't exist.

## Talking points for the class

- **"Stateless" is about clients, not about data.** The server has data (notes, the counter). What it doesn't have is per-client memory.
- **Sessions are bolted on.** Cookies and bearer tokens are the layer above HTTP that fakes "you're the same caller as before" by making the client present its identity each time.
- **Most backends are glue.** Demo 2 makes this concrete - one inbound request, one outbound request to wttr.in, response composed from the result. Almost every interesting API does this.
- **The server can never push.** Demo 6 is the cliffhanger. The note was created. Nobody else was notified. We had to ask. That's the gap every real-time pattern fills.

## Try it from curl

If you want to demo without Python:

```bash
# Plain GET
curl http://127.0.0.1:8101/time

# External API
curl http://127.0.0.1:8101/weather/Mumbai

# Auth (will fail then succeed)
curl http://127.0.0.1:8101/me
curl -H "Authorization: Bearer alice" http://127.0.0.1:8101/me

# POST + GET
curl -X POST http://127.0.0.1:8101/notes \
  -H "content-type: application/json" \
  -d '{"title":"Buy biryani","user":"alice"}'
curl http://127.0.0.1:8101/notes/1

# Counter
curl http://127.0.0.1:8101/counter
curl http://127.0.0.1:8101/counter
curl http://127.0.0.1:8101/counter
```
