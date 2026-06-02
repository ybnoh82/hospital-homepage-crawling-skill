---
name: hospital-homepage-crawl
description: 미용·성형·피부과 병원의 공식 홈페이지를 Playwright MCP로 직접 방문해 운영정보·의료진·제품·장비·시술·가격을 추출하고, 에스테틱 제품/장비 카탈로그에 매칭한 정규화 JSON을 만든다.
---

# 병원 홈페이지 크롤링
단일 병원의 **공식 홈페이지에서만** 데이터를 수집해 [output_scheme.py](reference/output_scheme.py) 스키마를 따르는 정규화 JSON을 만든다.

작업은 두 단계다. 이 파일(SKILL.md)은 **오케스트레이터**로, ① 홈페이지 URL을 확보·검증한 뒤 ② URL이 확정되면 수집 플레이북 **[`collect.md`](collect.md)** 를 읽고 그 절차를 따라 데이터를 수집·정규화·저장한다. 시행착오로 다듬은 라우팅·매칭·가격(vision)·정규화 규칙은 모두 `collect.md`에 있다.

## 배경 및 목적

### 배경
플랜닥스는 에스테틱 제품(톡신, 필러, 스킨부스터)을 미용·성형 병원에 판매하는 사업을 운영한다.
영업 및 마케팅 전략 수립을 위해 타깃병원(피부과, 클리닉의원, 성형외과)의 상세 정보가 필요하지만, 현재 공공DB에서 확보한 기본정보(이름, 주소, 좌표)만 보유하고 있다.

### 목적
**병원 1개의 공식 홈페이지를 자동 크롤링하여**, 운영정보·의료진·취급 제품·장비·시술·다국어 지원 여부를 수집하고, 관계형 DB에 적재할 수 있는 정규화된 JSON으로 출력한다.

### 기대 효과
- 병원별 취급 제품·장비 현황 파악 → 영업 타깃팅 정밀화
- 경쟁사 제품 침투율 분석 → 시장 점유율 전략 수립
- 시술 가격 분포 분석 → 가격 정책 수립 근거
- 다국어 지원 병원 식별 → 해외 마케팅 관심 병원 발굴

## 입력
- 병원 ID, 병원명, 시도, 시군구, 읍면동, 도로명주소, 위도, 경도, (선택) 홈페이지 URL
- 입력 스키마: [`input_scheme.py`](reference/input_scheme.py)
- 참조 카탈로그: [aesthetic_products.json](reference/aesthetic_products.json), [aesthetic_equipments.json](reference/aesthetic_equipments.json)

## 출력
추후 관계형 DB 저장에 용이하도록 정규화 된 형태의 JSON 파일로 저장한다.
- 스키마: [`output_scheme.py`](reference/output_scheme.py) · 샘플: [`sample_output.json`](reference/sample_output.json)
- 저장위치 및 형식: `/output/{병원이름}_{병원ID}.json`
- 필드 채움/검증의 상세 규칙은 [collect.md](collect.md) 참조.

## 절차

### 1. URL 확보·검증
- 홈페이지 URL이 주어지면 병원명, 주소 등의 정보로 검증 후 사용한다. 만약 잘못된 URL로 판단되면 WebSearch를 통해 찾는다.
- 없으면 WebSearch로 후보를 찾고 Playwright로 접속해 병원명·주소 일치를 확인한다.
- WebSearch는 **공식 홈페이지 URL을 찾는 용도로만** 쓴다. 블로그·SNS·지도·포털 등 검색 결과 자체는 데이터 추출 대상이 아니다.
- 확정되면 출력의 `homepage_url`·`url_source`·`url_confidence`를 채우고, 병원명·주소의 **예비 일치 판단**을 해둔다(`identity_status` 최종 확정은 수집 단계에서 사업자정보/운영정보로 한다 — collect.md §5).

### 2. 홈페이지 데이터 수집
URL이 확정되면 **[collect.md](collect.md)** 를 읽고 그 절차를 따른다: 페이지 라우팅 → 추출 → 카탈로그 매칭 → 가격(텍스트/vision) → 정규화 → 완전성·notes → 저장·검증·마무리(`browser_close`).

## 불변 규칙
- **홈페이지 전용.** 데이터는 병원 공식 홈페이지에서만 추출한다. WebSearch는 홈페이지 URL을 찾거나 검증하는 용도로만 쓰며, 블로그·SNS·지도·포털 결과는 데이터 출처가 아니다.
- 크롤링 종료 시 Playwright 브라우저를 **반드시 `browser_close`로 닫고** 임시 아티팩트(`.playwright-mcp/`, 캡처 이미지)를 정리한다.
- `crawl_metadata.notes`는 절대 비워두지 않는다(collect.md §6).
