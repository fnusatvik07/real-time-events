# 1. HTTP Fundamentals - the ground floor

> Before we can talk about real-time, we need a solid understanding of how the web normally talks. HTTP is the language. This page is for anyone who has used the word "API" without being totally sure what's underneath.

---

## What you'll learn

- What actually happens when your browser loads a web page
- What an HTTP "request" and "response" look like as text
- Why HTTP is described as "stateless" and why that matters
- Why HTTP alone can't do real-time, which is why we need the other four patterns

If you've built backend APIs before, you can skim. If you've never thought about what's under `fetch()` or `requests.get()`, this is exactly the right starting point.

---

## 1.1 The simplest possible exchange

Open your browser. Type `example.com` and hit enter. Here's what happens, simplified:

1. Your browser opens a network connection to a computer somewhere that owns `example.com`.
2. Your browser sends a small text message that says, in effect, "please send me the page at /".
3. The server reads that, looks up the page, and sends back another text message containing the HTML.
4. Your browser closes the connection (or holds it open briefly to make follow-up requests faster).
5. Your browser draws the HTML on screen.

That's it. HTTP - HyperText Transfer Protocol - is just rules for what those two text messages should look like, and a few conventions about who hangs up first.

**Mental model:** HTTP is the postal service for the internet. You write a letter (request), put it in an envelope with an address, drop it in the mailbox, and eventually a letter (response) arrives back. Each letter is a one-shot - no conversation, no ongoing relationship.

```mermaid
sequenceDiagram
    autonumber
    participant C as Your browser
    participant S as example.com server
    Note over C: You type example.com<br/>and press enter
    C->>S: GET / HTTP/1.1<br/>Host: example.com
    Note over S: server looks up the page
    S-->>C: 200 OK<br/>Content-Type: text/html<br/>(the HTML body)
    Note over C: browser renders<br/>the page
    Note over C,S: connection ends
```

The numbered arrows are the two HTTP messages. Steps with notes are things happening inside each computer.

---

## 1.2 What an HTTP request actually looks like

If we could open the envelope and peek inside, the request your browser sent would look like this, character for character:

```
GET /api/users HTTP/1.1
Host: api.example.com
Accept: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
User-Agent: Mozilla/5.0 ...

```

It's just plain text. Three things to notice:

1. **The first line** is the **start line**. It has three parts:
   - `GET` is the **method**. It means "fetch something". The other common methods are `POST` (create), `PUT` (replace), `PATCH` (modify), and `DELETE` (remove).
   - `/api/users` is the **path** - which thing on the server you want.
   - `HTTP/1.1` is the protocol version.

2. **The middle lines** are **headers**. They're key-value pairs giving the server extra context: who you are, what response format you can handle, your auth token. There are dozens of standard headers and you can invent your own (`x-` prefix is the convention).

3. **The blank line at the end** is mandatory. It's how the server knows the headers are done. After the blank line you can include a **body** (for `POST`/`PUT`), but `GET` requests usually don't have one.

### Try this yourself

If you want to see this for real, open a terminal and run:

```bash
curl -v https://httpbin.org/get
```

The lines that start with `>` are the request your `curl` sent. The lines starting with `<` are the response. You'll see exactly the format above.

---

## 1.3 What a response looks like

The server's reply looks similar:

```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 348
Cache-Control: no-store

{"users":[{"id":1,"name":"Maya"},{"id":2,"name":"Raj"}]}
```

Same three pieces:

1. **Status line**: `HTTP/1.1 200 OK`.
   - `200` is the **status code**. Three-digit numbers; the first digit tells you the category.
   - `OK` is the human-readable name.

2. **Headers** describing the response (content type, cache hints, etc.).

3. **Blank line, then the body** - the actual data you asked for.

### Status codes worth remembering

You'll encounter these constantly in real-time code. Bookmark this table:

| Code | Category | What it means | Where you'll see it |
|------|----------|---------------|---------------------|
| `200 OK` | Success | "Here's what you asked for" | Most successful API calls |
| `201 Created` | Success | "I made the new thing" | After a POST that creates something |
| `202 Accepted` | Success | "Got it, working on it asynchronously" | Long-running job kicks, webhook receivers |
| `204 No Content` | Success | "Done, nothing to return" | Successful DELETE; short polling with no new data |
| `301 / 302` | Redirect | "Look over there instead" | URL changed |
| `304 Not Modified` | Redirect | "What you have is still fresh" | Smart polling using ETags |
| `400 Bad Request` | Client error | "Your request is malformed" | Missing fields, bad JSON |
| `401 Unauthorized` | Client error | "Log in first" | Missing or expired token |
| `403 Forbidden` | Client error | "Logged in but you can't do this" | Permission denied |
| `404 Not Found` | Client error | "That thing doesn't exist" | Wrong URL or missing record |
| `408 Request Timeout` | Client error | "You took too long" | Long-polling fell past server limit |
| `409 Conflict` | Client error | "State conflict" | Editing something someone else just edited |
| `429 Too Many Requests` | Client error | "Slow down" | You're polling too aggressively, or rate-limited |
| `500 Internal Server Error` | Server error | "Something blew up on our side" | Bug, crashed dependency |
| `502 Bad Gateway` | Server error | "Proxy got nothing useful" | Backend was down when LB asked |
| `503 Service Unavailable` | Server error | "Try again soon" | Maintenance, overload |
| `504 Gateway Timeout` | Server error | "Backend took too long" | Slow endpoint behind a timeout |

**The pattern:** `1xx` info, `2xx` good, `3xx` go elsewhere, `4xx` your fault, `5xx` server's fault.

Why this matters for real-time: webhook senders treat `5xx` as "retry later" and `4xx` as "your problem, won't retry" (with the unfortunate exception that some treat `408` and `429` as retry-worthy). When you build a webhook receiver, **always return `200` for "I got it" even if you can't process the event yet** - retrying webhooks for problems you can't fix is just noise.

---

## 1.4 Stateless - the most important word on this page

HTTP is **stateless**. This single property shapes everything we'll build later.

"Stateless" means: **the server has no built-in memory of you between requests.** If you make a request now and another request five seconds later, those are two completely independent events from the protocol's point of view. The server treats them like two strangers walking up to a counter.

### Why this is good

It makes servers easy to scale. If you have 10 servers behind a load balancer, request #1 can go to server 3 and request #2 can go to server 7, and neither server has to know what the other knows. You can add and remove servers freely. Crashes don't lose conversations.

### Why this is awkward for us

If the server doesn't remember you, how does it know you're logged in? How does your shopping cart survive page navigations?

The answer: **you (the client) carry the memory and re-present it on every request.** That's what cookies and `Authorization` headers do. The server doesn't remember "Maya is logged in"; the server checks the token Maya's browser sends with every single request and re-derives "ah, this is Maya."

### Why this matters for real-time

If a new message arrives for Raj on the server, the server can't say "let me notify Raj" - it doesn't have any open line to Raj. There is no phone number for the server to call. There is no email address baked into the protocol.

So either:

- **Raj keeps asking** (polling)
- **Raj or his browser open a long-lived connection and the server pushes down it** (SSE, WebSockets)
- **Some external system already has a long line open to your server** (webhooks)

The four real-time patterns are all answers to the question "how do we work around the fact that HTTP is request/response, stateless, and client-initiated?"

---

## 1.5 Where the lines blur - stateful **connections** on top of stateless HTTP

HTTP itself is stateless, but the **TCP connection underneath** is stateful. TCP is the lower-level protocol HTTP runs on. When you "open a connection" to a server, you and the server agree on a tiny piece of shared state: sequence numbers, buffers, window sizes.

By default, every HTTP request used to open and close its own TCP connection. That's expensive (the open + close takes round trips). So HTTP/1.1 added **keep-alive**: re-use the same TCP connection for many requests.

```mermaid
flowchart LR
    subgraph H10["HTTP/1.0 - one TCP connection per request"]
        direction LR
        A1[open] --> B1[request] --> C1[response] --> D1[CLOSE] --> A2[open] --> B2[request] --> C2[response] --> D2[CLOSE]
    end
    subgraph H11["HTTP/1.1 keep-alive - reuse the connection"]
        direction LR
        A3[open] --> B3[request] --> C3[response] --> B4[request] --> C4[response] --> B5[request] --> C5[response]
    end
```

This little optimisation is the seed of two of our four patterns:

- **Long polling** uses one HTTP request that hangs around for a long time before the server replies. Built on plain keep-alive HTTP.
- **Server-Sent Events** uses one HTTP request that the server never finishes - it just keeps writing more bytes down the same response. Built on plain keep-alive HTTP.

**WebSockets** go further: they start as HTTP but then "upgrade" to a completely different protocol on the same TCP connection. After the upgrade, HTTP is gone and a custom binary frame format takes over.

---

## 1.6 HTTP versions in 90 seconds

You'll hear about HTTP/1.1, HTTP/2, and HTTP/3. Here's the just-enough-to-be-dangerous version:

| Version | What changed | Why you might care |
|---------|------|--------------------|
| **HTTP/1.0** | Original. One request per TCP connection. | Mostly historical |
| **HTTP/1.1** | Keep-alive (reuse connections), chunked transfer encoding | This is what most "long-lived" patterns assume |
| **HTTP/2** | One TCP connection multiplexes many parallel requests | SSE works much better on HTTP/2 because browsers limit you to 6 connections per host on HTTP/1.1 |
| **HTTP/3** | Same idea as HTTP/2 but runs on UDP (called QUIC) | Better on flaky mobile networks, survives IP changes |

For everything we'll talk about in this guide, the **patterns are identical across versions**. You'll just see slightly different scaling limits and slightly different debugging tools. If you're learning, use HTTP/1.1 mentally and don't worry about the rest until something forces you to.

---

## 1.7 Walking through Maya's first API call

Let's make this concrete. Maya is building LiveOrder. Her first endpoint returns the list of restaurants near a customer. Here's the full life of one request, with everything we've covered playing its part:

**Raj's phone wants to load the restaurant list.**

1. The app calls `fetch("https://api.liveorder.app/restaurants?lat=12.97&lng=77.59")`.
2. The OS resolves `api.liveorder.app` to an IP address using DNS.
3. The OS opens a TCP connection to that IP on port 443 (HTTPS).
4. TLS handshake happens (encryption setup; not really HTTP's concern but happens here).
5. Inside the encrypted tunnel, Raj's phone sends:
   ```
   GET /restaurants?lat=12.97&lng=77.59 HTTP/1.1
   Host: api.liveorder.app
   Authorization: Bearer eyJhbGc...
   Accept: application/json
   ```
6. The request travels over the internet to Maya's load balancer.
7. The load balancer picks one of her backend servers and forwards the request.
8. The backend server reads the headers, validates the auth token, queries the database, builds a JSON response, and writes:
   ```
   HTTP/1.1 200 OK
   Content-Type: application/json
   Content-Length: 1432

   [{"id":1,"name":"Priya's Biryani",...},{...}]
   ```
9. The bytes travel back; Raj's phone parses the JSON and renders the list.
10. The TCP connection stays open (keep-alive) so the next request - maybe `/restaurants/1/menu` - skips steps 3 and 4.

Notice everything from step 6 onward had no idea it was Raj specifically. Each server in the chain treated this as just another request, validated the token, served it, and moved on. **That's statelessness.** That's why Maya can run 50 backends in parallel without anything coordinating between them.

Now imagine: while Raj is browsing the menu, Sam the delivery driver moves. Maya's server knows Sam moved. But Maya's server has no open line to Raj's phone right now - the keep-alive TCP connection is idle and Raj's app isn't actively asking anything. The server cannot push the new position to Raj. This is exactly the limitation the next four pages will solve.

---

## 1.8 Cheat sheet

- **HTTP** = the rules for how clients and servers talk on the web.
- **Request** = client's message asking for something. Has a method (`GET`/`POST`/...), a path, headers, and an optional body.
- **Response** = server's reply. Has a status code (`200`/`404`/`500`/...), headers, and a body.
- **Stateless** = server has no memory between requests. The client must re-present any context (cookies, tokens) each time.
- **TCP connection** = the underlying pipe HTTP rides on. Can be reused for many requests (keep-alive) or upgraded entirely (WebSockets).
- **Status code categories**: 1xx info, 2xx success, 3xx redirect, 4xx client error, 5xx server error.
- **The reason real-time is hard**: HTTP only lets the client speak first. Real-time patterns all work around that.

Now turn the page. We'll see what happens when Maya needs Raj's phone to find out about something the server knows but he didn't ask for.
