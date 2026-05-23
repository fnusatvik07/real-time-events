# 03 - Long Polling (Uber-style ride dispatch)

Realistic scenario: Raj opens Uber and requests a ride. The app shows "Looking for a driver..." and waits. The instant a driver accepts, the app updates with driver name, vehicle, and ETA.

This is a perfect long-polling use case:
- The client doesn't know WHEN the driver will accept (could be 2 seconds, could be 30).
- Latency matters - Raj wants to see "Driver assigned" the moment it happens.
- Polling every second would burn requests for nothing.
- A single held request, replied to the moment of acceptance, is exactly what's needed.

## What the server does

`POST /rides` creates a ride and kicks off a background task that picks a driver after a random 4-12 seconds.

`GET /rides/{id}/wait` is the long-poll endpoint. It uses an `asyncio.Event` to wait until the background task marks the ride as accepted, then returns immediately. If 30 seconds pass first, it returns with `timed_out: true` so the client knows to reconnect.

## Run

**Terminal 1:**
```bash
cd examples/03_long_polling
uvicorn server:app --port 8103
```

**Terminal 2:**
```bash
cd examples/03_long_polling
python client.py
```

## What you'll see

```
==> Demo 2: Open the long-poll connection and wait for a driver

  REQUEST   GET    http://127.0.0.1:8103/rides/ride_xyz/wait
            (the server will NOT respond immediately; it will hold this
             request open until a driver accepts, or up to 30 seconds)

  WAITING   connection open, no traffic flowing...
  REPLIED   after 6.81 seconds

  RESPONSE  200 OK   (application/json)
            {
              "id": "ride_xyz",
              "status": "accepted",
              "driver": {
                "name": "Priya",
                "vehicle": "KA-05-CD-5678",
                "rating": 4.8,
                "eta_min": 3
              },
              ...
            }
```

Then the cost comparison:

```
  Time until driver accepted               6.8 s
  Requests we sent (long polling)          1
  Requests we'd have sent if short polling ~5
  Wasteful requests with short polling     ~4
```

## Talking points

- **One held request vs many short ones.** Both deliver the result; long polling does so with 80% fewer requests.
- **Near-zero latency on acceptance.** The driver acceptance fires the `asyncio.Event` which immediately unblocks the held HTTP handler.
- **Server-side cost is RAM, not CPU.** Each held connection is mostly a sleeping coroutine and a couple of kilobytes of socket state.
- **The two production gotchas:**
  - Server timeout must be **less** than the load balancer's idle timeout, or the LB will cut the connection first.
  - Synchronous frameworks fall over fast - one held request per worker thread; 50 concurrent rides exhausts a default Gunicorn pool.

## Try it from curl

```bash
# Create a ride
RIDE=$(curl -s -X POST http://127.0.0.1:8103/rides \
  -H "content-type: application/json" \
  -d '{"rider":"Raj","pickup":"Whitefield","dropoff":"Airport"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Long-poll for the driver. This will hang for a few seconds, then return.
curl http://127.0.0.1:8103/rides/$RIDE/wait
```

You'll feel the wait. Then the response prints. That's long polling in one observation.
