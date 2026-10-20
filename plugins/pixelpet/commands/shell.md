---
description: Show long-running PowerShell commands on PixelPet (or disconnect with --remove)
argument-hint: '[--remove]'
allowed-tools: Bash(python:*)
---

Run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/app/shell_setup.py" $ARGUMENTS
```

Relay the script output to the user in their language.
If it was connected, remind the user that it only applies to PowerShell windows opened from now on,
and that only commands running longer than 10 seconds appear on the pet.
