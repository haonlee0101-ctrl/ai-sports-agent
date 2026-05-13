# TASKLOG

Use this file to record each day of work, commands run, and what should happen next.

## Day 1 Entry Template

```markdown
## YYYY-MM-DD

### 오늘의 목표
- Phase 0 저장소 기본 구조 생성
- Codex 작업 규칙 정리
- Phase 1 Mock HTML 리포트 준비

### 완료한 작업
- AGENTS.md 생성 또는 업데이트
- README.md 생성 또는 업데이트
- TASKLOG.md 생성 또는 업데이트
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
- .gitignore
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
pytest 결과: Phase 0은 문서/설정 파일 중심이라 아직 테스트 파일 없음. Phase 1 이후 테스트 추가 예정.
