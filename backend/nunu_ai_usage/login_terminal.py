import shutil
import subprocess

from nunu_ai_usage.managed_login import build_login


def find_terminal():
    terminal = shutil.which("gnome-terminal")

    if terminal:
        return terminal, "gnome"

    terminal = shutil.which("x-terminal-emulator")

    if terminal:
        return terminal, "generic"

    raise RuntimeError("No supported terminal emulator found")


def build_terminal_login(account):
    command, env, profile = build_login(account)
    terminal, kind = find_terminal()

    if kind == "gnome":
        terminal_command = [
            terminal,
            "--",
            *command,
        ]
    else:
        terminal_command = [
            terminal,
            "-e",
            *command,
        ]

    return terminal_command, env, profile


def launch_terminal_login(account):
    terminal_command, env, profile = build_terminal_login(account)

    process = subprocess.Popen(
        terminal_command,
        env=env,
    )

    return process, profile
