---
name: gangnamunni-hospital-extract
description: 강남언니(gangnamunni.com) 병원 상세페이지 URL(또는 병원 ID)이 주어지면, 병원정보(운영정보·통계·속성)와 이벤트정보(시술·옵션·가격·제품명)를 정규화 JSON으로 추출한다. 번들된 파이썬 스크립트가 페이지의 __NEXT_DATA__를 파싱한다(브라우저 렌더 불필요).
---

# 강남언니 병원 상세 추출

**강남언니 병원 상세페이지 URL이 주어졌을 때**, 그 병원의 운영정보와 이벤트(시술 상품) 정보를 구조화 JSON으로 뽑는 **독립 스킬**이다. 홈페이지 크롤링 스킬과 무관하게 단독으로 동작한다.

## 동작 원리
강남언니 병원 페이지는 Next.js로 **서버 렌더**되어, 초기 HTML의 `<script id="__NEXT_DATA__">` 안에 병원·이벤트 데이터가 JSON으로 그대로 담겨 있다. 번들 스크립트 [`extract.py`](extract.py)가 그 JSON만 파싱해 정규화한다 — **Playwright/브라우저 렌더 불필요, 모델 토큰 소모 없음**(순수 결정론적 파싱).

## 입력
- 병원 상세 URL `https://www.gangnamunni.com/hospitals/{id}` 또는 병원 ID(`6345`)
- (URL 확보는 이 스킬의 범위 밖 — 외부에서 주어진다고 가정)

## 실행
의존성 없음(파이썬 stdlib만 사용). 프로젝트 루트에서:

```bash
# 병원정보 + 이벤트 요약(제목·가격·평점)
python3 .claude/skills/gangnamunni-hospital-extract/extract.py 6345 --pretty

# 이벤트 상세까지(옵션별 제품·횟수·가격·설명·부작용·다운타임) — 이벤트당 1요청 추가
python3 .claude/skills/gangnamunni-hospital-extract/extract.py https://www.gangnamunni.com/hospitals/6345 --events-detail --out out/gn_6345.json
```
`uv run python ...` 으로 실행해도 된다. 옵션: `--events-detail`(옵션·제품 상세), `--out FILE`(파일 저장), `--pretty`(들여쓰기).

## 출력 형태
```jsonc
{
  "source": "gangnamunni",
  "url": "...", "hospital_id": 6345, "fetched_at": "2026-..+09:00",
  "hospital": {
    "id","name","introduction",
    "address": { full, sido, sigungu, zipcode, latitude, longitude, subways[] },
    "phone",
    "office_hours": { MON..SUN: "HH:MM-HH:MM"|null }, "office_hours_comment",
    "treatment_tags": [ ... ],            // 피부/보톡스/필러/리프팅 ...
    "languages": [ ... ],                 // 다국어 지원(있으면)
    "booking_methods": { phone, chat, general },
    "attributes": [ { name, description } ],   // 여성 의사 진료, 역 도보 5분 ...
    "statistics": { rating, review_count, event_count, recent_consultation_member_count },
    "images": { profile, main, others[] }
  },
  "events": [
    {
      "id","title","url","operation_type","include_vat","thumbnail",
      "price": { currency, original, discounted, discount_percentage, special_offer },
      "rating": { score, count }, "medical_cases_count", "badges": [ ... ],
      // --events-detail 일 때만:
      "options": [ { name, price{...}, treatments:[{name, times_value, times_type, material}], point_reward, bundle_id } ],
      "description","side_effects","downtime","period","procedure_process"
    }
  ],
  "event_count": N
}
```

## 활용 메모
- **제품·장비 매칭**: 이벤트 옵션의 `treatments[].name`에 실제 제품/장비명이 자주 박혀 있다(예: 울트라콜 100/200, 쥬베룩, 리쥬란힐러, 포텐자). 카탈로그 매칭이 필요하면 추출 JSON을 받아 별도로 매칭 로직(예: `hospital-homepage-crawl`의 카탈로그)에 태운다. 단 옵션명은 병원이 자유 입력하므로 **표기가 카탈로그 정식명과 다를 수 있다** — 정규화/교차매칭 전제.
- **이벤트 가격은 프로모션가**(정상가/할인가/할인율 구조화 제공). 상시가가 아님에 유의.
- 평점/리뷰수·상담수·속성 배지는 영업 활성도 신호로 쓸 수 있다.

## 주의 (반드시)
- 데이터는 **제3자 플랫폼(강남언니) 소유**다. **권한 있는 용도로만** 쓰고, 요청 간격·약관(ToS)·rate limit을 존중한다. 스크립트는 `--events-detail` 시 이벤트당 0.7초 간격을 둔다.
- 본 스킬은 **단건 조회용**이다. 대량 수집은 ToS·법무 판단이 선행되어야 하며, 차단/구조 변경에 대비해야 한다.
- SSR(`__NEXT_DATA__`) 구조가 바뀌면 파싱이 깨질 수 있다(스크립트가 `[parse error]`로 알린다).
