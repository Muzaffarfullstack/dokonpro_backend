from __future__ import annotations

import re

from app.core.exceptions import AppException


def normalize_phone(phone: str) -> str:
    phone = phone.strip()
    digits = re.sub(r"\D+", "", phone)
    if len(digits) == 9:
        digits = f"998{digits}"
    if phone.startswith("00"):
        digits = digits[2:]

    if not 8 <= len(digits) <= 15 or digits.startswith("0"):
        raise AppException(
            code="INVALID_PHONE",
            message="Telefon raqam xalqaro formatda bo'lishi kerak, masalan +14155552671.",
            field="phone",
        )
    return f"+{digits}"
