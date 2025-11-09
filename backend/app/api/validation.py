"""API endpoints for data validation."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session

from ..core.validator import validate_all_data
from ..db import get_session

router = APIRouter(prefix="/validation", tags=["validation"])


@router.get("/warnings")
def get_validation_warnings(session: Session = Depends(get_session)) -> List[dict]:
    """
    Run all data validation checks and return warnings.

    Returns warnings for:
    - Impossible dates (death before birth, child born before parent)
    - Suspicious age gaps (spouses with >25 year gap, parent <12 or >60 at child's birth)
    - Duplicate names within families
    - Unrealistic lifespans (>120 years)
    """
    warnings = validate_all_data(session)
    return warnings
