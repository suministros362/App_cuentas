import re
from datetime import datetime

from pypdf import PdfReader


MONTH_NAMES = {
    "ene": "01",
    "feb": "02",
    "mar": "03",
    "abr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "ago": "08",
    "sep": "09",
    "set": "09",
    "oct": "10",
    "nov": "11",
    "dic": "12",
}


def parse_amount(value: str, keep_sign: bool = False) -> float | None:
    cleaned = re.sub(r"[^\d,.-]", "", value).strip()
    if not cleaned:
        return None

    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        amount = float(cleaned)
    except ValueError:
        return None

    if not keep_sign:
        amount = abs(amount)

    return amount if amount != 0 else None


def _transaction_date(year: str, month: str, day: str) -> str | None:
    try:
        value = datetime(2000 + int(year), int(month), int(day))
    except ValueError:
        return None
    return value.strftime("%Y-%m-%d")


def current_month() -> str:
    return datetime.now().strftime("%Y-%m")


def parse_visa_expenses(text: str, month: str) -> list[dict]:
    expenses = []
    transaction_pattern = re.compile(
        r"^"
        r"(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{2})\s+"
        r"(?:(?P<receipt>\d{6})\s+)?"
        r"(?P<description>.+?)\s+"
        r"(?P<pesos>-?\d{1,3}(?:\.\d{3})*,\d{2})\s+"
        r"(?P<dollar>-?\d{1,3}(?:\.\d{3})*,\d{2})"
        r"$"
    )

    for line in text.splitlines():
        normalized = " ".join(line.split())
        if not normalized:
            continue

        match = transaction_pattern.match(normalized)
        if not match:
            continue

        amount = parse_amount(match.group("pesos"), keep_sign=True)
        if amount is None:
            continue

        transaction_date = _transaction_date(
            match.group("year"), match.group("month"), match.group("day")
        )
        if transaction_date is None:
            continue

        description = match.group("description").strip(" -:|")
        lowered = description.lower()
        if lowered.startswith("su pago") or "total consumos" in lowered:
            continue

        expenses.append(
            {
                "month": month,
                "date": transaction_date,
                "description": description[:180],
                "amount": abs(amount),
                "movement_type": "refund" if amount < 0 else "expense",
            }
        )

    return expenses


def parse_master_expenses(text: str, month: str) -> list[dict]:
    expenses = []
    transaction_pattern = re.compile(
        r"^"
        r"(?P<day>\d{2})-(?P<month_name>[A-Za-zÁÉÍÓÚáéíóú]+)-(?P<year>\d{2})\s+"
        r"(?P<description>.+?)\s+"
        r"(?P<receipt>\d{5})\s+"
        r"(?P<pesos>-?\d+(?:,\d{2})?)"
        r"$"
    )

    for line in text.splitlines():
        normalized = " ".join(line.split())
        if not normalized:
            continue

        match = transaction_pattern.match(normalized)
        if not match:
            continue

        amount = parse_amount(match.group("pesos"), keep_sign=True)
        if amount is None:
            continue

        month_key = match.group("month_name").lower()[:3]
        transaction_month = MONTH_NAMES.get(month_key)
        if not transaction_month:
            continue

        transaction_date = _transaction_date(
            match.group("year"), transaction_month, match.group("day")
        )
        if transaction_date is None:
            continue

        expenses.append(
            {
                "month": month,
                "date": transaction_date,
                "description": match.group("description").strip(" -:|")[:180],
                "amount": abs(amount),
                "movement_type": "refund" if amount < 0 else "expense",
            }
        )

    return expenses


def parse_pdf_expenses(
    file_storage,
    card_type: str,
    payment_month: str,
    statement_month: str,
) -> list[dict]:
    reader = PdfReader(file_storage.stream)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    month = payment_month

    if card_type == "visa":
        expenses = parse_visa_expenses(text, month)
    elif card_type == "mastercard":
        expenses = parse_master_expenses(text, month)
    else:
        raise ValueError("Tipo de tarjeta invalido")

    for expense in expenses:
        expense["month"] = payment_month
        expense["payment_month"] = payment_month
        expense["statement_month"] = statement_month
        expense["card_type"] = card_type
        expense["payment_method"] = "Visa" if card_type == "visa" else "Mastercard"
        expense["source"] = "PDF"
    return expenses
