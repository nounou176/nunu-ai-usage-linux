import re

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
URL_RE = re.compile(r"https?://[^\s]+")
CODE_RE = re.compile(r"[A-Z0-9]{3,8}(?:-[A-Z0-9]{3,8})+")


def strip_ansi(text):
    return ANSI_RE.sub("", text or "")


def parse_codex_challenge(text):
    clean = strip_ansi(text)
    lines = [line.strip() for line in clean.splitlines()]

    url = None
    code = None

    for line in lines:
        for candidate in URL_RE.findall(line):
            if "auth.openai.com" in candidate:
                url = candidate.rstrip(".,)")
                break
        if url:
            break

    for index, line in enumerate(lines):
        if "one-time code" not in line.lower():
            continue

        for candidate_line in lines[index + 1:index + 5]:
            match = CODE_RE.search(candidate_line)
            if match:
                code = match.group(0)
                break

        if code:
            break

    return url, code
