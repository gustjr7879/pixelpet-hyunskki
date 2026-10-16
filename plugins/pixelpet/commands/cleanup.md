---
description: Stop PixelPet and remove its Codex hooks, autostart entry and runtime files
allowed-tools: Bash(python:*)
---

Run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/app/cleanup.py"
```

Relay the script output to the user in their language.
Tell them the plugin itself can then be removed with `/plugin uninstall pixelpet@pixelpet-hyunskki`.
