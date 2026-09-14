# Account Model

NUNU AI Usage Linux uses one generic account model for all AI providers.

## Goals

- Support multiple accounts per provider.
- Keep credentials out of config files.
- Allow different authentication mechanisms.
- Allow new providers without redesigning the UI.
- Hide provider-specific technical details from normal users.

## Account fields

- id: stable local identifier; must not contain email, token, or private data.
- provider: provider adapter identifier such as codex or claude.
- label: user-facing local name such as Personal, Work, or Client A.
- enabled: whether NUNU refreshes this account.
- show_on_widget: whether the account appears on the desktop widget.
- connection.type: managed or existing.
- connection.profile_id: internal profile identifier.
- connection.source: normally auto; provider adapters resolve the actual method.

## Credentials

Credentials must never be stored directly in public config files.

Do not store passwords, OAuth tokens, refresh tokens, cookies, browser sessions, or auth.json contents in config.

## Multiple accounts

Each account has an independent ID, profile, label, and connection state.
