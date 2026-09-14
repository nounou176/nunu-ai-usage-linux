# Codex Provider

NUNU supports OpenAI Codex usage monitoring.

An existing locally authenticated Codex profile can be referenced without
copying credentials into the NUNU configuration.

NUNU can also create isolated managed profiles for additional Codex accounts.

Usage retrieval is performed non-interactively so normal background refreshes
do not intentionally start login flows.

CodexBarCLI is used for quota retrieval and is installed separately from the
NUNU source code.
