# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 이 저장소의 정체

**일반적인 애플리케이션이 아니다.** 주 산출물은 미용·성형·피부과 병원의 공식 홈페이지를 (Playwright MCP 서버로) 크롤링해 정규화된 JSON 레코드를 만드는 **Claude Code 스킬**이다. 파이썬 패키지(`main.py`, `claude-agent-sdk` 의존성)는 향후 SDK 기반 배치 러너를 위한 **미완성 스텁**이며, 현재는 스킬을 Claude Code 안에서 대화형으로 실행한다.

사업 맥락: 플랜닥스는 에스테틱 제품(톡신·필러·스킨부스터)을 이런 병원에 판매하며, 공공DB 기본정보(이름·주소·좌표)를 넘어선 병원별 상세정보(운영정보·의료진·취급 제품/장비·시술·가격·다국어 지원)가 필요하다. 현재 목표는 **한 번에 병원 1개**에 대해 높은 정확도를 달성하는 것이고, 검증 후 약 8,000개로 확대한다.

## 스킬 (실제 산출물)

`.claude/skills/hospital-homepage-crawl/` — `/hospital-homepage-crawl`로 호출하거나 자동 트리거된다.

- `SKILL.md` — 오케스트레이터. 크롤링 관련 작업 전에 반드시 먼저 읽을 것. 배경·목적, 입력/출력 계약, ①URL 확보·검증과 ②`collect.md`로의 핸드오프, 불변 규칙을 담는다.
- `collect.md` — **홈페이지 데이터 수집 플레이북**(URL 확정 가정). 시행착오로 다듬은 규칙이 여기 담겨 있다(페이지 라우팅, 카탈로그 한↔영 교차 매칭, 이미지 전용 가격의 vision 판독, 가격 출처로서의 비급여진료비용 페이지, 실제 장비명을 가리는 자체 브랜드 시술명, 정규화·완전성·notes·마무리 등). SKILL.md §2가 URL 확정 후 이 파일을 읽어 따른다.
- `reference/output_scheme.py` — **권위 있는 출력 스키마**(Pydantic). `HospitalResult`가 최상위 출력 모델.
- `reference/input_scheme.py` — `HospitalInput`, 병원별 입력 계약.
- `reference/aesthetic_products.json`(124개) / `aesthetic_equipments.json`(46개) — 사이트 텍스트를 대조하는 매칭 카탈로그.
- `reference/sample_output.json` — 스키마와 항상 일치시키는 참조 출력.

데이터 흐름: `data/*.csv`(병원 기본정보) + 참조 카탈로그 → Playwright MCP로 홈페이지 1곳 크롤링 → 정규화된 `HospitalResult` JSON을 `output/{병원이름}_{병원ID}.json`에 저장.

## 불변 규칙 — 깨지 말 것

- **홈페이지 전용.** 데이터는 병원 공식 홈페이지에서만 추출한다. WebSearch는 홈페이지 URL을 찾거나 검증하는 용도로만 쓰며, 블로그·SNS·지도·포털 결과는 데이터 출처가 아니다.
- **스키마·샘플·기존 출력은 함께 움직인다.** `output_scheme.py`를 바꾸면 `reference/sample_output.json`을 갱신하고 기존 `output/*.json`을 in-place로 마이그레이션한다(재크롤링은 비용이 드니, 스키마 반영 목적의 재크롤링은 절대 하지 않는다). 변경 후 항상 스키마로 검증한다(아래 참조).
- **`run_meta` 및 비용/시간 필드는 에이전트가 채우지 않는다** — 아직 만들지 않은 SDK 러너용으로 남겨졌다가 라이브 스키마에서 제거됐다. 에이전트가 채우는 필드로 되살리지 말 것.
- 스킬은 크롤링 종료 시 Playwright 브라우저를 닫고(`browser_close`) 임시 아티팩트(`.playwright-mcp/`, 캡처 이미지)를 정리해야 한다.

## 명령어

uv 프로젝트다(Python 3.14).

```bash
uv sync                       # .venv에 의존성 설치
uv run main.py                # 패키지 엔트리포인트 실행 (현재는 스텁)
uv run ruff check .           # 린트
uv run ruff format .          # 포맷
```

스키마/출력 정합성 검증(스키마나 출력을 수정한 뒤):

```bash
uv run python -c "
import sys, glob, json; sys.path.insert(0,'.claude/skills/hospital-homepage-crawl/reference')
from output_scheme import HospitalResult
for f in ['.claude/skills/hospital-homepage-crawl/reference/sample_output.json', *glob.glob('output/*.json')]:
    HospitalResult.model_validate(json.load(open(f))); print('OK', f)
"
```

테스트 스위트는 없다.

## 참고 / 주의

- `.mcp.json`은 `playwright` MCP 서버(`npx @playwright/mcp@latest`)만 설정한다 — 이것이 크롤링 엔진이다.
- 라이브 스키마는 Pydantic `reference/output_scheme.py`(및 `input_scheme.py`)이며, 별도의 JSON-Schema 파일은 없다.
- 산출된 출력에서 `crawl_metadata.notes`는 절대 비워두지 않는다 — 가격 출처, 매칭/보류 항목, 별도 도메인·정책 결정, 미방문 영역을 기록한다(SKILL.md가 강제).
