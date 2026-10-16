<p align="center"><img src="docs/images/banner.png" alt="PixelPet" width="720"></p>

<p align="center"><a href="README.md">한국어</a> · <b>English</b></p>

# PixelPet

A Claude Code plugin that puts a **90s-style pixel pet** in the corner of your screen and lets you know
when Claude Code or Codex finishes its work. Every session gets its own notification card, and when Claude
hands work off to Codex, you get **a single notification once everything — including the Codex work — is done**.

<p align="center"><img src="docs/images/demo.gif" alt="working → done animation" width="156">
&nbsp;&nbsp;&nbsp;<img src="docs/images/panel.png" alt="notification panel" width="300"></p>

> **Windows only** (Windows 10/11, Windows Terminal recommended). The UI text is in Korean.

## Features

- 🐱 **11 pixel pets**: cat · dog · chick · ghost · slime + WIBEE FRIENDS (Wibee · Dalbo · Bombom · Dugi · Cu · Puding) (right-click → 펫 고르기 / choose pet)
- 💻 **Working indicator**: a little laptop appears and the pet types away. The logo and speech bubble show who is working
  (Claude = orange `✳`, Codex = green `>_`, Claude waiting for Codex = hourglass)
- 🔔 **Per-session cards**: each card shows the session name (conversation topic). Up to 5 are visible; expand to scroll through all of them
- ❗ **Input-needed alerts**: permission prompts, multiple-choice questions, Codex approval requests
- 🧩 **Claude → Codex sub-tasks**: Codex runs started by Claude are attached under that Claude card
- ↗️ **Click to jump**: clicking a card brings that Claude Code terminal window/tab to the front
- 📊 **Usage tab**: how much of your Claude and Codex 5-hour / weekly plan limits you've used, and when they reset
- 🎵 Chiptune sounds, notifications on/off, clear all, collapse/expand, start with Windows

<p align="center"><img src="docs/images/states.png" alt="pet states" width="560"></p>

## Install

**Requirements**: Windows, [Python 3](https://www.python.org/downloads/) (check *Add python.exe to PATH*; includes tkinter), Claude Code

In Claude Code:

```
/plugin marketplace add gustjr7879/pixelpet-hyunskki
/plugin install pixelpet@pixelpet-hyunskki
```

Restart Claude Code and the pet appears. On first run it also registers itself to start with Windows
(you can turn that off from the right-click menu).

### Connect Codex too (optional)

Run once in Claude Code:

```
/pixelpet:codex
```

Then open `codex` once in a terminal and **approve (trust) the PixelPet hooks** in the hook review screen.
Codex only runs hooks you have approved. Until then, no Codex notifications arrive.

### Show Claude limits in the usage tab (optional)

<p align="center"><img src="docs/images/usage.png" alt="usage tab" width="300"></p>

Open the `사용량` (Usage) tab in the panel to see your plan limits. **Codex needs no setup**: PixelPet reads the logs Codex keeps on your machine.
For Claude, run this once in Claude Code:

```
/pixelpet:usage
```

This connects PixelPet to the limit info Claude Code passes to its status line. If you already have a status line, it keeps showing.
The numbers appear after Claude replies once. Only **Pro/Max subscriptions** report plan limits, so API-key logins show nothing.
To undo it, run `/pixelpet:usage --remove`.

## Usage

| Action | Result |
| --- | --- |
| Click the pet | Open/close the notification panel |
| Drag the pet | Move it (position is remembered) |
| Right-click the pet | Notifications on/off · sound · choose pet · clear all · test alert · start with Windows · quit |
| Click a card | Mark as read + jump to that Claude session's terminal |
| `▼ 자세히` (details) | Show the full message and all sub-tasks |
| `펼치기 ▼` / `접기 ▲` | Expand to scroll through more than 5 cards / collapse |
| `_` button / double-click title bar | Collapse ↔ expand the panel |
| `모두 정리` (clear all) | Clear every card that isn't in progress |
| `알림` / `사용량` tabs (alerts / usage) | Switch between the card list and Claude/Codex plan usage |

### Card types

| Card | When |
| --- | --- |
| ✔ 작업 완료! (done) | Claude or Codex finished replying (after all child Codex work is done) |
| ⌛ 작업중... / codex 작업 기다리는 중 | Progress only (no sound) |
| ! 확인이 필요해요! | Claude is waiting for a permission approval |
| ! 선택이 필요해요! | Claude is asking a multiple-choice question |
| ! 승인이 필요해요! | Codex approval request |

## Uninstall

```
/pixelpet:cleanup
/plugin uninstall pixelpet@pixelpet-hyunskki
```

`cleanup` stops the pet, removes the Codex hooks and the startup entry, restores your original status line, and deletes `%LOCALAPPDATA%\PixelPet`.

## Troubleshooting

- **No pet appears**: make sure `python --version` works in a terminal, then restart Claude Code.
- **No Codex notifications**: run `/pixelpet:codex` and approve the hooks inside `codex`.
- **No Claude usage shown**: run `/pixelpet:usage`, then send Claude a message. Only Pro/Max plans report limits.
- **Clicking a card doesn't jump**: jumping works for Claude Code sessions running in Windows Terminal or a console.
  Standalone Codex sessions and headless (`claude -p`) sessions can't be jumped to.
- Log file: `%LOCALAPPDATA%\PixelPet\data\pet.log`

## How it works

- Claude Code hooks (`SessionStart`, `UserPromptSubmit`, `Stop`, `Notification`, `PreToolUse:AskUserQuestion`)
  and Codex hooks (`UserPromptSubmit`, `Stop`, `PermissionRequest`) send events to the pet app on `127.0.0.1:47321`.
  Nothing leaves your machine.
- Usage: for Claude, the status line's `rate_limits` are saved to `%LOCALAPPDATA%\PixelPet\data` and read from there.
  For Codex, PixelPet reads the logs in `~/.codex/sessions`. Neither makes a network request.
- A Codex run started by Claude is linked to its Claude session through the inherited `CLAUDE_CODE_SESSION_ID` environment variable.
- The app runs from a copy in `%LOCALAPPDATA%\PixelPet`, refreshed automatically at the next session start after a plugin update.

## License

- Code: [MIT](LICENSE)
- Font: [Galmuri](https://github.com/quiple/galmuri) © Lee Minseo, SIL Open Font License 1.1 (`plugins/pixelpet/assets/LICENSE-Galmuri.txt`)
