# Deployment Notes

## System dependencies

### antiword (required for legacy .doc parsing — Phase 2)

`backend/app/parsing/doc_parser.py` shells out to `antiword` to extract text
from pre-2007 binary `.doc` files. There's no reliable pure-Python reader
for that format.

If `antiword` isn't installed on the host, `.doc` uploads fail with a clear
`LAB_READ_FAILED` message asking the student to re-upload as `.docx` or
`.pdf` — the app doesn't crash, and it doesn't fabricate content. PDF and
DOCX parsing are unaffected either way.

**Install on Debian/Ubuntu-based hosts:**

```bash
apt-get update && apt-get install -y antiword
```

**Docker:** add the line above to whatever base-image Dockerfile ends up
serving the FastAPI backend (not yet created as of Phase 2).

**Vercel / serverless / other minimal hosts:** confirm antiword can be
installed or vendored before relying on `.doc` support in that environment;
otherwise `.doc` uploads will consistently fail there while PDF/DOCX
continue to work.

### Docker (required for safe code execution — Phase 4)

`backend/app/execution/python_executor.py` shells out to the `docker` CLI
to run student code in an isolated, network-disabled, resource-limited
container. This requires:

- The `docker` CLI available on `PATH` for the process running the FastAPI
  backend.
- That process able to reach the Docker daemon (typically via
  `/var/run/docker.sock`).
- The `python:3.11-slim` image available locally, or reachable to pull —
  `docker pull python:3.11-slim` ahead of time avoids a slow first request.

If the backend itself runs inside a container, this means giving that
container access to the *host's* Docker daemon (commonly by mounting
`/var/run/docker.sock` into it) — running Docker-in-Docker via a nested
daemon is unnecessary and generally discouraged for this use case.

Per `PROJECT_SPEC.md` §4, code execution is disabled by default
(`CODE_EXECUTION_ENABLED=false`) until an operator explicitly confirms
this is set up correctly in a given environment — see
`docs/CODE_EXECUTION.md` for the two-gate check this relies on.

### Playwright / Chromium (required for screenshots — Phase 5)

`backend/app/screenshots/` uses Playwright to render terminal-style
screenshots of real execution output. The `playwright` Python package
alone isn't enough — it also needs a downloaded Chromium binary.

**Install:**

```bash
pip install -r requirements.txt
playwright install --with-deps chromium
```

`--with-deps` also installs the OS-level libraries Chromium needs
(fonts, `libnss3`, etc.) — skipping it is a common cause of a Chromium
binary being present but failing to launch.

If Chromium isn't installed or fails to launch, `GenerationService`
catches the failure and returns a report with no `screenshots` field
rather than failing the whole request — see `docs/SCREENSHOTS.md`.

**Sandboxed dev/CI environments:** Playwright downloads Chromium from
`cdn.playwright.dev`. If that host isn't reachable (restricted network
egress), the install step fails and screenshot capture will always
degrade to "no screenshots" in that environment — this was the case in
the sandbox this phase was built in, so screenshot capture itself was
verified with Playwright's browser API mocked, not a real Chromium
instance. Confirm one real run with actual Chromium before relying on
this in production.

**Docker:** if `backend/` ends up running inside its own container
(separate from the code-execution sandbox containers `PythonExecutor`
launches — see the Phase 4 section above), that image needs the Chromium
install step too, or Chromium needs to run outside the container with
Playwright configured to connect to it remotely
(`playwright.chromium.connect(...)`) — decide based on whatever
containerization approach the team lands on for deployment.

