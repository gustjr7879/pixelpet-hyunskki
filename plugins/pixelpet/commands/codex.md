---
description: Connect (or disconnect with --remove) PixelPet to Codex CLI hooks
argument-hint: '[--remove]'
allowed-tools: Bash(python:*)
---

Run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/app/codex_setup.py" $ARGUMENTS
```

Relay the script output to the user in their language.
If hooks were added, remind the user that Codex only runs new hooks after they are approved:
they should open `codex` once in a terminal and approve (trust) the PixelPet hooks in the hook review screen.
