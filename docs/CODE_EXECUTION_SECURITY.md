# Code Execution Security

`backend/app/execution/python_executor.py` runs AI-generated Python code
from an untrusted source (a student's uploaded lab, processed by an AI
model) inside a disposable, sandboxed Docker container. This documents
the actual safety model, not an aspirational one -- every control below
is real code, not a plan.

## Threat model

The code being run is:

1. Written by an LLM, not a human who's already been vetted.
2. Ultimately derived from a file a random visitor uploaded --
   indirectly attacker-influenced, even if the AI itself behaves.
3. Executed with no human review in between.

So the goal isn't "sandbox nice code that might have bugs" -- it's
"assume any given execution could be actively adversarial, and bound the
damage regardless."

## What's spent per execution

```bash
docker run --rm --name labemate-exec-<random> \
  --network none \
  --cpus="0.5" \
  --memory="256m" \
  --pids-limit="50" \
  --read-only \
  -v <tmp-dir>:/app:ro \
  --workdir /app \
  python:3.11-slim \
  python /app/main.py
```

| Control | What it stops |
|---|---|
| `--network none` | Exfiltrating data, calling out to a C2 server, hitting internal network services, or using the sandbox as an SSRF relay. No network stack exists inside the container at all -- not a firewall rule, an absent interface. |
| `--cpus="0.5"`, `--memory="256m"` | A single execution burning the whole host's CPU or OOM-killing other work (including the FastAPI process itself). |
| `--pids-limit="50"` | A fork bomb -- without this, `while True: os.fork()` is a one-line DoS. |
| `--read-only` + `-v <tmp-dir>:/app:ro` | The code can't modify its own source, install packages, write to the image filesystem, or persist anything back to the host. The only writable filesystem inside the container is Docker's own ephemeral overlay (if anything) -- the mounted lab code itself is read-only. |
| A disposable, randomly-named container per execution | No shared state or leftover files between one student's report and the next. |
| `--rm` | Automatic cleanup on normal exit. |

## What Docker's own flags don't cover, closed separately

- **A hung process, or a client-side timeout that doesn't stop the
  server-side container.** `--rm` only cleans up when the container
  exits normally -- a `docker run` client process being killed on
  timeout does **not** stop the container still running in the Docker
  daemon. `_force_kill` explicitly runs `docker kill <container_name>`
  as a second step, so a timed-out script can't keep burning CPU/memory
  in an orphaned container after the request has already returned.
- **Unbounded output.** Docker bounds memory/CPU, not how much text a
  process can print. A trivial `while True: print("x")` would otherwise
  produce a response body limited only by available disk/memory on the
  response-buffering side. `_MAX_OUTPUT_CHARS = 20_000` truncates
  `stdout`/`stderr` independently of any Docker-level limit.
- **No safe sandbox available at all.** Per `PROJECT_SPEC.md` §4: *"If
  safe sandboxing is unavailable in a deployment environment, execution
  should be disabled rather than performed unsafely."* Enforced, not
  just documented: `_availability_error()` checks two independent gates
  -- `settings.code_execution_enabled` (defaults `False`) and a real
  `shutil.which("docker")` check -- and **both** must pass before any
  Docker command is even constructed. Either gap degrades to a real,
  honest `ExecutionStatus.UNSUPPORTED` result. There is no code path
  that falls back to running generated code directly on the host.

## What's deliberately out of scope

- **Only Python is implemented.** `UnsupportedExecutor` handles every
  other language honestly rather than attempting a less-hardened sandbox
  for each one.
- **No syscall-level sandboxing beyond Docker's own defaults** (no
  seccomp/AppArmor profile customization, no gVisor/Kata). Docker's
  container boundary is the security boundary here -- a reasonable
  trade-off for the actual threat model (arbitrary student-lab Python,
  not a bug-bounty target), but worth being explicit that it's a
  boundary, not perfect isolation from the host kernel.
- **No rate limiting across requests.** A burst of concurrent report
  generations could still launch many containers in parallel, each
  individually bounded but not collectively throttled.

## Verified

`backend/tests/test_execution.py` covers both availability gates, real
timeout + real container kill behavior, output truncation, and the
graceful-degradation path with no Docker installed -- the last one
verified for real (unmocked) in every sandbox this project has been
developed in, since none of them have Docker available either. See
`docs/PHASE9_TESTING.md` for the full test posture.
