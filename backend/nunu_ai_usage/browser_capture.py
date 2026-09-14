import shlex
import shutil
import tempfile
from pathlib import Path


def create_browser_capture():
    root = Path(tempfile.mkdtemp(prefix="nunu-login-"))
    root.chmod(0o700)

    capture = root / "browser-url.txt"
    wrapper = root / "browser-wrapper"

    target = shlex.quote(str(capture))

    wrapper.write_text(
        "#!/bin/sh\n"
        "umask 077\n"
        "printf '%s\\n' \"$@\" > " + target + "\n",
        encoding="utf-8",
    )

    wrapper.chmod(0o700)
    return root, wrapper, capture


def read_browser_url(capture):
    if not capture.exists():
        return None

    for line in capture.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        value = line.strip()
        if value.startswith(("https://", "http://")):
            return value

    return None


def cleanup_browser_capture(root):
    shutil.rmtree(root, ignore_errors=True)
