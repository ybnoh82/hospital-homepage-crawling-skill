from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# 입력 모델 (에이전트가 받는 병원 기본정보)
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
