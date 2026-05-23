# 01 - HTTP Basics

The simplest possible request/response. Establishes the baseline:

- **Client always initiates.**
- **One request → one response.**
- **Server has no way to push.**

## Run

**Terminal 1** (start the server):
```bash
cd examples/01_http_basics
uvicorn server:app --port 8101
```

**Terminal 2** (run the client):
```bash
cd examples/01_http_basics
python client.py
```

## Expected output

```
Request 1 ----------------------------------
status : 200
body   : {'message': 'hello', 'hit_number': 1, 'server_time': '...', 'note': '...'}

Request 2 (server doesn't remember us) -----
body   : {'message': 'hello', 'hit_number': 2, ...}

Request 3 with a query param ---------------
body   : {'you_said': 'real-time workshop', 'i_say': 'REAL-TIME WORKSHOP'}
```

## What to point out in class

- `hit_number` increments - that's *server* state, not session state. From the protocol's view each request is independent.
- The conversation lasts microseconds. To get more, the client must ask again. That's the limitation we'll spend the rest of the workshop working around.
