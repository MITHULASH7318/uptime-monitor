# AI Collaboration Log

## AI tech stack

- **Claude Sonnet 5** (claude.ai) — used for scaffolding the FastAPI backend, the
  Streamlit dashboard, and reviewing the docker-compose networking setup.
- **GitHub Copilot** — inline completions while cleaning up the SQLAlchemy models and
  Streamlit form handling.

## The prompts that shipped it

**Backend scaffold:**
> "Build a FastAPI backend for an uptime monitor. I need endpoints to register a URL,
> list all registered URLs with their latest health check, and view a URL's check
> history. Use SQLAlchemy + SQLite. Add a background job with APScheduler that pings
> every registered URL every 60 seconds and records status code, response time in ms,
> and whether it's up or down. Down = anything that isn't a 2xx/3xx response, or a
> request exception (timeout, DNS failure, connection refused)."

**Frontend scaffold:**
> "Now build a Streamlit dashboard that polls that API. Show a table of all monitored
> URLs with a status badge (up/down), latest response time, and last-checked
> timestamp. Add a form to register a new URL and a way to remove one. It needs to
> auto-refresh every 15 seconds without the user manually reloading the page."

**Containerizing it:**
> "Write Dockerfiles for both services and a docker-compose.yml so the whole thing
> comes up with one `docker compose up`. The backend needs a persistent volume so the
> SQLite file survives a restart. The frontend needs to reach the backend by its
> service name, not localhost, since they're on the same Docker network."

## Course corrections

The first draft of the frontend refresh logic used a `while True: time.sleep(15)` loop
wrapped around the API call, straight from the initial AI suggestion. That's a classic
Streamlit anti-pattern — it blocks the whole script thread, so the UI never re-renders
and the "Add URL" form becomes unresponsive while it's sleeping. I caught this by
actually running the app: the form input just froze.

Fix: swapped it for the `streamlit-autorefresh` component, which triggers a proper
Streamlit rerun on a timer instead of blocking inside the script. That's a real,
maintained package (not hallucinated), but it wasn't the first thing suggested — the
AI defaulted to the naive polling loop until I pushed back with "this freezes the UI,
give me a non-blocking way to auto-refresh a Streamlit page."

Second smaller fix: the initial backend only ran the ping job on the 60-second
schedule, so a URL you'd just added sat with no data ("Pending") for up to a minute
before you could see it was working. I asked for an immediate check on registration so
the demo/testing flow (add a URL, see its status right away) doesn't require waiting
around — that's why `POST /api/urls` fires one ping synchronously before returning.

---
*Note to self before submitting: personalize this with your own actual back-and-forth —
screenshots or copy-pasted snippets from your real Claude/Cursor session make this land
better than a tidy summary.*
