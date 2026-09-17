import shutil
import subprocess
import tempfile

from app.core.errors import AppError


def parse_doc(content: bytes) -> str:
    """Extracts text from a legacy (pre-2007) .doc file via antiword.

    There's no good pure-Python reader for the old binary .doc format, so
    this shells out to `antiword`. If it isn't installed on the host, we
    fail with a clear, actionable message rather than crashing or guessing
    at the content — see docs/DEPLOYMENT.md for the required system package.
    """
    if shutil.which("antiword") is None:
        raise AppError(
            "LAB_READ_FAILED",
            "Legacy .doc files aren't supported on this server right now. "
            "Please save the lab as .docx or .pdf and re-upload.",
        )

    with tempfile.NamedTemporaryFile(suffix=".doc") as tmp:
        tmp.write(content)
        tmp.flush()
        try:
            result = subprocess.run(
                ["antiword", tmp.name],
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise AppError("LAB_READ_FAILED", "Could not read the .doc file.") from exc

    text = result.stdout.strip()
    if not text:
        raise AppError("LAB_READ_FAILED", "The .doc file appears to be empty.")
    return text
