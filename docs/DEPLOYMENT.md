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
