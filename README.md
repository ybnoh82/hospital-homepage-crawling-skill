# 병원 홈페이지 크롤링 스킬

미용·성형·피부과 병원의 **공식 홈페이지**를 크롤링해, 운영정보·의료진·취급 제품/장비·시술·가격·다국어 지원 여부를 추출하고 정규화된 JSON으로 만드는 Claude Code 스킬입니다.

## 왜 만드나

플랜닥스는 에스테틱 제품(톡신·필러·스킨부스터)을 병원에 판매합니다. 영업·마케팅 전략에는 병원별 상세정보가 필요하지만, 현재는 공공DB의 기본정보(이름·주소·좌표)만 보유하고 있습니다. 이 스킬은 그 공백을 홈페이지 크롤링으로 채웁니다.

추출 결과는 사이트 표기를 [참조 카탈로그](.claude/skills/hospital-homepage-crawl/reference/)(에스테틱 제품 124종·장비 46종)에 매칭해, 어떤 병원이 어떤 제품·장비를 취급하는지 구조화합니다.

> 현재 단계 목표는 **병원 1개에 대해 신뢰할 수 있는 완성도·정확도**를 달성하는 것입니다. 품질이 검증되면 약 8,000개 병원으로 확대합니다.

## 동작 방식

이 저장소의 핵심은 일반 프로그램이 아니라 **Claude Code 스킬**입니다. Claude Code가 Playwright MCP(브라우저 자동화)로 홈페이지를 직접 방문해 데이터를 뽑습니다.

```
data/*.csv (병원 기본정보)  ─┐
                            ├─►  홈페이지 크롤링 (Playwright MCP)  ─►  output/{병원이름}_{병원ID}.json
참조 카탈로그 (제품·장비)    ─┘
```

`main.py`와 `claude-agent-sdk` 의존성은 향후 다수 병원 일괄 처리를 위한 **SDK 러너 자리표시(스텁)**이며 아직 구현되지 않았습니다.

## 사용법

### 1. 환경 준비 (uv, Python 3.14)

```bash
uv sync
```

### 2. 크롤링 실행

Claude Code에서 스킬을 호출합니다.

```
/hospital-homepage-crawl
```

병원 기본정보(이름·주소·홈페이지 URL 등, `data/beauty_hospitals_gangnam.csv` 형식)를 주면, 스킬이 홈페이지를 방문해 `output/`에 정규화 JSON을 저장합니다. 자세한 크롤링 규칙·판단 기준은 [`SKILL.md`](.claude/skills/hospital-homepage-crawl/SKILL.md)에 정리돼 있습니다.

## 저장소 구조

| 경로 | 설명 |
|---|---|
| `.claude/skills/hospital-homepage-crawl/SKILL.md` | 스킬 운영 매뉴얼 (크롤링 규칙의 단일 출처) |
| `.claude/skills/.../reference/output_scheme.py` | 출력 스키마 (Pydantic, 권위 있는 정의) |
| `.claude/skills/.../reference/input_scheme.py` | 입력 스키마 |
| `.claude/skills/.../reference/aesthetic_*.json` | 제품·장비 매칭 카탈로그 |
| `.claude/skills/.../reference/sample_output.json` | 출력 예시 |
| `data/` | 입력 병원 목록(CSV) |
| `output/` | 크롤링 결과 JSON |

## 출력 검증

스키마나 출력을 수정한 뒤 정합성을 확인합니다.

```bash
uv run python -c "
import sys, glob, json; sys.path.insert(0,'.claude/skills/hospital-homepage-crawl/reference')
from output_scheme import HospitalResult
for f in ['.claude/skills/hospital-homepage-crawl/reference/sample_output.json', *glob.glob('output/*.json')]:
    HospitalResult.model_validate(json.load(open(f))); print('OK', f)
"
```

## 기여 시 유의사항

- **데이터는 공식 홈페이지에서만** 추출합니다. WebSearch는 홈페이지 URL을 찾는 용도로만 쓰고, 블로그·SNS·지도·포털 결과는 데이터 출처가 아닙니다.
- 스키마(`output_scheme.py`)를 바꾸면 `sample_output.json`과 기존 `output/*.json`을 함께 갱신합니다. 재크롤링은 비용이 크므로, 스키마 변경 반영은 기존 파일을 직접 마이그레이션하는 방식으로 처리합니다.

개발 시 추가 지침은 [`CLAUDE.md`](CLAUDE.md)를 참고하세요.
