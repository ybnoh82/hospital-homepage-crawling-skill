---
name: babitalk-hospital-extract
description: 바비톡(babitalk.com) 병원 상세페이지 URL(또는 병원 ID)이 주어지면, 병원정보(운영정보·통계·카테고리)와 이벤트정보(시술명·가격·할인·카테고리·옵션)를 정규화 JSON으로 추출한다. 바비톡 공개 JSON API를 호출하며 브라우저 렌더가 필요 없다. 후기 본문은 수집하지 않는다.
---

# 바비톡 병원 상세 추출

**바비톡 병원 상세페이지 URL이 주어졌을 때**, 그 병원의 운영정보와 이벤트(시술 상품) 정보를 구조화 JSON으로 뽑는 **독립 스킬**이다. 다른 스킬과 무관하게 단독 동작한다. **후기(리뷰) 본문은 수집하지 않는다**(리뷰 카운트·평점 같은 집계 수치만 포함).

## 동작 원리
바비톡 웹은 Next.js App Router(RSC)라 페이지 HTML 파싱은 까다롭지만, 페이지가 호출하는 **공개 JSON API가 인증 없이 열려 있다**. 번들 스크립트 [`extract.py`](extract.py)가 그 API를 직접 호출해 정규화한다 — **Playwright/브라우저 렌더 불필요, 모델 토큰 소모 없음**(순수 결정론적 파싱).
- 병원정보: `GET https://web-api.babitalk.com/v2/hospitals/{id}`
- 이벤트목록: `GET https://web-api.babitalk.com/v2/hospitals/{id}/events` (`{data[], pagination}`, `search_after` 커서로 페이지네이션 — 스크립트가 자동 순회)
- 이벤트옵션: `GET https://web-api.babitalk.com/v2/events/{event_id}/options` (`--events-detail` 시 이벤트당 호출)

## 입력
- 병원 상세 URL `https://web.babitalk.com/hospitals/{id}` 또는 병원 ID(`5217`)
- (URL 확보는 이 스킬의 범위 밖 — 외부에서 주어진다고 가정)

## 실행
의존성 없음(파이썬 stdlib만 사용). 프로젝트 루트에서:

```bash
# 병원정보 + 이벤트 목록(시술명·가격·카테고리)
python3 .claude/skills/babitalk-hospital-extract/extract.py 5217 --pretty

# 이벤트 옵션(옵션별 이름·가격)까지 — 이벤트당 1요청 추가
python3 .claude/skills/babitalk-hospital-extract/extract.py https://web.babitalk.com/hospitals/5217 --events-detail --out out/bb_5217.json
```
`uv run python ...` 으로 실행해도 된다. 옵션: `--events-detail`(옵션 상세), `--out FILE`(파일 저장), `--pretty`(들여쓰기).

## 출력 형태
```jsonc
{
  "source": "babitalk",
  "url": "...", "api": "...", "hospital_id": 5217, "fetched_at": "2026-..+09:00",
  "hospital": {
    "id","name","phone","region","address","way","location_map_url","description",
    "is_parking","medical_department",
    "categories": [ ... ],                 // 리프팅/보톡스/피부/필러 ...
    "office_hours": { monday..sunday: "HH:MM-HH:MM"|"휴무"|null }, "lunch_time",
    "statistics": { rating, review_count, event_count, view_count, ask_count },
    "images": [ ... ], "infos": [ ... ]
  },
  "events": [
    {
      "id","cid","name","description","target","side_effect",
      "category": { main, mid, sub },
      "price": { original, discounted, discount_rate, include_vat, currency },
      "rating","review_count","period": { start, end },
      "is_hot","is_kakao","option_type","ask_count","image","banner_image",
      // --events-detail 일 때만:
      "options": [ { id, name, option_type, price:{ original, discounted, discount_rate, currency } } ]
    }
  ],
  "event_count": N
}
```

## 활용 메모
- **제품·장비 매칭**: 이벤트 `name`에 실제 장비/제품명이 그대로 들어있는 경우가 많다(예: 티타늄·슈링크유니버스·인모드·온다·쿨소닉·울쎄라피 프라임·소프웨이브·써마지FLX·스컬트라·쥬베룩·리쥬란힐러). 카탈로그 매칭이 필요하면 추출 JSON을 받아 별도 매칭 로직(예: `hospital-homepage-crawl`의 카탈로그)에 태운다. 표기가 카탈로그 정식명과 다를 수 있으니 정규화/교차매칭 전제.
- **이벤트 가격은 프로모션가**(정상가/할인가/할인율 제공). 상시가가 아님.
- **이벤트 옵션**은 `--events-detail`로 `GET /v2/events/{id}/options`에서 옵션별 이름·가격을 채운다(예: 슈링크 유니버스 울트라/부스터 300·600샷, 쥬베룩 스킨 2cc/4cc·볼륨 12cc). 옵션명에 용량·샷수·라인이 들어가 매칭 신호가 더 풍부하다.
- 평점·리뷰수·조회수·문의수는 영업 활성도 신호로 쓸 수 있다.

## 주의 (반드시)
- 데이터는 **제3자 플랫폼(바비톡) 소유**다. **권한 있는 용도로만** 쓰고, 요청 간격·약관(ToS)·rate limit을 존중한다. 스크립트는 이벤트 페이지네이션 시 0.4초 간격을 둔다.
- 본 스킬은 **단건 조회용**이다. 대량 수집은 ToS·법무 판단이 선행되어야 하며, 차단/구조 변경에 대비해야 한다.
- 공개 API 경로/응답 구조가 바뀌면 추출이 깨질 수 있다(스크립트가 `[fetch error]`/`[parse error]`로 알린다).
