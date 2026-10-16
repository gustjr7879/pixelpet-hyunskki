---
description: Show Claude plan usage in the PixelPet panel (or undo with --remove)
argument-hint: '[--remove]'
allowed-tools: Bash(python:*)
---

Run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/app/usage_setup.py" $ARGUMENTS
```

Relay the script output to the user in their language.
If the relay was installed, tell the user the numbers appear in the pet panel's 사용량 (Usage) tab
after Claude replies once, and that only Pro/Max subscriptions report plan limits (API-key logins show nothing).
Codex usage needs no setup: it is read from Codex's own local session logs.
