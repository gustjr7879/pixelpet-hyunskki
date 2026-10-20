<p align="center"><img src="docs/images/banner.png" alt="PixelPet" width="720"></p>

<p align="center"><b>한국어</b> · <a href="README.en.md">English</a></p>

# PixelPet

Claude Code와 Codex의 작업이 끝나면 화면 구석의 **90년대 픽셀 펫**이 알려주는 Claude Code 플러그인이에요.
여러 세션을 동시에 돌려도 세션마다 알림 카드가 따로 생기고, Claude가 Codex를 불러 일을 맡긴 경우엔
**Codex 작업까지 모두 끝났을 때 한 번만** 알려줘요.

<p align="center"><img src="docs/images/demo.gif" alt="작업중 → 완료 애니메이션" width="156">
&nbsp;&nbsp;&nbsp;<img src="docs/images/panel.png" alt="알림함" width="300"></p>

> **Windows 전용**이에요. (Windows 10/11, Windows Terminal 권장)

## 주요 기능

- 🐱 **픽셀 펫 11종**: 고양이 · 강아지 · 병아리 · 유령 · 슬라임 + 위비프렌즈(위비 · 달보 · 봄봄 · 두기 · 큐 · 푸딩) (우클릭 → 펫 고르기)
- 💻 **작업 중 표시**: 펫 앞에 노트북이 생기고 타이핑해요. 로고와 말풍선으로 누가 일하는지 보여줘요
  (Claude = 주황 `✳`, Codex = 초록 `>_`, 일반 명령 = 파랑 `$_`, Claude가 Codex를 기다리는 중 = 모래시계)
- 🔔 **세션별 알림 카드**: 카드 상단에 세션 이름(대화 주제)이 표시돼요. 최대 5개가 보이고, `펼치기`를 누르면 스크롤로 전부 볼 수 있어요
- ⌨️ **일반 명령도 표시 (선택)**: PowerShell에서 10초 넘게 걸리는 스크립트·빌드도 카드로 보이고, 끝나거나 실패하면 알려줘요
- ❗ **입력이 필요할 때도 알림**: 권한 승인, 선택지 질문, Codex 승인 요청
- 🧩 **Claude → Codex 서브 알림**: Claude가 실행한 Codex 작업이 카드 아래 서브 항목으로 붙어요
- ↗️ **클릭하면 해당 세션으로 이동**: 카드를 클릭하면 그 Claude Code가 열린 터미널 창이나 탭이 앞으로 와요
- 📊 **사용량 탭**: Claude·Codex 요금제의 5시간/주간 한도를 몇 % 썼는지, 언제 초기화되는지 보여줘요
- 🎵 칩튠 효과음, 알림 ON/OFF, 모두 정리, 축소/확대, 윈도우 시작 시 자동 실행

<p align="center"><img src="docs/images/states.png" alt="펫 상태 표" width="640"></p>

## 설치

**필요한 것**: Windows, [Python 3](https://www.python.org/downloads/) (설치 시 *Add python.exe to PATH* 체크, tkinter 포함), Claude Code

Claude Code에서:

```
/plugin marketplace add gustjr7879/pixelpet-hyunskki
/plugin install pixelpet@pixelpet-hyunskki
```

Claude Code를 다시 시작하면 펫이 나타나요. 처음 실행할 때 윈도우 시작프로그램에도 등록되고, 우클릭 메뉴에서 끌 수 있어요.

### Codex도 연결하기 (선택)

Codex 알림을 받으려면 Claude Code에서 한 번 실행하세요:

```
/pixelpet:codex
```

그다음 터미널에서 `codex`를 한 번 열고, **훅 검토 화면에서 PixelPet 훅을 승인**하세요.
Codex는 승인된 훅만 실행해요. 승인하기 전에는 Codex 알림이 오지 않아요.

### PowerShell 명령도 표시하기 (선택)

Claude·Codex가 아닌 일반 스크립트나 빌드(`python train.py`, `npm run build` 등)도 펫에 보이게 하려면 한 번 실행하세요:

```
/pixelpet:shell
```

PowerShell 프로필(`$PROFILE`)에 연결 줄을 추가해요. **새로 여는 PowerShell 창부터** 적용돼요.
10초 넘게 걸린 명령만 `SHELL` 카드로 보이고, 끝나면 완료/실패(종료 코드)를 알려줘요. 금방 끝나는 명령은 아무것도 안 떠요.
`claude`, `codex`, `ssh`, `vim` 같은 대화형 프로그램과 Ctrl+C로 멈춘 명령은 알리지 않아요.
되돌리려면 `/pixelpet:shell --remove`를 실행하세요.

### 사용량 탭에 Claude 한도 표시하기 (선택)

<p align="center"><img src="docs/images/usage.png" alt="사용량 탭" width="300"></p>

알림함의 `사용량` 탭을 누르면 한도 사용량이 보여요. **Codex는 따로 설정할 필요가 없어요.** Codex가 로컬에 남기는 기록을 읽어요.
Claude는 Claude Code에서 한 번 실행하세요:

```
/pixelpet:usage
```

Claude Code가 상태줄(status line)에 넘겨주는 한도 정보를 받아 오도록 연결해요. 쓰던 상태줄이 있으면 그대로 보여요.
Claude가 한 번 답하면 숫자가 나타나요. 한도 정보는 **Pro/Max 구독**에서만 나와요. API 키로 로그인했다면 표시되지 않아요.
되돌리려면 `/pixelpet:usage --remove`를 실행하세요.

## 사용법

| 동작 | 결과 |
| --- | --- |
| 펫 클릭 | 알림함 열기/닫기 |
| 펫 드래그 | 위치 이동 (기억됨) |
| 펫 우클릭 | 알림 ON/OFF · 소리 · 펫 고르기 · 모두 정리 · 테스트 알림 · 시작 시 실행 · 종료 |
| 카드 클릭 | 읽음 처리 + 해당 Claude 세션 터미널로 이동 |
| `▼ 자세히` | 메시지와 서브 작업 전체 보기 |
| `펼치기 ▼` / `접기 ▲` | 5개 넘는 알림을 스크롤로 보기 |
| `_` 버튼 / 제목 표시줄 더블클릭 | 알림함 축소 ↔ 확대 |
| `모두 정리` | 진행 중이 아닌 알림 전부 정리 |
| `알림` / `사용량` 탭 | 알림 목록 ↔ Claude·Codex 한도 사용량 화면 전환 |

### 알림 종류

| 카드 | 언제 |
| --- | --- |
| ✔ 작업 완료! | Claude 또는 Codex가 답변을 마쳤을 때 (하위 Codex 작업까지 모두 끝난 뒤) |
| ⌛ 작업중... / codex 작업 기다리는 중 | 진행 상황 표시 (알림음 없음) |
| ! 확인이 필요해요! | Claude 권한 승인 대기 |
| ! 선택이 필요해요! | Claude가 선택지 질문을 보여줄 때 |
| ! 승인이 필요해요! | Codex 승인 요청 |
| ✔ 명령 완료! / ! 명령 실패 | PowerShell에서 10초 넘게 걸린 명령이 끝났을 때 (`/pixelpet:shell` 연결 시) |

## 제거

```
/pixelpet:cleanup
/plugin uninstall pixelpet@pixelpet-hyunskki
```

`cleanup`은 펫을 끄고, Codex 훅·PowerShell 연결과 시작프로그램 등록을 해제하고, 상태줄을 원래대로 되돌린 뒤 `%LOCALAPPDATA%\PixelPet`을 삭제해요.

## 문제 해결

- **펫이 안 보여요**: 터미널에서 `python --version`이 되는지 확인하세요. 그다음 Claude Code를 다시 시작하세요.
- **Codex 알림이 안 와요**: `/pixelpet:codex`를 실행한 뒤 `codex`에서 훅을 승인했는지 확인하세요.
- **Claude 사용량이 안 나와요**: `/pixelpet:usage`를 실행한 뒤 Claude에게 메시지를 한 번 보내세요. Pro/Max 구독만 한도 정보가 있어요.
- **카드를 클릭해도 이동하지 않아요**: 이동은 Windows Terminal / 콘솔에서 실행 중인 Claude Code 세션만 돼요.
  Codex 단독 세션이나 헤드리스(`claude -p`) 세션은 이동하지 않아요.
- **PowerShell 명령이 안 보여요**: `/pixelpet:shell` 후 **새** PowerShell 창에서 실행했는지, 10초 넘게 걸렸는지 확인하세요.
  실행 정책이 `Restricted`면 프로필이 안 읽혀요 (`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`).
- 로그 파일: `%LOCALAPPDATA%\PixelPet\data\pet.log`

## 동작 방식

- Claude Code 훅(`SessionStart`, `UserPromptSubmit`, `Stop`, `Notification`, `PreToolUse:AskUserQuestion`)과
  Codex 훅(`UserPromptSubmit`, `Stop`, `PermissionRequest`)이 이벤트를 `127.0.0.1:47321`의 펫 앱으로 보내요.
  네트워크 밖으로는 아무것도 보내지 않아요.
- 사용량: Claude는 상태줄 입력의 `rate_limits`를 `%LOCALAPPDATA%\PixelPet\data`에 저장해서 읽고,
  Codex는 `~/.codex/sessions`의 기록을 읽어요. 어느 쪽도 네트워크 요청을 하지 않아요.
- PowerShell 연결은 PSReadLine이 명령을 실행하기 직전과 다음 프롬프트가 뜰 때 명령 내용·종료 코드를 펫 앱에 보내요 (역시 로컬로만).
- Claude가 실행한 Codex는 Claude가 넘겨주는 환경변수(`CLAUDE_CODE_SESSION_ID`)로 같은 세션에 묶여요.
- 실행 파일은 `%LOCALAPPDATA%\PixelPet`에 복사해서 실행해요. 플러그인을 업데이트하면 다음 세션을 시작할 때 자동으로 갱신돼요.

## 라이선스

- 코드: [MIT](LICENSE)
- 폰트: [Galmuri](https://github.com/quiple/galmuri) © Lee Minseo, SIL Open Font License 1.1 (`plugins/pixelpet/assets/LICENSE-Galmuri.txt`)
