from decimal import Decimal, InvalidOperation


CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("9999999999.99")


def parse_positive_amount(value) -> Decimal | None:
    if isinstance(value, bool):
        return None

    text = str(value).strip().replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None

    if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT:
        return None
    if amount != amount.quantize(CENT):
        return None
    return amount
