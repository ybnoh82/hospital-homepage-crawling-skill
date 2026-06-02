from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# 입력 모델
# ---------------------------------------------------------------------------

class HospitalInput(BaseModel):
    id: str
    hospital_name: str
    sido: str
    sggu: str
    emdong: str
    address: str
    longitude: float | None = None
    latitude: float | None = None


# ---------------------------------------------------------------------------
# Stage 1: URL 탐색 결과
# ---------------------------------------------------------------------------

class Stage1Result(BaseModel):
    hospital_id: str
    homepage_url: str | None = None
    url_source: str | None = None  # "web_search", "naver_map", "kakao_map"
    url_confidence: Literal["high", "medium", "low"] | None = None
    blog_url: str | None = None
    sns_url: str | None = None
    alternative_urls: list[str] = []
    error: str | None = None


# ---------------------------------------------------------------------------
# Stage 2: 사이트맵 분석 결과
# ---------------------------------------------------------------------------

class CrawlTarget(BaseModel):
    url: str
    page_type: str  # "about", "doctors", "treatments", "prices", "equipment", "language"
    expected_data: list[str] = []
    priority: int = 1


class Stage2Result(BaseModel):
    hospital_id: str
    homepage_url: str
    crawl_targets: list[CrawlTarget] = []
    has_language_switcher: bool = False
    detected_languages: list[str] = []
    error: str | None = None


# ---------------------------------------------------------------------------
# Stage 3: 페이지 크롤링 결과
# ---------------------------------------------------------------------------

class RawPageData(BaseModel):
    url: str
    page_type: str
    raw_data: dict[str, Any] = {}


class Stage3Result(BaseModel):
    hospital_id: str
    pages_crawled: int = 0
    raw_pages: list[RawPageData] = []
    error: str | None = None


# ---------------------------------------------------------------------------
# Stage 4: 최종 정규화 결과 (병원별 출력 JSON)
# ---------------------------------------------------------------------------

class OperatingHours(BaseModel):
    open: str | None = None
    close: str | None = None
    break_start: str | None = None
    break_end: str | None = None


class OperationInfo(BaseModel):
    hospital_name: str | None = None
    representative_name: str | None = None
    business_number: str | None = None
    phone: str | None = None
    phone_secondary: str | None = None
    fax: str | None = None
    email: str | None = None
    kakao_channel: str | None = None
    operating_hours: dict[str, OperatingHours | None] | None = None
    operating_hours_note: str | None = None  # 야간진료·휴진 등 요일 구조에 안 담기는 특이사항
    parking_info: str | None = None
    transport_info: str | None = None
    facilities: list[str] = []


# 레코드 단위 신뢰도. verified=원문에서 직접 확인, unverified=확인 못함, inferred=정황상 추론.
VerificationStatus = Literal["verified", "unverified", "inferred"]


class DoctorInfo(BaseModel):
    name: str
    is_representative: bool = False
    role: str | None = None
    specialty: list[str] = []
    education: list[str] = []
    career: list[str] = []
    associations: list[str] = []
    awards: list[str] = []
    profile_image_url: str | None = None
    verification_status: VerificationStatus | None = None


class SourceRef(BaseModel):
    """한 항목의 출처 1건. 동일 제품/장비가 여러 페이지에 나오면 모두 기록(통합 시 출처 손실 방지)."""
    channel: str = "homepage"  # 홈페이지 전용 스킬이므로 기본 homepage
    url: str | None = None
    evidence: str | None = None  # 인용된 본문 일부


class MatchedProduct(BaseModel):
    product_kr: str
    brand_kr: str | None = None
    manufacturer_kr: str | None = None
    category: str | None = None
    plandocs_handled: int | None = None
    plandocs_featured: int | None = None
    mention_count: int | None = None  # 본문 언급 횟수(영업 신호)
    sources: list[SourceRef] = []
    context: str | None = None  # 매칭 근거·판단 사유(출처 인용문은 sources[].evidence)
    verification_status: VerificationStatus | None = None


class UnmatchedProduct(BaseModel):
    raw_name: str
    category_guess: str | None = None
    mention_count: int | None = None
    sources: list[SourceRef] = []
    context: str | None = None
    verification_status: VerificationStatus | None = None


class ProductsInfo(BaseModel):
    matched_products: list[MatchedProduct] = []
    unmatched_products: list[UnmatchedProduct] = []


class MatchedEquipment(BaseModel):
    name_kr: str
    name_en: str | None = None
    category: str | None = None
    mention_count: int | None = None
    sources: list[SourceRef] = []
    context: str | None = None
    verification_status: VerificationStatus | None = None


class UnmatchedEquipment(BaseModel):
    raw_name: str
    category_guess: str | None = None
    mention_count: int | None = None
    sources: list[SourceRef] = []
    context: str | None = None
    verification_status: VerificationStatus | None = None


class EquipmentsInfo(BaseModel):
    matched_equipments: list[MatchedEquipment] = []
    unmatched_equipments: list[UnmatchedEquipment] = []


class TreatmentPrice(BaseModel):
    text: str | None = None       # 원문 그대로. 예: "180만원", "5~30만원", "상담 후 결정"
    low: int | None = None        # KRW 정수(범위 하한 또는 단일가)
    high: int | None = None       # KRW 정수(범위 상한). 단일가면 low와 동일하거나 null
    unit: str | None = None       # 회/cc/ml/샷/부위/패키지
    currency: str | None = "KRW"
    is_event_price: bool | None = None


class TreatmentPackage(BaseModel):
    sessions: int | None = None
    duration_months: int | None = None
    event_period: str | None = None  # 예: "2026-05-01 ~ 2026-05-31"


class TreatmentInfo(BaseModel):
    treatment_name: str
    category: str | None = None
    product_name: str | None = None    # 연결된 제품 matched 이름(복수는 '; '로 연결)
    equipment_name: str | None = None  # 연결된 장비 matched 이름(복수는 '; '로 연결)
    price: TreatmentPrice | None = None
    package: TreatmentPackage | None = None
    notes: str | None = None
    source_page: str | None = None
    verification_status: VerificationStatus | None = None


class LanguageSupport(BaseModel):
    supported_languages: list[str] = []
    has_language_switcher: bool = False
    foreign_language_pages: dict[str, str] = {}


class Address(BaseModel):
    """출력에 주소를 구조화해 보존(관계형 DB 적재 시 재조인 불필요)."""
    sido: str | None = None
    sigungu: str | None = None
    eupmyeondong: str | None = None
    road: str | None = None
    detail: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class SiblingBranch(BaseModel):
    name: str
    url: str | None = None
    address: str | None = None


class Branches(BaseModel):
    """단독/지점/본점 여부. 별도 도메인 분원(SKILL.md §2)을 구조화해 기록."""
    type: Literal["single", "branch", "headquarters"] | None = None
    network_group: str | None = None
    this_branch_name: str | None = None
    sibling_branches: list[SiblingBranch] = []


class RunMeta(BaseModel):
    """모델 호출 메타(비용·시간·토큰). runner 가 SDK 응답에서 주입."""
    model: str | None = None
    turns: int | None = None
    total_cost_usd: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    elapsed_seconds: int | None = None
    stream_error: str | None = None


class CrawlCompleteness(BaseModel):
    operation_info: bool = False
    doctors: bool = False
    products: bool = False
    equipments: bool = False
    treatments: bool = False
    prices: bool = False
    language_support: bool = False


class CrawlMetadata(BaseModel):
    pages_crawled: int = 0
    pages_visited: list[str] = []  # 실제 방문 URL 목록(sample_output 와 정합)
    crawl_method: str | None = None  # 추출 방식 설명(서버데이터/DOM/이미지 등)
    crawl_duration_seconds: int = 0
    errors: list[str] = []
    completeness: CrawlCompleteness = CrawlCompleteness()
    stage_costs: dict[str, float] = {}
    # 크롤링 판단 근거(가격 출처, 매칭/보류 사유, 별도 도메인·다국어 정책, 미방문 영역 등).
    # SKILL.md가 'crawl_metadata.notes는 비워두지 말 것'으로 필수 기재를 요구하므로 추가됨.
    notes: list[str] = []


class HospitalResult(BaseModel):
    hospital_id: str
    hospital_name: str
    crawled_at: str
    address: Address | None = None
    homepage_url: str | None = None
    url_source: str | None = None
    url_confidence: str | None = None
    # 입력 병원명·주소와 홈페이지 표기 일치 여부. match/mismatch/partial.
    identity_status: Literal["match", "mismatch", "partial"] | None = None
    blog_url: str | None = None
    sns_url: str | None = None
    alternative_urls: list[str] = []

    branches: Branches | None = None
    operation_info: OperationInfo | None = None
    doctors: list[DoctorInfo] = []
    products: ProductsInfo = ProductsInfo()
    equipments: EquipmentsInfo = EquipmentsInfo()
    treatments: list[TreatmentInfo] = []
    language_support: LanguageSupport = LanguageSupport()
    crawl_metadata: CrawlMetadata = CrawlMetadata()
    run_meta: RunMeta | None = None
