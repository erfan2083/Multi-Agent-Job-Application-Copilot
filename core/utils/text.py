import re


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def contains_any(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in keywords)
