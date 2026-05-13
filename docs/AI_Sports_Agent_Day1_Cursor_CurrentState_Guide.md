# AI Sports Analyst Agent V7.2 Fast Track
# Day 1 Cursor + Codex 초보자 진행 가이드

작성 목적: 현재 사용자가 MacBook + Cursor에서 `ai-sports-agent` 폴더, Python 가상환경, Git 초기 커밋, `day1-phase0` 브랜치, `docs/` 폴더까지 만든 상태에서 바로 이어서 진행할 수 있도록 정리한다.

---

## 0. 현재 확인된 상태

스크린샷 기준 현재 상태:

```text
프로젝트 폴더: /Users/haon/Desktop/ai-sports-agent
터미널: Cursor Terminal
가상환경: (.venv) 활성화됨
현재 브랜치: day1-phase0
현재 보이는 파일/폴더: README.md, docs
```

완료된 것:

```text
[완료] ai-sports-agent 폴더 생성
[완료] Cursor에서 프로젝트 폴더 열기
[완료] Python 가상환경 .venv 생성
[완료] .venv 활성화
[완료] git init
[완료] 첫 README 커밋
[완료] day1-phase0 브랜치 생성
[완료] docs 폴더 생성
```

아직 해야 할 것:

```text
[필수] V7.2 운영 매뉴얼 .md 파일을 docs/에 넣기
[필수] Codex 실행
[필수] Phase 0 파일 생성
[필수] requirements 설치
[필수] ruff / pytest 실행
[필수] Phase 0 커밋
[선택] Phase 1-A 시작
```

---

## 1. 지금 바로 먼저 확인할 명령어

Cursor 터미널에서 아래를 한 줄씩 실행한다.

```bash
pwd
ls -la
git status
git branch --show-current
python --version
```

정상 기준:

```text
pwd 결과: /Users/haon/Desktop/ai-sports-agent
현재 브랜치: day1-phase0
python 버전: Python 3.11.x
```

`git status`에서 `.venv/`가 보이면 안 된다. `.venv/`가 보이면 `.gitignore`가 없거나 제대로 설정되지 않은 것이다.

---

## 2. V7.2 운영 매뉴얼 파일을 docs/에 넣기

ChatGPT가 제공한 파일을 다운로드한 뒤, 다운로드 폴더에 있다고 가정한다.

파일 이름:

```text
AI_Sports_Analyst_Agent_V7_2_FastTrack_Codex_Manual_Day1.md
```

복사 명령:

```bash
cp ~/Downloads/AI_Sports_Analyst_Agent_V7_2_FastTrack_Codex_Manual_Day1.md docs/project_operations_manual_v7_2_fast_track.md
```

확인:

```bash
ls docs
```

정상 결과:

```text
project_operations_manual_v7_2_fast_track.md
```

파일이 없다면 아직 다운로드하지 않은 것이다. 먼저 ChatGPT의 파일 링크에서 다운로드한다.

---

## 3. .gitignore 확인 또는 생성

가상환경 `.venv/`는 Git에 올리면 안 된다.

먼저 확인한다.

```bash
cat .gitignore
```

없다고 나오면 아래를 실행한다.

```bash
cat > .gitignore <<'GITIGNORE'
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd

# Virtual environment
.venv/
venv/

# Environment secrets
.env

# Test / lint cache
.pytest_cache/
.ruff_cache/
.mypy_cache/

# Local output
out/*.html

# Local database
data/*.sqlite
data/*.db

# OS files
.DS_Store
Thumbs.db
GITIGNORE
```

그다음 확인한다.

```bash
git status
```

`.venv/`가 나오면 안 된다.

---

## 4. Codex 실행 전 도구 확인

```bash
node --version
npm --version
codex --version
```

`codex`가 없다고 나오면 설치한다.

```bash
npm i -g @openai/codex
```

설치 후:

```bash
codex
```

---

## 5. Codex에게 줄 Phase 0 프롬프트

Codex가 열리면 아래를 그대로 붙여넣는다.

```text
Current task: Phase 0 - Initialize repository basics for AI Sports Analyst Agent V7.2 Fast Track.

You are the main developer.
ChatGPT is the PM/senior engineer.
The user is the operator.

Read docs/project_operations_manual_v7_2_fast_track.md if it exists.
If it does not exist, follow this prompt.

Files allowed to edit:
- AGENTS.md
- TASKLOG.md
- README.md
- requirements.txt
- requirements-dev.txt
- .env.example
- .gitignore
- pyproject.toml
- .pre-commit-config.yaml

Requirements:
- Do not create the full application yet.
- Do not create run_report.py yet.
- Do not create src modules yet.
- Do not create tests yet unless needed only for configuration validation.
- Add beginner-friendly setup instructions.
- Add environment variable names only, not real secrets.
- Add Ruff and pre-commit config.
- AGENTS.md must include Codex working rules.
- AGENTS.md must include GPT Analyst Fast Track rules.
- AGENTS.md must include NEXT TASK REMINDER format.
- TASKLOG.md must include a Day 1 entry template.
- README.md must include setup, mock run plan, test, lint, and format commands.
- requirements.txt should include pydantic only for now.
- requirements-dev.txt should include pytest, ruff, and pre-commit.
- pyproject.toml must configure Ruff.
- .gitignore must ignore .env, .venv, __pycache__, out/*.html, and local sqlite files.

Required environment variable names:
- API_SPORTS_KEY
- ODDS_API_KEY
- SENDGRID_API_KEY
- REPORT_FROM_EMAIL
- REPORT_TO_EMAIL
- OPENAI_API_KEY
- HEALTHCHECKS_EAST_URL
- HEALTHCHECKS_WEST_URL

Safety rules:
- Never hardcode API keys, emails, tokens, or secrets.
- Do not invent injuries, lineups, player names, weather, news, or probabilities.
- If data is missing, mark it as missing instead of guessing.
- Do not use forbidden expressions:
  - 무조건
  - 필승
  - 확실
  - 100% 보장
  - 돈 걸어도 됨
  - 적중 확정
- Treat reports as analysis, not betting advice.

Done when:
- Base files are created.
- The next task is clearly Phase 1 mock HTML report.
- No secrets are hardcoded.
- ruff format ., ruff check ., and pytest are run if applicable.
- If tests do not apply yet, explain why.

At the end, include NEXT TASK REMINDER.
```

---

## 6. Phase 0 후 직접 실행할 명령어

Codex가 끝나면 터미널에서 직접 실행한다.

```bash
ls -la
git status
```

보여야 하는 파일:

```text
AGENTS.md
TASKLOG.md
README.md
requirements.txt
requirements-dev.txt
.env.example
.gitignore
pyproject.toml
.pre-commit-config.yaml
docs/
```

의존성 설치:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
```

품질 검사:

```bash
ruff format .
ruff check .
pytest
```

`pytest`가 `no tests ran`이라고 나오면 Phase 0에서는 괜찮다. `TASKLOG.md`에 이유를 적는다.

```text
pytest 결과: Phase 0은 문서/설정 파일 중심이라 아직 테스트 파일 없음. Phase 1 이후 테스트 추가 예정.
```

---

## 7. Phase 0 커밋

변경 확인:

```bash
git diff --stat
git diff
```

커밋:

```bash
git add AGENTS.md TASKLOG.md README.md requirements.txt requirements-dev.txt .env.example .gitignore pyproject.toml .pre-commit-config.yaml docs
git commit -m "chore: initialize project basics"
```

---

## 8. Phase 1-A 시작 프롬프트

Phase 0 커밋이 끝나면 Codex에 아래를 붙여넣는다.

```text
Current task: Phase 1-A - Create mock report schemas, mock data, and HTML renderer.

Follow AGENTS.md and V7.2 Fast Track rules.

Files allowed to edit:
- src/schemas.py
- src/mock_data.py
- src/reports/html_renderer.py

Requirements:
- Use Pydantic schemas.
- Use mock data only.
- Do not call any real API.
- Do not send email.
- Do not write to SQLite.
- Do not call OpenAI or any LLM.
- Define beginner-friendly report and game schemas.
- Create sample east and west mock report data.
- Render a report payload into an HTML string.
- Include these labels:
  - 강력 추천 경기
  - 고신뢰 분석 경기
  - 시장 괴리 높은 경기
  - 데이터 부족 경기
- If data is missing, display it as missing instead of guessing.
- Do not use forbidden expressions:
  - 무조건
  - 필승
  - 확실
  - 100% 보장
  - 돈 걸어도 됨
  - 적중 확정

Done when:
- schemas.py defines the report and game structure.
- mock_data.py returns sample east and west report data.
- html_renderer.py renders a report payload into an HTML string.
- ruff format ., ruff check ., and pytest are run or the reason is recorded.

At the end, include NEXT TASK REMINDER.
```

---

## 9. Day 1 완료 기준

필수 완료:

```text
[ ] docs/project_operations_manual_v7_2_fast_track.md 추가
[ ] AGENTS.md 생성
[ ] TASKLOG.md 생성
[ ] README.md 업데이트
[ ] requirements.txt 생성
[ ] requirements-dev.txt 생성
[ ] .env.example 생성
[ ] .gitignore 확인
[ ] pyproject.toml 생성
[ ] .pre-commit-config.yaml 생성
[ ] pip install 완료
[ ] pre-commit install 완료
[ ] ruff format . 실행
[ ] ruff check . 실행
[ ] pytest 실행
[ ] Phase 0 commit 완료
```

가능하면 추가:

```text
[ ] Phase 1-A 시작
[ ] src/schemas.py 생성
[ ] src/mock_data.py 생성
[ ] src/reports/html_renderer.py 생성
```

---

## NEXT TASK REMINDER

- Completed task: 현재 상태 기준 Day 1 이어가기 문서 작성
- Current state: README.md, docs 폴더, day1-phase0 브랜치까지 완료
- Next task: V7.2 운영 매뉴얼 md 파일을 docs에 넣고 Codex로 Phase 0 실행
- Files likely involved:
  - docs/project_operations_manual_v7_2_fast_track.md
  - AGENTS.md
  - TASKLOG.md
  - README.md
  - requirements.txt
  - requirements-dev.txt
  - .env.example
  - .gitignore
  - pyproject.toml
  - .pre-commit-config.yaml
- Exact command to start:

```bash
cp ~/Downloads/AI_Sports_Analyst_Agent_V7_2_FastTrack_Codex_Manual_Day1.md docs/project_operations_manual_v7_2_fast_track.md
```
