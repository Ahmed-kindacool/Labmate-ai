# Architecture

> **Updated during migration** from a single Next.js app to a split
> React (Vite) frontend + FastAPI backend. See `../MIGRATION_NOTES.md` for
> the file-by-file mapping.

## Principle

Use a **modular monolith** — one backend service, no microservices.

This project is intentionally small. Do not create microservices or a complicated backend.

The architecture should still have clean boundaries so the code is easy to maintain.

## High-level architecture

```text
              React (Vite) UI
                    │
                    ▼   HTTP (multipart/form-data)
        POST /api/v1/labs/generate
                    │
                    ▼
           GenerationService
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
   Lab Parser    AI Service   Template Service
       │            │            │
       └────────────┼────────────┘
                    ▼
             Code Executor
                    │
                    ▼
             Screenshot Service
                    │
                    ▼
             DOCX Generator
                    │
                    ▼
                 Download
```

## Folder structure

```text
frontend/
└── src/
    ├── App.tsx
    ├── components/
    │   ├── ui/
    │   ├── lab-form/
    │   └── generation/
    ├── lib/
    │   └── utils.ts
    └── types/

backend/
└── app/
    ├── main.py
    ├── routes/
    │   ├── health.py
    │   └── lab.py
    ├── schemas/
    │   ├── student.py
    │   ├── generate.py
    │   └── lab.py
    ├── services/
    │   └── generation_service.py
    ├── validation/
    │   └── lab_file.py
    ├── core/
    │   ├── config.py
    │   └── errors.py
    ├── domain/
    │   └── university.py
    ├── parsing/          # Phase 2
    ├── ai/               # Phase 3
    ├── execution/        # Phase 4
    ├── screenshots/      # Phase 5
    ├── templates_registry/ # Phase 6
    └── documents/        # Phase 7

templates/
├── air/
├── bahria/
└── nust/

backend/tests/
```

Adjust the exact structure when implementing if a simpler organization is clearly better.

## Design patterns

Do not use patterns just for the sake of using patterns. Use them where they solve a real problem.

### Service Layer

`GenerationService` coordinates the complete workflow.

The API route should remain thin — routing and validation only, no business logic.

### Strategy Pattern

Use separate executor strategies:

```text
CodeExecutor
├── PythonExecutor
├── CppExecutor
├── JavaExecutor
└── UnsupportedExecutor
```

Start with Python. `CodeExecutor` is defined as an interface in
`backend/app/execution/` — `PythonExecutor` currently raises "not
implemented"; no sandbox exists yet.

### Adapter Pattern

Hide third-party services behind interfaces.

For example:

```python
from abc import ABC, abstractmethod

class AIProvider(ABC):
    @abstractmethod
    async def generate_solution(self, lab_content: str) -> dict:
        ...
```

This keeps the rest of the application independent from a specific AI SDK.

### Template Registry

Use a simple registry for university templates:

```python
class University(str, Enum):
    AIR = "air"
    BAHRIA = "bahria"
    NUST = "nust"
```

Adding a university later should mainly involve adding its template/logo and registry entry.

## Important separation

AI decides:

> What should be in the report?

Application code decides:

> How should the report look?

Therefore:

```text
AI
 ↓
Structured content
 ↓
DOCX renderer
 ↓
University template
```

Do not ask AI to generate the DOCX formatting.

## Keep it simple

Do NOT add:

- Database
- Authentication
- Redis
- Queues
- Microservices
- Event buses
- Complex agent frameworks
- Unnecessary repositories/interfaces
- Dozens of configuration files

A clean modular monolith is enough.
