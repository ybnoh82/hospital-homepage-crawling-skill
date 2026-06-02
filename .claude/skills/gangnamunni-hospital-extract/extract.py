#!/usr/bin/env python3
"""강남언니(gangnamunni.com) 병원 상세페이지 → 병원정보·이벤트정보 추출기.

병원 상세페이지는 Next.js로 서버 렌더되어, 초기 HTML의
<script id="__NEXT_DATA__"> 안에 병원/이벤트 데이터가 JSON으로 그대로 들어있다.
이 스크립트는 그 JSON만 파싱해 정규화한다(브라우저 렌더 불필요).

사용:
    python3 extract.py <hospital_url_or_id> [--events-detail] [--out FILE] [--pretty]

예:
    python3 extract.py https://www.gangnamunni.com/hospitals/6345
    python3 extract.py 6345 --events-detail --out shineyou.json

--events-detail 을 주면 각 이벤트의 상세페이지(/events/{id})까지 받아
옵션별 구성(제품명·횟수)·가격·설명·부작용·다운타임까지 채운다(요청 수 증가).

주의: 데이터는 제3자 플랫폼(강남언니) 소유다. 권한 있는 용도로만 쓰고,
요청 간격/약관(ToS)·rate limit을 존중할 것. 본 스크립트는 단건 조회용이며
대량 수집 시에는 별도의 정책·법무 판단이 선행되어야 한다.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = "https://www.gangnamunni.com"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
DAY_ORDER = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
KST = timezone(timedelta(hours=9))


def fetch_html(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", "replace")


def parse_next_data(html: str) -> dict:
    m = NEXT_DATA_RE.search(html)
    if not m:
        raise ValueError("__NEXT_DATA__ 를 찾지 못함 (페이지 구조 변경 또는 차단 가능)")
    return json.loads(m.group(1))


def hospital_id_from(arg: str) -> str:
    arg = arg.strip()
    m = re.search(r"/hospitals/(\d+)", arg)
    if m:
        return m.group(1)
    if arg.isdigit():
        return arg
    raise ValueError(f"병원 ID/URL 형식이 아님: {arg!r}")


# --------------------------------------------------------------------------- #
# 가격/이벤트 정규화
# --------------------------------------------------------------------------- #
def norm_price(p: dict | None) -> dict | None:
    if not isinstance(p, dict):
        return None
    return {
        "currency": p.get("currency"),
        "original": p.get("originalAmount"),
        "discounted": p.get("discountedAmount"),
        "discount_percentage": p.get("discountPercentage"),
        "special_offer": p.get("specialOffer"),
    }


def norm_office_hours(office: dict | None) -> tuple[dict | None, str | None]:
    """hospital.officeHours -> ({MON: 'HH:MM-HH:MM' | None, ...}, comment)."""
    if not isinstance(office, dict):
        return None, None
    inner = office.get("officeHours")
    comment = office.get("officeHoursComment") or office.get("description")
    hours = {d: None for d in DAY_ORDER}
    if isinstance(inner, dict):  # {THU: '11:00-20:00', ...}
        for d, v in inner.items():
            if d in hours:
                hours[d] = v
    elif isinstance(inner, list):  # [{day, hour}, ...]
        for item in inner:
            d, v = item.get("day"), item.get("hour")
            if d in hours:
                hours[d] = v
    return hours, comment


def extract_hospital(data: dict) -> dict:
    h = data.get("hospital") or {}
    hdm = data.get("hospitalDetailMain") or {}
    loc = h.get("location") or {}
    stat = h.get("statistic") or hdm.get("statistics") or {}
    hours, hours_comment = norm_office_hours(h.get("officeHours"))
    booking = hdm.get("bookingMethods") or {}
    return {
        "id": h.get("hospitalId") or hdm.get("id"),
        "name": h.get("name") or hdm.get("name"),
        "country": h.get("country") or hdm.get("country"),
        "introduction": h.get("introduction"),
        "address": {
            "full": loc.get("address") or (hdm.get("address") or {}).get("address"),
            "sido": loc.get("sido"),
            "sigungu": loc.get("sigungu"),
            "zipcode": loc.get("zipCode"),
            "latitude": loc.get("lat"),
            "longitude": loc.get("lng"),
            "subways": loc.get("subwayNames")
            or (hdm.get("address") or {}).get("subwayNames")
            or [],
        },
        "phone": (h.get("contact") or {}).get("mainPhoneNumber")
        or hdm.get("mainPhoneNumber"),
        "office_hours": hours,
        "office_hours_comment": hours_comment,
        "treatment_tags": [t.get("name") for t in (h.get("treatmentTags") or [])],
        "languages": hdm.get("supportingLanguages") or [],
        "booking_methods": {
            "phone": booking.get("isPhoneCallApplicable"),
            "chat": booking.get("isChatApplicable"),
            "general": booking.get("isGeneralConsultationApplicable"),
        },
        "attributes": [
            {"name": a.get("name"), "description": a.get("description")}
            for a in (hdm.get("attributes") or [])
        ],
        "statistics": {
            "rating": stat.get("rating"),
            "review_count": stat.get("reviewCount"),
            "event_count": stat.get("eventCount"),
            "recent_consultation_member_count": stat.get(
                "recentConsultationMemberCount"
            ),
        },
        "images": {
            "profile": (h.get("images") or {}).get("profileImageUrl"),
            "main": (h.get("images") or {}).get("mainImageUrl"),
            "others": [
                i.get("imageUrl")
                for i in (h.get("images") or {}).get("otherImages", [])
            ],
        },
    }


def extract_event_summary(e: dict) -> dict:
    r = e.get("rating") or {}
    return {
        "id": e.get("id"),
        "title": e.get("title"),
        "url": f"{BASE}/events/{e.get('id')}",
        "operation_type": e.get("operationType"),
        "price": norm_price(e.get("price")),
        "include_vat": e.get("includeVat"),
        "rating": {"score": r.get("totalRating"), "count": r.get("ratingCount")},
        "medical_cases_count": e.get("medicalCasesCount"),
        "badges": e.get("badges") or [],
        "thumbnail": e.get("thumbnail"),
    }


def extract_event_options(service_offer: dict) -> list[dict]:
    out = []
    for o in service_offer.get("options") or []:
        out.append(
            {
                "name": o.get("name"),
                "price": norm_price(o.get("price")),
                "treatments": [
                    {
                        "name": t.get("name"),
                        "times_value": (t.get("times") or {}).get("value"),
                        "times_type": (t.get("times") or {}).get("type"),
                        "material": t.get("material"),
                    }
                    for t in (o.get("treatments") or [])
                ],
                "point_reward": (o.get("pointReward") or {}).get("amount"),
                "bundle_id": (o.get("procedureProduct") or {}).get("bundleId"),
            }
        )
    return out


def enrich_event_detail(event: dict, sleep: float = 0.7) -> dict:
    """이벤트 상세페이지에서 옵션·설명·부작용·다운타임·기간을 채운다."""
    time.sleep(sleep)  # rate-limit 존중
    try:
        html = fetch_html(f"{BASE}/events/{event['id']}")
        so = parse_next_data(html)["props"]["pageProps"].get("serviceOffer") or {}
    except (HTTPError, URLError, ValueError, KeyError) as exc:
        event["detail_error"] = str(exc)
        return event
    event["options"] = extract_event_options(so)
    event["description"] = so.get("description")
    event["side_effects"] = so.get("sideEffects")
    event["downtime"] = so.get("downtime")
    event["period"] = so.get("period")
    event["procedure_process"] = so.get("procedureProcess")
    return event


def extract(url_or_id: str, with_detail: bool = False) -> dict:
    hid = hospital_id_from(url_or_id)
    url = f"{BASE}/hospitals/{hid}"
    data = parse_next_data(fetch_html(url))["props"]["pageProps"].get("data") or {}
    events = [extract_event_summary(e) for e in (data.get("events") or [])]
    if with_detail:
        events = [enrich_event_detail(e) for e in events]
    return {
        "source": "gangnamunni",
        "url": url,
        "hospital_id": int(hid),
        "fetched_at": datetime.now(KST).isoformat(timespec="seconds"),
        "hospital": extract_hospital(data),
        "events": events,
        "event_count": len(events),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="강남언니 병원 상세 → 병원/이벤트 JSON 추출"
    )
    ap.add_argument(
        "hospital", help="병원 상세 URL 또는 병원 ID (예: 6345 또는 .../hospitals/6345)"
    )
    ap.add_argument(
        "--events-detail",
        action="store_true",
        help="이벤트 상세(옵션·제품·설명)까지 수집",
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
