import subprocess
import threading
import time

from nunu_ai_usage.browser_capture import (
    cleanup_browser_capture,
    create_browser_capture,
    read_browser_url,
)
from nunu_ai_usage.login_challenge import parse_codex_challenge
from nunu_ai_usage.managed_login import build_login


class LoginRuntime:
    def __init__(self, session):
        self.session = session
        self.process = None
        self.thread = None
        self.capture_thread = None
        self._buffer = ""
        self._capture_done = False
        self._capture_root = None
        self._capture_file = None

    def start(self):
        if self.session.provider not in ("codex", "claude"):
            raise ValueError("Unsupported login provider")

        command, env, _ = build_login(self.session.account)

        if self.session.provider == "claude":
            root, wrapper, capture = create_browser_capture()
            self._capture_root = root
            self._capture_file = capture
            env["BROWSER"] = str(wrapper)

        self.process = subprocess.Popen(
            command,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        self.session.process_pid = self.process.pid
        self.session.state = "waiting_for_challenge"

        self.thread = threading.Thread(
            target=self._read_output,
            daemon=True,
        )
        self.thread.start()

        if self.session.provider == "claude":
            self.capture_thread = threading.Thread(
                target=self._watch_browser_capture,
                daemon=True,
            )
            self.capture_thread.start()

        return self

    def _read_output(self):
        if self.process is None or self.process.stdout is None:
            return

        for line in self.process.stdout:
            if self.session.provider != "codex":
                continue

            if self._capture_done:
                continue

            self._buffer += line
            url, code = parse_codex_challenge(self._buffer)

            if url:
                self.session.login_url = url

            if code:
                self.session.user_code = code

            if url or code:
                self.session.state = "waiting_for_user"

            if self.session.login_url and self.session.user_code:
                self._capture_done = True
                self._buffer = ""

    def _watch_browser_capture(self):
        while self.process is not None:
            if self._capture_file is not None:
                url = read_browser_url(self._capture_file)

                if url:
                    self.session.login_url = url
                    self.session.state = "waiting_for_user"
                    return

            if self.process.poll() is not None:
                return

            time.sleep(0.1)

    def wait_for_challenge(self, timeout=20):
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if self.session.provider == "codex":
                ready = (
                    self.session.login_url is not None
                    and self.session.user_code is not None
                )
            else:
                ready = self.session.login_url is not None

            if ready:
                return True

            if self.process and self.process.poll() is not None:
                return False

            time.sleep(0.1)

        return False

    def is_running(self):
        return (
            self.process is not None
            and self.process.poll() is None
        )

    def cleanup(self):
        if self._capture_root is not None:
            cleanup_browser_capture(self._capture_root)
            self._capture_root = None
            self._capture_file = None

    def terminate(self):
        if self.is_running():
            self.process.terminate()

            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)

        self.cleanup()


def start_login_runtime(session):
    return LoginRuntime(session).start()
