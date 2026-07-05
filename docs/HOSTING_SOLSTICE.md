# Hosting ISA Under solsticestudio.ai/isa

This note describes how ISA can be hosted under the existing Solstice public Flask web server at `solsticestudio.ai/isa`. The ISA repo now supports subpath hosting, and the local Solstice `web_server.py` has a `/isa` reverse proxy that forwards to a separate ISA process. Deployment should still be done deliberately with secrets, process management, and document access policies in place.

## Short Answer

Difficulty: moderate, not hard.

The existing `C:\dev\Solstice-EIM\web_server.py` already has many route and proxy patterns. The safest approach is to run ISA as a separate internal service, then proxy `/isa` and `/isa/*` from the public web server to that service.

This avoids merging two Flask apps and keeps ISA dependencies, environment variables, logs, and document storage isolated.

## Recommended Architecture

```mermaid
flowchart LR
    U[Browser] --> D[solsticestudio.ai/isa]
    D --> W[Solstice web_server.py]
    W -->|Reverse proxy /isa/api/* and assets| I[ISA Flask service on localhost]
    I --> G[Gemini API]
    I --> P[Pinecone]
    I --> K[Local ISA knowledge/ PDFs]
```

## Why Proxy Instead Of Importing ISA Directly?

Proxying is cleaner because:

- ISA has its own Flask app, templates, static files, and config.
- ISA has separate Python dependencies.
- ISA needs its own `.env` and private PDF directory.
- Restarting ISA should not require restarting the public marketing site.
- Public routes can be gated or removed quickly at the proxy layer.
- It avoids route collisions with the existing Solstice app.

## ISA Base-Path Support

ISA supports an app base path for `/isa` hosting. The frontend reads `window.ISA_BASE_PATH`, API calls use that prefix, document source links use that prefix, and Flask trusts `X-Forwarded-Prefix` via `ProxyFix` when proxied.

Useful deployment setting:

```env
ISA_BASE_PATH=/isa
```

If `ISA_BASE_PATH` is not set, ISA can still infer `/isa` from the proxy's `X-Forwarded-Prefix` header.

## Solstice Web Server Route

In `C:\dev\Solstice-EIM\web_server.py`, the local route proxies `/isa`, `/isa/`, and `/isa/<path>` to ISA:

```python
ISA_UPSTREAM_URL = os.getenv("ISA_UPSTREAM_URL", "http://127.0.0.1:5010").rstrip("/")

@app.route("/isa", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
@app.route("/isa/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
@app.route("/isa/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
def isa_proxy(path):
    upstream_path = f"/{path}" if path else "/"
    upstream_url = f"{ISA_UPSTREAM_URL}{upstream_path}"
    # forward request and send X-Forwarded-Prefix: /isa
```

The proxy should strip the `/isa` prefix before forwarding, preserve the request method, query string, body, and content type, and send `X-Forwarded-Prefix: /isa` so ISA can generate correct asset and source-document URLs.

## Process Management

ISA should run as a separate process on localhost, for example:

```powershell
$env:PORT="5010"
$env:ISA_BASE_PATH="/isa"
python app.py
```

For a real deployment:

- use Waitress or Gunicorn/WSGI depending on host OS
- run it as a service
- restart automatically on failure
- keep logs separate from the public site
- keep `.env` outside Git

## Security Considerations Before Public Exposure

Before exposing `/isa` publicly, decide whether ISA is:

1. a public demo, or
2. a private interview/demo endpoint.

For a private demo, add at least one of:

- basic auth at the web-server/proxy layer
- a secret demo token
- IP allowlist
- Cloudflare Access
- temporary route enabled only during the interview

Do not expose private Inogen PDFs publicly unless there is permission to do so. Source document links would serve PDFs from `knowledge/`, so public hosting needs a document-access policy.

## Estimated Work

### Fast Internal Demo

Time: 1-2 hours.

- Run ISA on localhost port 5010.
- Use the `/isa` proxy route in `web_server.py`.
- Add minimal path rewriting if needed.
- Add temporary basic access control.
- Smoke test chat and static assets.

### Clean Public Demo

Time: 0.5-1 day.

- Use ISA base-path support.
- Use the Solstice proxy route.
- Add auth/demo gate.
- Add process manager.
- Add health check.
- Confirm no private PDFs are exposed unintentionally.
- Test source links and static assets under `/isa`.

### Production-Grade Deployment

Time: 2-5 days depending on hosting environment.

- Containerize or service-manage ISA.
- Add auth, rate limiting, CSRF, and logging policy.
- Add prompt-injection hardening.
- Add source-document governance.
- Add monitoring and uptime checks.
- Add backup and rollback process.

## Recommendation For The Interview

Do not host the full Inogen-specific assistant publicly before the interview unless you are comfortable exposing the demo and its source document behavior.

The strongest option is:

- keep the GitHub repo public without private PDFs or keys
- run ISA locally for the interview demo
- optionally prepare `/isa` as a private, gated route if a hosted demo becomes necessary

That shows engineering readiness without giving away a production deployment or private documentation setup.
