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


class MatchedProduct(BaseModel):
    product_kr: str
    brand_kr: str | None = None
    manufacturer_kr: str | None = None
    category: str | None = None
    plandocs_handled: int | None = None
    plandocs_featured: int | None = None
    source_page: str | None = None
    context: str | None = None


class UnmatchedProduct(BaseModel):
    raw_name: str
    category_guess: str | None = None
    source_page: str | None = None
    context: str | None = None


class ProductsInfo(BaseModel):
    matched_products: list[MatchedProduct] = []
    unmatched_products: list[UnmatchedProduct] = []


class MatchedEquipment(BaseModel):
    name_kr: str
    name_en: str | None = None
    category: str | None = None
    source_page: str | None = None
    context: str | None = None


class UnmatchedEquipment(BaseModel):
    raw_name: str
    category_guess: str | None = None
    source_page: str | None = None
    context: str | None = None


class EquipmentsInfo(BaseModel):
    matched_equipments: list[MatchedEquipment] = []
    unmatched_equipments: list[UnmatchedEquipment] = []


class TreatmentInfo(BaseModel):
    treatment_name: str
    category: str | None = None
    product_name: str | None = None
    equipment_name: str | None = None
    price: int | None = None
    price_display: str | None = None
    unit: str | None = None
    is_event_price: bool | None = None
    notes: str | None = None
    source_page: str | None = None


class LanguageSupport(BaseModel):
    supported_languages: list[str] = []
    has_language_switcher: bool = False
    foreign_language_pages: dict[str, str] = {}


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
    homepage_url: str | None = None
    url_source: str | None = None
    url_confidence: str | None = None
    blog_url: str | None = None
    sns_url: str | None = None
    alternative_urls: list[str] = []

    operation_info: OperationInfo | None = None
    doctors: list[DoctorInfo] = []
    products: ProductsInfo = ProductsInfo()
    equipments: EquipmentsInfo = EquipmentsInfo()
    treatments: list[TreatmentInfo] = []
    language_support: LanguageSupport = LanguageSupport()
    crawl_metadata: CrawlMetadata = CrawlMetadata()
