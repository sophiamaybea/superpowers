# Superpowers — shared GitHub research + prompt optimisation

Two surfaces: a private ChatGPT skill plugin and a standalone browser-based agent. The same methodology is documented in the plugin and implemented by `engine/core.py` for the standalone service.

## Run locally
Python 3.10+; no external Python packages needed.

```bash
cd extensions/superpowers-scout
export OPENAI_API_KEY='your-key' # optional: without this, research and prompt improvement still work
export GITHUB_TOKEN='your-token' # optional: improves GitHub rate limits
python server.py
```

Open http://localhost:8000. Every POST to `/api/run` first performs GitHub searches, then produces an improved prompt, then optionally calls the language model. A failed GitHub search is reported, not concealed. This is a best-effort research gate, not a guarantee of GitHub availability.

## Deployment
Can be deployed on a Python-capable hosting service; set `PORT`, `OPENAI_API_KEY`, and optionally `GITHUB_TOKEN`. Do not put keys in frontend code. For production add authentication, request quotas, observability, retry/backoff and provider-specific deployment configuration. Do not expose the API publicly without authentication.

## Limitations
The private plugin is a skill-based workflow, not a background interceptor for every ChatGPT message. The standalone agent enforces research-before-generation on its own endpoint. GitHub repository discovery uses public GitHub API search, not uncontrolled HTML scraping; GitHub results are candidates, not independently audited code. The model integration uses the OpenAI Chat Completions API when a key is supplied.

## v0.2 research upgrade
- Searches GitHub API, scores candidates transparently and inspects skill-file paths.
- Reads up to three bounded SKILL.md previews as **untrusted** text; never executes downloaded code.
- Adds `strict: true` in POST `/api/run` to refuse AI generation when research is incomplete.
- Stores cached public GitHub metadata in SQLite (set `SUPERPOWERS_DB` for persistent disk).
- API authentication: set `SUPERPOWERS_API_KEY` and pass `Authorization: Bearer <key>`.
- The private ChatGPT plugin is a *skill*, not an HTTP-connected app. A single hosted API shared by both surfaces is **not** yet available.

## Version 0.3: iterative recovery and design quality
The standalone `/api/run` now attempts up to four distinct GitHub queries by default, scores candidates against the actual type of task, inspects candidate skills and records a research trace. `max_rounds` can be set from 1 to 6; `strict: true` prevents AI generation if the evidence shortlist fails its threshold. The gate is heuristic: a real website clone still needs screenshot comparison, interaction tests and manual design review. This is not an autonomous coding loop and does not run untrusted code.


## v0.4: cross-source investigation and optional Laya
`POST /api/investigate` accepts `{ "prompt": "...", "max_rounds": 3, "include_communities": true, "use_laya": false }`. It performs bounded GitHub research plus public Hacker News and Stack Overflow discovery. Community posts are leads, not verified answers. This endpoint returns evidence, not executed fixes.

Laya is **optional**. Run a compatible Laya `/v1/systemone` HTTP server locally, then set `LAYA_BASE_URL=http://127.0.0.1:8001` and pass `use_laya: true`. The adapter deliberately rejects remote HTTP hosts and reports failures instead of claiming inference succeeded. The payload contract must be checked against the installed Laya server version. No model weights are bundled; no Laya inference has been benchmarked here. The existing `/api/run` endpoint retains its v0.3 behaviour.

Research is bounded and cannot guarantee finding the best possible solution. Autonomous code modification, screenshot comparison and repeated repair are not implemented. Public source retrieval must comply with applicable terms and rate limits.

## Website design and cloning specialisation
See `skills/web-design/SKILL.md` and `examples/website-reconstruction-brief.md`. This is a documented execution workflow for capable coding/browser agents, **not** an implemented screenshot-to-code or visual regression executor. It covers reference inspection, evidence-led library selection, accessibility, performance, screenshot comparisons, and iterative repair. A runtime with browser and code-editing tools is required to execute those steps.
