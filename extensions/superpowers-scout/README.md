# Superpowers Scout — optional research and web-design toolkit

**An independent extension to [obra/superpowers](https://github.com/obra/superpowers), not the original Superpowers project.** This folder provides a Python research agent, a local HTTP interface, a CLI entry point and a website-reconstruction skill. The fork's upstream framework and release cadence are separate from this extension.

## What works

- GitHub repository discovery and ranking using repository name, description, **README excerpts**, topics and bounded popularity signals. README evidence is fetched for shortlisted candidates and reranking happens after inspection.
- Skill-file inspection **only for explicit agent-skill searches**. For website cloning and real software libraries, SKILL.md presence has **zero ranking bonus**.
- Failure-specific search strategies. An ordinary investigation tries two distinct search queries by default before shortlisting; a supplied failure requires at least three where the budget allows. This is a **research loop, not a code-execution or screenshot-repair loop**.
- Query and inspection caching in SQLite under `~/.cache/superpowers-scout/cache.sqlite3` (or `$XDG_CACHE_HOME/superpowers-scout/cache.sqlite3`). Configure `SUPERPOWERS_DB` to use an attached persistent volume when hosting. Cache persistence is not guaranteed on ephemeral hosting.
- Bounded GitHub API requests per investigation, explicit GitHub rate-limit errors and short retry/backoff for transient 5xx/network failures. Set `GITHUB_TOKEN` for meaningful throughput; **unauthenticated API quota is very limited**.
- Honest prompt refinement: a deterministic *execution brief* by default, optional actual model-assisted rewriting with `OPENAI_API_KEY`, labelled `prompt_optimisation_method`.
- A local-first HTTP server with optional bearer authentication, CORS allowlist, request quota, concurrency cap, validated inputs and generic server errors. It will **not listen on a non-local interface without `SUPERPOWERS_API_KEY`**.
- A CLI that calls **the exact same Python engine** as the server. The ChatGPT plugin remains an **instructions-only skill** unless an execution environment or explicit HTTP tool is provided.
- Design and cloning checklist: `skills/web-design/SKILL.md` and `examples/website-reconstruction-brief.md`.

## Quick start

Python 3.10+; no external Python packages are required.

```bash
# From the fork root:
cd extensions/superpowers-scout
export GITHUB_TOKEN='your-token' # strongly recommended; not committed to Git
python -m engine.cli --prompt 'Clone the authorised landing page at https://example.com' --no-model
python -m engine.cli --prompt 'Fix the clone' --failure 'On mobile the header overflows' --no-model
python server.py
# Then open http://127.0.0.1:8000
```

Generation uses `OPENAI_API_KEY`, if set. By default `POST /api/run` constructs a deterministic brief, refines it with a model if configured, and then optionally asks the model for an answer. This **does not** execute code or verify the answer.

## APIs

- `POST /api/run` with `{"prompt":"...", "failure":"...", "max_rounds":4, "strict":true, "refine_prompt":true}`.
- `POST /api/investigate` with `{"prompt":"...", "failure":"...", "include_communities":true, "use_laya":false}` for research leads without code execution.
- `GET /api/manifest` exposes the shared evidence-policy and workflow manifest.
- `GET /health` checks server availability.

`strict: true` prevents *both* model refinement and answer generation when the evidence shortlist is inadequate. It does **not** imply the shortlisted code has passed build, security, accessibility or screenshot QA.

For remote hosting, use `HOST=0.0.0.0 SUPERPOWERS_API_KEY=<secret>` and TLS via the host's proxy. Set `SUPERPOWERS_ALLOWED_ORIGINS=https://your.domain` only when cross-origin browser access is required. Per-process request quotas and concurrency limits are **not distributed** across replicas; use an ingress/gateway quota for production. Do not put tokens in public frontend JavaScript. Configure a persistent cache volume if hosting needs persistence.

## Optional Laya and communities

`engine/laya.py` supports an *optional local* `/v1/systemone` decision service. No Laya model is installed or benchmarked by this repository. `engine/discovery.py` searches public Hacker News and Stack Overflow APIs as candidate leads; it does not scrape private boards or verify community claims.

## Shared behaviour and the ChatGPT limitation

`engine.iterative.solve` is the canonical implementation used by `python -m engine.cli` and by `server.py`. `plugin/skills/superpowers/SKILL.md` points at that engine and uses it when the local workspace or an authenticated API is actually accessible. The ChatGPT skill cannot create a global pre-answer hook or independently connect to this HTTP server. Without those capabilities, any manual search is a **fallback**, not a claim that the plugin and server executed the same process.

`workflow_spec.json` describes shared workflow intent; unlike executable code, it does not guarantee behaviour without a running tool. The root fork follows the separate `obra/superpowers` project. If the fork is behind upstream, synchronise it separately and review the upstream changes; do not overwrite upstream framework files while changing this extension.

## Tests

```bash
cd extensions/superpowers-scout
python -m unittest discover -s tests -v
```

The tests mock GitHub and model calls and exercise local HTTP handling. A green test suite does **not** demonstrate live API throughput, accurate visual cloning, live Laya inference or security certification.

## Non-goals

This is not a general background ChatGPT interceptor, an automatic code-modifying agent, an installation or security audit, or an implemented browser screenshot-to-code comparator. Respect licences, site ownership and access restrictions; do not copy unauthorised protected assets. Research results remain untrusted source material.
