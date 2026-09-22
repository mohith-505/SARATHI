# SARATHI Security Model

**V0.1 status: no tools, no shell, no filesystem writes.**

V0.1 does not execute any user- or model-controlled action beyond sending
text to a configured local or cloud LLM. There is no shell access, no file
mutation, no network calls beyond the configured provider endpoint.

## Forward-looking principles (enforced from V0.4 onward)

- Permission tiers T0–T3; see the project brief.
- LLM never gets unrestricted shell access.
- Secrets only via env vars / OS keyring; never in source.
- Audit log for all T1+ actions.
- Global emergency STOP.

## V0.1 secret handling

- No API keys are used by V0.1 (Ollama is local).
- `.env` and `config/local.toml` are gitignored.
- Logs must not include secrets.
