#!/usr/bin/env python3
"""바비톡(babitalk.com) 병원 상세페이지 → 병원정보·이벤트정보 추출기.

바비톡 웹은 Next.js App Router(RSC)라 페이지 HTML 파싱은 까다롭지만,
페이지가 호출하는 공개 JSON API가 인증 없이 열려 있다(브라우저 렌더 불필요):
    GET https://web-api.babitalk.com/v2/hospitals/{id}          → 병원정보
    GET https://web-api.babitalk.com/v2/hospitals/{id}/events    → 이벤트목록({data[],pagination})
이 스크립트는 그 API를 직접 호출해 정규화한다. (후기 본문은 수집하지 않는다 — 카운트만.)

사용:
    python3 extract.py <hospital_url_or_id> [--out FILE] [--pretty]
예:
    python3 extract.py https://web.babitalk.com/hospitals/5217 --pretty
    python3 extract.py 5217 --out out/bb_5217.json

주의: 데이터는 제3자 플랫폼(바비톡) 소유다. 권한 있는 용도로만 쓰고,
요청 간격·약관(ToS)·rate limit을 존중할 것. 단건 조회용이며, 대량 수집은
별도 정책·법무 판단이 선행되어야 한다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API = "https://web-api.babitalk.com/v2"
WEB = "https://web.babitalk.com"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Accept-Language": "ko-KR,ko",
    "Origin": WEB,
    "Referer": WEB + "/",
}
KST = timezone(timedelta(hours=9))
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MAX_PAGES = 50  # 페이지네이션 안전장치


def get_json(url: str, timeout: int = 20):
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def hospital_id_from(arg: str) -> str:
    arg = arg.strip()
    m = re.search(r"/hospitals/(\d+)", arg)
    if m:
        return m.group(1)
    if arg.isdigit():
        return arg
    raise ValueError(f"병원 ID/URL 형식이 아님: {arg!r}")


def norm_office_hours(operation_time: list | None):
    """[{day_type, day_name, day_from, day_to, day_off}] -> (요일dict, lunch)."""
    hours = {d: None for d in DAYS}
    lunch = None
    for d in operation_time or []:
        if (d.get("day_type") or "").upper() == "LUNCH_TIME":
            lunch = f"{d.get('day_from')}-{d.get('day_to')}"
            continue
        name = (d.get("day_name") or "").lower()
        if name in hours:
            hours[name] = (
                "휴무" if d.get("day_off") else f"{d.get('day_from')}-{d.get('day_to')}"
            )
    return hours, lunch


def extract_hospital(h: dict) -> dict:
    hours, lunch = norm_office_hours(h.get("operation_time"))
    return {
        "id": h.get("id"),
        "name": h.get("name"),
        "phone": h.get("tel"),
        "region": h.get("region"),
        "address": h.get("address"),
        "way": h.get("way") or None,
        "location_map_url": h.get("location_map_url") or None,
        "description": h.get("description"),
        "is_parking": h.get("is_parking"),
        "medical_department": h.get("medical_department") or None,
        "categories": (h.get("main_category_names") or [])
        + (h.get("category_names") or []),
        "office_hours": hours,
        "lunch_time": lunch,
        "statistics": {
            "rating": h.get("star_avg"),
            "review_count": h.get("review_count"),
            "event_count": h.get("event_count"),
            "view_count": h.get("view_count"),
            "ask_count": h.get("ask_count"),
        },
        "images": h.get("images") or [],
        "infos": h.get("infos") or [],
    }


def extract_event(e: dict) -> dict:
    return {
        "id": e.get("id"),
        "cid": e.get("cid"),
        "name": e.get("name"),
        "description": e.get("description"),
        "target": e.get("target"),
        "side_effect": e.get("side_effect"),
        "category": {
            "main": e.get("main_category_name"),
            "mid": e.get("mid_category_name"),
            "sub": e.get("sub_category_name"),
        },
        "price": {
            "original": e.get("price"),
            "discounted": e.get("discount_price"),
            "discount_rate": e.get("discount_rate"),
            "include_vat": e.get("include_vat"),
            "currency": "KRW",
        },
        "rating": e.get("rating"),
        "review_count": e.get("review_count"),
        "period": {"start": e.get("start_date"), "end": e.get("end_date")},
        "is_hot": e.get("is_hot"),
        "is_kakao": e.get("is_kakao"),
        "option_type": e.get("option_type"),
        "ask_count": e.get("ask_count"),
        "image": e.get("image"),
        "banner_image": e.get("banner_image"),
    }


def fetch_event_options(event_id) -> list[dict]:
    """이벤트 옵션(GET /v2/events/{id}/options) → 옵션별 이름·가격."""
    try:
        d = get_json(f"{API}/events/{event_id}/options")
    except OSError:  # HTTPError·URLError 모두 OSError 하위 (파이썬 버전 무관 안전)
        return []
    return [
        {
            "id": o.get("id"),
            "name": o.get("name"),
            "option_type": o.get("option_type"),
            "price": {
                "original": o.get("price"),
                "discounted": o.get("discount_price"),
                "discount_rate": o.get("discount_rate"),
                "currency": "KRW",
            },
        }
        for o in (d.get("data") or [])
    ]


def fetch_events(hid: str) -> list[dict]:
    """페이지네이션(search_after 커서) 따라 전체 이벤트 수집."""
    events, cursor, seen = [], None, set()
    for _ in range(MAX_PAGES):
        url = f"{API}/hospitals/{hid}/events"
        if cursor:
            url += f"?search_after={cursor}"
        d = get_json(url)
        page = d.get("data") or []
        events.extend(page)
        pg = d.get("pagination") or {}
        nxt = pg.get("search_after")
        if not pg.get("has_next") or not page or nxt in (None, cursor) or nxt in seen:
            break
        seen.add(nxt)
        cursor = nxt
        time.sleep(0.4)  # rate-limit 존중
    return events


def extract(url_or_id: str, with_detail: bool = False) -> dict:
    hid = hospital_id_from(url_or_id)
    hospital_raw = get_json(f"{API}/hospitals/{hid}")
    if not isinstance(hospital_raw, dict) or "name" not in hospital_raw:
        raise ValueError("병원 API 응답 형식이 예상과 다름 (구조 변경/차단 가능)")
    events = [extract_event(e) for e in fetch_events(hid)]
    if with_detail:
        for ev in events:
            ev["options"] = fetch_event_options(ev["id"])
            time.sleep(0.4)  # rate-limit 존중
    return {
        "source": "babitalk",
        "url": f"{WEB}/hospitals/{hid}",
        "api": f"{API}/hospitals/{hid}",
        "hospital_id": int(hid),
        "fetched_at": datetime.now(KST).isoformat(timespec="seconds"),
        "hospital": extract_hospital(hospital_raw),
        "events": events,
        "event_count": len(events),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="바비톡 병원 상세 → 병원/이벤트 JSON 추출")
    ap.add_argument(
        "hospital", help="병원 상세 URL 또는 병원 ID (예: 5217 또는 .../hospitals/5217)"
    )
    ap.add_argument(
        "--events-detail",
        action="store_true",
        help="이벤트 옵션(옵션별 이름·가격)까지 수집",
    )
    ap.add_argument("--out", help="결과 JSON 저장 경로(미지정 시 stdout)")
    ap.add_argument("--pretty", action="store_true", help="들여쓰기 출력")
    args = ap.parse_args()

    try:
        result = extract(args.hospital, with_detail=args.events_detail)
    except (HTTPError, URLError) as exc:
        print(f"[fetch error] {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"[parse error] {exc}", file=sys.stderr)
        return 3

    text = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.out:
        out_dir = os.path.dirname(args.out)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"saved -> {args.out} (events={result['event_count']})", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
