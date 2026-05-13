# AI Sports Analyst Agent V7.2 Fast Track
# Codex 운영 매뉴얼 + 기획서 타임라인 + Day 1 실행 지시서

작성 기준: V7.1 운영 매뉴얼 + 현재 논의 반영
운영 기준: Codex 메인 개발자 + ChatGPT PM + GPT Analyst Fast Track
대상 독자: 초보/주니어 프로그래머, Codex 작업자, 프로젝트 운영자

---

## 0. 이 문서의 목적

이 문서는 `초대호 Codex`에게 바로 제공할 수 있는 프로젝트 운영 기준서다.
목표는 Codex가 프로젝트를 한 번에 크게 만들지 않고, 작은 단계로 안전하게 진행하도록 만드는 것이다.

이 문서의 기본 방향은 다음과 같다.

1. Codex는 실제 파일 생성/수정/테스트 실행을 담당한다.
2. ChatGPT는 PM/시니어 엔지니어로서 TASK 분해, Codex 프롬프트 작성, 오류 분석, 다음 작업 지정을 담당한다.
3. 사용자는 운영자이며, API 키/이메일/Secrets/결과 확인/최종 승인을 담당한다.
4. 서버, 데이터 수집, 송출, 저장은 코드가 담당한다.
5. 분석 설명, 라벨링, 우선순위 판단은 Fast Track 초본에서는 ChatGPT API가 담당할 수 있다.
6. GPT Analyst는 입력에 없는 선수명, 부상, 라인업, 날씨, 뉴스, 확률을 만들면 안 된다.
7. 모든 작업은 `NEXT TASK REMINDER`로 끝난다.

---

## 1. 프로젝트 한 줄 정의

AI Sports Analyst Agent는 하루 2회 스포츠 경기 분석 리포트를 자동 생성하고 이메일로 발송하는 시스템이다.

- East report: KBO, NPB, K League 중심
- West report: MLB, EPL, Serie A, LaLiga, UCL 중심
- 초기 목표: 완벽한 예측 모델이 아니라, 안정적인 자동 리포트 생성/발송/기록/감시

---

## 2. V7.2 Fast Track 핵심 변경

기존 V7.1은 다음 순서였다.

```text
Mock HTML → SendGrid → SQLite → API-Sports → Odds API → reference model → scoring → LLM reporter → Actions → Dry Run
```

V7.2 Fast Track은 초반 속도를 높이기 위해 다음 순서로 간다.

```text
Mock HTML
→ ReportInput / AnalysisOutput 계약
→ GPT Analyst + fallback analyst
→ Analysis Validator
→ SendGrid
→ SQLite
→ Live Collector 최소 연결
→ GitHub Actions + Healthchecks
→ Dry Run
→ deterministic model/scoring 고도화
```

즉, 초본에서는 모델/스코어링을 완성하기 전에 `GPT Analyst`를 임시 분석 엔진으로 둔다.

단, GPT Analyst는 사실 생성자가 아니다.
GPT Analyst는 정규화된 입력 JSON을 받아 분석 설명과 라벨을 생성하는 역할만 한다.

---

## 3. 역할 분담

| 역할 | 담당 | 책임 |
|---|---|---|
| PM/시니어 엔지니어 | ChatGPT | 설계, TASK 분해, Codex 프롬프트, 오류 분석, 다음 작업 지정 |
| 메인 개발자 | Codex | 파일 생성/수정, 테스트 실행, diff 요약, 버그 수정 |
| 운영자 | 사용자 | 터미널 실행 승인, API 키 관리, 결과 확인, 최종 승인 |
| 분석 엔진 | ChatGPT API | ReportInput 기반 AnalysisOutput 생성 |
| API 조사 | Perplexity 또는 공식 문서 | API-Sports, The Odds API, quota, endpoint 확인 |
| 실행 감시 | Healthchecks | 예약 실행 누락, 실패 ping 감시 |
| 작업 관리 | GitHub Issues/Projects | Phase, TASK, NEXT TASK 추적 |

---

## 4. Codex 작업 원칙

Codex에게 항상 지켜야 할 규칙:

1. 전체 프로젝트를 한 번에 만들지 않는다.
2. 한 TASK에서 수정 파일은 가능하면 1~3개, 최대 5개 이내로 제한한다.
3. 수정 전 변경 예정 파일을 먼저 말한다.
4. 실제 API 키, 이메일, 토큰, secrets를 코드에 쓰지 않는다.
5. 환경변수 이름만 `.env.example`에 둔다.
6. 없는 스포츠 정보를 지어내지 않는다.
7. 데이터가 없으면 `missing`, `unavailable`, `확인 불가`로 표시한다.
8. 금지 표현을 쓰지 않는다.
9. 모든 TASK 후 `ruff format .`, `ruff check .`, `pytest`를 실행하거나, 실행하지 못한 이유를 기록한다.
10. 모든 TASK는 `NEXT TASK REMINDER`로 끝난다.

금지 표현:

```text
무조건
필승
확실
100% 보장
돈 걸어도 됨
적중 확정
```

---

## 5. V7.2 Fast Track 데이터 흐름

```text
GitHub Actions or Local CLI
→ run_report.py
→ collectors or mock_data
→ contracts/report_input.py
→ analysis/gpt_analyst.py or fallback_analyst.py
→ analysis/analysis_validator.py
→ reports/report_builder.py
→ reports/html_renderer.py
→ messaging/sendgrid_mailer.py
→ evaluation/prediction_log.py
→ Healthchecks success/failure ping
```

초기에는 실제 서버를 따로 만들지 않는다.
한 저장소 안에서 책임만 분리한다.

초기 CLI 목표:

```bash
python run_report.py --region east --mode mock
python run_report.py --region west --mode mock
python run_report.py --region east --mode mock --send
python run_report.py --region west --mode live --send
```

---

## 6. GPT Analyst 규칙

GPT Analyst가 해도 되는 일:

- 경기별 분석 요약
- 추천 라벨 선택
- 데이터 부족 사유 정리
- 시장 괴리 설명
- 리스크/주의사항 작성
- 사용자가 읽기 쉬운 문장 생성

GPT Analyst가 하면 안 되는 일:

- 실제 경기 일정 수집
- odds 직접 조회
- 뉴스 크롤링
- 부상자 추측
- 라인업 추측
- 날씨 추측
- 확률 임의 생성
- 이메일 발송
- SQLite 저장
- GitHub Secrets 접근

GPT Analyst 출력은 JSON Schema 또는 Pydantic schema에 맞는 구조화 결과여야 한다.
validator를 통과하지 못하면 fallback analyst 결과를 사용한다.

---

## 7. 추천 저장소 구조

초기 Phase 0/1에서는 아래 전체 구조를 다 만들지 않는다.
Phase가 진행될 때 필요한 폴더만 만든다.

```text
ai-sports-agent/
  AGENTS.md
  TASKLOG.md
  README.md
  requirements.txt
  requirements-dev.txt
  pyproject.toml
  .pre-commit-config.yaml
  .env.example
  run_report.py
  docs/
    project_operations_manual_v7_2_fast_track.md
  src/
    schemas.py
    mock_data.py
    contracts/
      report_input.py
      analysis_output.py
    analysis/
      prompt_builder.py
      gpt_analyst.py
      fallback_analyst.py
      analysis_validator.py
    reports/
      html_renderer.py
      report_builder.py
      plain_text_renderer.py
    messaging/
      sendgrid_mailer.py
    evaluation/
      prediction_log.py
  tests/
  data/
    .gitkeep
  out/
    .gitkeep
  .github/workflows/
    report.yml
```

---

## 8. 전체 기획 타임라인

### Fast Track 14일 계획

| Day | 목표 | 완료 기준 |
|---|---|---|
| Day 1 | Phase 0 저장소 기본 구조 + Phase 1 착수 | AGENTS.md, README, TASKLOG, requirements, Ruff/pre-commit 준비 |
| Day 2 | Phase 1 Mock HTML 리포트 완료 | `out/report_east.html`, `out/report_west.html` 생성 |
| Day 3 | ReportInput/AnalysisOutput 계약 | Pydantic schema와 tests 통과 |
| Day 4 | GPT Analyst + fallback analyst | API key 없어도 fallback으로 분석 가능 |
| Day 5 | Analysis Validator | 금지 표현, unknown game_id, schema 오류 탐지 |
| Day 6 | Report Builder 연결 | AnalysisOutput 기반 HTML 리포트 생성 |
| Day 7 | SendGrid 발송 | mock 리포트 이메일 도착 |
| Day 8 | SQLite 저장 | data/sports_agent.sqlite에 기록 저장 |
| Day 9 | Live Collector 최소 연결 | 일부 fixture 또는 local JSON adapter 연결 |
| Day 10 | Odds API 최소 연결 | market_probability 일부 매칭 또는 unavailable 처리 |
| Day 11 | GitHub Actions 수동 실행 | workflow_dispatch 성공 |
| Day 12 | Healthchecks 연결 | start/success/fail ping 동작 |
| Day 13 | East/West 예약 Dry Run | mock/live 리포트 발송 상태 기록 |
| Day 14 | Dry Run 안정화 판단 | 실패 로그, TASKLOG, 다음 보강점 정리 |

### 30일 계획

| 기간 | 목표 | 완료 기준 |
|---|---|---|
| Week 1 | 뼈대 + Mock + GPT Analyst | HTML 생성, fallback 분석, validator |
| Week 2 | 발송/저장/자동화 | SendGrid, SQLite, GitHub Actions, Healthchecks |
| Week 3 | Live 데이터 안정화 | API-Sports/Odds/팀명 매칭/fallback 안정화 |
| Week 4 | 모델/스코어링 보강 | deterministic scoring, reference model, 리포트 품질 개선 |

### 90일 계획

| 기간 | 목표 |
|---|---|
| Day 1-14 | Fast Track MVP 생성 |
| Day 15-30 | dry run과 동양권 안정화 |
| Day 31-60 | 리그 확장, odds 매칭률 개선, 결과 수집 |
| Day 61-90 | 운영판 검토, 비용/성과/유지보수성 판단 |

---

## 9. Phase 0 상세 지시서

### 목표

Codex가 작업할 수 있는 기본 저장소와 지침 파일을 만든다.

### 수정 허용 파일

```text
AGENTS.md
TASKLOG.md
README.md
requirements.txt
requirements-dev.txt
.env.example
pyproject.toml
.pre-commit-config.yaml
```

### 수정 금지

```text
run_report.py
src/ 전체 앱 모듈
tests/ 전체 테스트 모듈
실제 API key 또는 이메일
```

### Phase 0 성공 기준

- 기본 파일 8개가 생성된다.
- README에 설치/실행/테스트/린트/포맷 명령어가 있다.
- AGENTS.md에 Codex 작업 규칙이 있다.
- AGENTS.md에 `NEXT TASK REMINDER` 형식이 있다.
- `.env.example`에는 환경변수 이름만 있고 실제 값은 없다.
- `requirements-dev.txt`에는 `pytest`, `ruff`, `pre-commit`이 있다.
- `pyproject.toml`에는 Ruff 설정이 있다.
- 다음 작업이 Phase 1 Mock HTML report임을 문서에 남긴다.

### Phase 0 Codex 프롬프트

```text
Current task: Phase 0 - Initialize repository basics for AI Sports Analyst Agent V7.2 Fast Track.

Follow the V7.2 Fast Track rules:
- Codex is the main developer.
- ChatGPT is the PM/senior engineer.
- The user is the operator.
- Do not create the full application yet.
- Do not hardcode secrets.
- End with NEXT TASK REMINDER.

Files allowed to edit:
- AGENTS.md
- TASKLOG.md
- README.md
- requirements.txt
- requirements-dev.txt
- .env.example
- pyproject.toml
- .pre-commit-config.yaml

Requirements:
- Do not create run_report.py yet.
- Do not create src/ application modules yet.
- Add beginner-friendly setup instructions.
- Add environment variable names only, not real secrets.
- Add Ruff and pre-commit config.
- AGENTS.md must include Codex working rules.
- AGENTS.md must include GPT Analyst Fast Track rules.
- AGENTS.md must include NEXT TASK REMINDER format.
- TASKLOG.md must include a Day 1 entry template.
- README.md must include setup, mock run plan, test, lint, and format commands.
- requirements.txt should include only runtime dependencies needed for early MVP.
- requirements-dev.txt should include pytest, ruff, and pre-commit.
- pyproject.toml must configure Ruff.

Required environment variable names:
- API_SPORTS_KEY
- ODDS_API_KEY
- SENDGRID_API_KEY
- REPORT_FROM_EMAIL
- REPORT_TO_EMAIL
- OPENAI_API_KEY
- HEALTHCHECKS_EAST_URL
- HEALTHCHECKS_WEST_URL

Done when:
- Base files are created.
- The next task is clearly Phase 1 mock HTML report.
- No secrets are hardcoded.
- ruff format ., ruff check ., and pytest are run if applicable.
- If tests do not apply yet, explain why.

At the end, include NEXT TASK REMINDER.
```

---

## 10. Phase 1 상세 지시서

### 목표

실제 API 없이 mock 데이터만으로 HTML 리포트를 생성한다.

### 생성 결과

```text
out/report_east.html
out/report_west.html
```

### 필수 라벨

```text
강력 추천 경기
고신뢰 분석 경기
시장 괴리 높은 경기
데이터 부족 경기
```

### 금지

```text
실제 API 호출 금지
SendGrid 발송 금지
SQLite 저장 금지
OpenAI API 호출 금지
실제 선수/부상/라인업/날씨/뉴스 생성 금지
```

### Phase 1-A: schema/mock data/renderer

수정 허용 파일:

```text
src/schemas.py
src/mock_data.py
src/reports/html_renderer.py
```

Codex 프롬프트:

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

### Phase 1-B: CLI 연결

수정 허용 파일:

```text
run_report.py
```

Codex 프롬프트:

```text
Current task: Phase 1-B - Wire mock HTML report generation CLI.

Follow AGENTS.md and V7.2 Fast Track rules.

Files allowed to edit:
- run_report.py

Requirements:
- Add CLI arguments:
  - --region east|west
  - --mode mock
- Only support mock mode for now.
- Load mock report data from src/mock_data.py.
- Render HTML using src/reports/html_renderer.py.
- Create out/ directory if missing.
- Write:
  - out/report_east.html for east
  - out/report_west.html for west
- Do not call any real API.
- Do not send email.
- Do not write to SQLite.
- Do not call OpenAI or any LLM.
- Print a clear success message with the output file path.

Done when:
- python run_report.py --region east --mode mock creates out/report_east.html.
- python run_report.py --region west --mode mock creates out/report_west.html.
- ruff format ., ruff check ., and pytest are run or the reason is recorded.

At the end, include NEXT TASK REMINDER.
```

---

## 11. Day 1 실행 프로그램

### Day 1 목표

1. 프로젝트 폴더에서 Git 상태 확인
2. Day 1 브랜치 생성
3. Codex 실행 준비
4. Phase 0 기본 파일 생성
5. 품질 명령 실행
6. Phase 0 commit/push
7. 가능하면 Phase 1-A 착수

---

### Step 0. 터미널 열기

VS Code/Cursor 기준:

```text
Terminal → New Terminal
```

또는 단축키:

```text
Windows: Ctrl + `
Mac: Control + `
```

---

### Step 1. 프로젝트 폴더인지 확인

터미널에서 한 줄씩 실행한다.

```bash
pwd
ls
git --version
git status
git branch --show-current
```

Windows PowerShell에서 `ls`가 불편하면:

```powershell
dir
```

`git status`에서 아래가 나오면 정상 Git repo다.

```text
On branch main
```

아래가 나오면 프로젝트 폴더가 아니다.

```text
fatal: not a git repository
```

---

### Step 2. Day 1 브랜치 만들기

현재 브랜치가 `main`이면:

```bash
git checkout -b day1-phase0
```

이미 브랜치가 있으면:

```bash
git checkout day1-phase0
```

확인:

```bash
git branch --show-current
```

정상 결과:

```text
day1-phase0
```

---

### Step 3. Codex 실행

프로젝트 루트에서:

```bash
codex
```

Codex가 열리면 Phase 0 프롬프트를 붙여넣는다.

주의:

- 터미널 명령어는 일반 터미널에 입력한다.
- 긴 작업 지시문은 Codex 입력창에 붙여넣는다.
- Codex가 파일 수정/명령 실행을 요청하면 내용을 보고 승인한다.

---

### Step 4. Phase 0 완료 후 파일 확인

```bash
git status
ls
```

확인해야 할 파일:

```text
AGENTS.md
TASKLOG.md
README.md
requirements.txt
requirements-dev.txt
.env.example
pyproject.toml
.pre-commit-config.yaml
```

---

### Step 5. 가상환경과 의존성 설치

Mac/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
```

---

### Step 6. 품질 명령 실행

```bash
ruff format .
ruff check .
pytest
```

테스트 파일이 아직 없어서 pytest가 실패하거나 `no tests ran`이면 TASKLOG에 기록한다.

예시:

```text
pytest 결과: Phase 0은 문서/설정 파일 중심이라 테스트 파일이 아직 없음. Phase 1 이후 테스트 추가 예정.
```

---

### Step 7. 변경 내용 확인

```bash
git diff --stat
git diff
git status
```

`git diff`에서 실제 secret이 들어갔는지 반드시 확인한다.

---

### Step 8. Phase 0 commit/push

```bash
git add AGENTS.md TASKLOG.md README.md requirements.txt requirements-dev.txt .env.example pyproject.toml .pre-commit-config.yaml
git commit -m "chore: initialize project basics"
git push -u origin day1-phase0
```

push에서 remote 에러가 나면 전체 로그를 ChatGPT에게 전달한다.

---

### Step 9. Phase 1 착수 여부 결정

Phase 0가 끝나고 시간이 있으면 Phase 1-A를 시작한다.

```text
Phase 1-A: src/schemas.py, src/mock_data.py, src/reports/html_renderer.py
Phase 1-B: run_report.py
```

Phase 1을 시작하기 전 브랜치를 새로 만들고 싶다면:

```bash
git checkout -b day1-phase1-mock-report
```

또는 같은 브랜치에서 계속 진행해도 된다.

---

## 12. Day 1 완료 체크리스트

### 필수

```text
[ ] git --version 확인
[ ] git status 확인
[ ] day1-phase0 브랜치 생성
[ ] Phase 0 Codex 프롬프트 전달
[ ] AGENTS.md 생성
[ ] TASKLOG.md 생성
[ ] README.md 생성
[ ] requirements.txt 생성
[ ] requirements-dev.txt 생성
[ ] .env.example 생성
[ ] pyproject.toml 생성
[ ] .pre-commit-config.yaml 생성
[ ] .env.example에 실제 secret 없음
[ ] README에 설치/테스트/린트/포맷 명령어 있음
[ ] AGENTS.md에 NEXT TASK REMINDER 형식 있음
[ ] ruff format . 실행
[ ] ruff check . 실행
[ ] pytest 실행 또는 미실행 사유 기록
[ ] git diff 확인
[ ] TASKLOG.md Day 1 기록
[ ] commit 완료
[ ] push 시도 또는 에러 기록
```

### 추가

```text
[ ] Phase 1-A 시작
[ ] src/schemas.py 생성
[ ] src/mock_data.py 생성
[ ] src/reports/html_renderer.py 생성
[ ] Phase 1-B 시작
[ ] run_report.py 생성
[ ] out/report_east.html 생성
[ ] out/report_west.html 생성
```

---

## 13. TASKLOG Day 1 템플릿

```markdown
# TASKLOG

## YYYY-MM-DD

### 오늘의 목표
- Phase 0 저장소 기본 구조 생성
- Codex 작업 규칙 정리
- Phase 1 Mock HTML 리포트 준비

### 완료한 작업
- AGENTS.md 생성
- README.md 생성
- TASKLOG.md 생성
- requirements 파일 생성
- Ruff / pre-commit 설정 생성
- .env.example 생성

### 변경된 파일
- AGENTS.md
- TASKLOG.md
- README.md
- requirements.txt
- requirements-dev.txt
- .env.example
- pyproject.toml
- .pre-commit-config.yaml

### 실행한 명령어
- git status
- git branch --show-current
- ruff format .
- ruff check .
- pytest

### 테스트 결과
- ruff format . 결과:
- ruff check . 결과:
- pytest 결과:

### 발생한 문제
- 없음 또는 에러 내용 기록

### 해결 방법
- 없음 또는 해결 내용 기록

### 남은 문제
- Phase 1 Mock HTML 리포트 생성 필요
- 실제 API 연결 전
- 이메일 발송 전
- SQLite 저장 전
- GPT Analyst 연결 전

### NEXT TASK REMINDER
다음 작업: Phase 1 Mock HTML 리포트 생성
다음 파일:
- run_report.py
- src/schemas.py
- src/mock_data.py
- src/reports/html_renderer.py
다음 명령어:
- python run_report.py --region east --mode mock
- python run_report.py --region west --mode mock
다음 Codex 프롬프트:
Current task: Phase 1-A - Create mock report schemas, mock data, and HTML renderer.
```

---

## 14. 에러 발생 시 ChatGPT에게 보낼 형식

```text
나는 초보 개발자이고 AI Sports Analyst Agent를 만들고 있어.

현재 Phase:
[Phase 0 또는 Phase 1]

방금 실행한 명령어:
[명령어 전체]

발생한 에러:
[에러 로그 전체]

관련 파일:
- [파일 1]
- [파일 2]

초보자 기준으로:
1. 에러 원인
2. 내가 먼저 확인할 것
3. Codex에게 줄 수정 프롬프트
4. 수정 후 실행할 명령어
5. NEXT TASK REMINDER
를 정리해줘.
```

---

## 15. 현재 기준 업데이트

이 프로젝트의 현재 운영 기준은 다음으로 업데이트한다.

```text
운영 버전: V7.2 Fast Track
개발 방식: Codex main developer 체계
분석 초본: GPT Analyst structured output 방식
초기 우선순위: Mock HTML → GPT Analyst contract → Validator → SendGrid → SQLite → Live Collector
Day 1 시작점: Phase 0 저장소 기본 구조
Day 1 다음점: Phase 1 Mock HTML report
```

---

## 16. NEXT TASK REMINDER

- Completed task: V7.2 Fast Track 운영 매뉴얼, 기획서 타임라인, Day 1 지시서 작성
- Changed files: 문서 초안만 작성됨
- Commands run: 없음
- Test result: 실행 전
- Remaining issue: 실제 repo에 `docs/project_operations_manual_v7_2_fast_track.md`로 반영 필요
- Next task: Phase 0 저장소 기본 구조 생성
- Files likely involved:
  - AGENTS.md
  - TASKLOG.md
  - README.md
  - requirements.txt
  - requirements-dev.txt
  - .env.example
  - pyproject.toml
  - .pre-commit-config.yaml
- Exact command to start:

```bash
git status
```

- Prompt to give Codex next:

```text
Current task: Phase 0 - Initialize repository basics for AI Sports Analyst Agent V7.2 Fast Track.
Follow the V7.2 Fast Track rules.
Create only the allowed base files.
Do not create the full application yet.
Do not hardcode secrets.
At the end, include NEXT TASK REMINDER.
```
