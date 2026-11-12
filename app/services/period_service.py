from calendar import monthrange
from datetime import date, datetime
import re


MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_period_month(value: str) -> str | None:
    if not MONTH_PATTERN.fullmatch(value):
        return None
    year, month = (int(part) for part in value.split("-"))
    if not 1 <= month <= 12 or year < 1:
        return None
    return value


def parse_period_date(value: str) -> date | None:
    if not DATE_PATTERN.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def month_bounds(month: str) -> tuple[str, str]:
    year, month_number = (int(part) for part in month.split("-"))
    last_day = monthrange(year, month_number)[1]
    return f"{month}-01", f"{month}-{last_day:02d}"


def validate_period_args(args):
    month = args.get("month", "").strip()
    year = args.get("year", "").strip()
    exact_date = args.get("date", "").strip()
    start_date = args.get("from", "").strip()
    end_date = args.get("to", "").strip()

    if month and year:
        if not year.isdecimal() or len(year) != 4 or int(year) < 1:
            return None, ({"error": "El año debe tener formato YYYY."}, 400)
        if month.isdecimal() and 1 <= int(month) <= 12:
            month = f"{year}-{int(month):02d}"
        else:
            return None, ({"error": "El mes debe estar entre 1 y 12 cuando se indica el año."}, 400)
    elif month and parse_period_month(month) is None:
        return None, ({"error": "Indica el mes y el año por separado."}, 400)
    elif not month and year:
        if not year.isdecimal() or len(year) != 4 or int(year) < 1:
            return None, ({"error": "El año debe tener formato YYYY."}, 400)
    if exact_date and parse_period_date(exact_date) is None:
        return None, ({"error": "La fecha debe ser válida y tener formato YYYY-MM-DD."}, 400)
    if start_date and parse_period_date(start_date) is None:
        return None, ({"error": "La fecha inicial debe tener formato YYYY-MM-DD."}, 400)
    if end_date and parse_period_date(end_date) is None:
        return None, ({"error": "La fecha final debe tener formato YYYY-MM-DD."}, 400)
    if exact_date and (start_date or end_date):
        return None, ({"error": "Usa una fecha exacta o un rango, no ambos."}, 400)
    if (month or year) and (start_date or end_date):
        return None, ({"error": "Usa un período o un rango de fechas, no ambos."}, 400)
    if start_date and end_date and start_date > end_date:
        return None, ({"error": "La fecha inicial no puede ser posterior a la final."}, 400)
    if exact_date and month and not exact_date.startswith(f"{month}-"):
        return None, ({"error": "La fecha no pertenece al mes seleccionado."}, 400)

    if not (month or year or exact_date or start_date or end_date):
        month = datetime.now().strftime("%Y-%m")

    return {
        "month": month,
        "year": int(year) if year else (int(month[:4]) if month else None),
        "date": exact_date,
        "from": start_date,
        "to": end_date,
    }, None
