# Multiple Accounts

NUNU supports multiple accounts for each provider.

Accounts may be either:

- existing local provider accounts
- isolated NUNU-managed provider profiles

Managed profiles are stored under:

    ~/.local/share/nunu-ai-usage-linux/profiles/

Removing an account from the NUNU configuration does not delete the managed
provider profile by default.

This allows account metadata to be removed from the widget without destroying
the underlying provider login session.
