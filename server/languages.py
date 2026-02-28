from __future__ import annotations

from typing import Any


LANGUAGE_METADATA: dict[str, dict[str, Any]] = {
    "en": {"name": "English", "scripts": ["latin"], "aliases": ["english"]},
    "as": {"name": "Assamese", "scripts": ["bengali"], "aliases": ["assamese"]},
    "bn": {"name": "Bengali", "scripts": ["bengali"], "aliases": ["bengali", "bangla"]},
    "brx": {"name": "Bodo", "scripts": ["devanagari"], "aliases": ["bodo"]},
    "doi": {"name": "Dogri", "scripts": ["devanagari"], "aliases": ["dogri"]},
    "gu": {"name": "Gujarati", "scripts": ["gujarati"], "aliases": ["gujarati"]},
    "hi": {"name": "Hindi", "scripts": ["devanagari"], "aliases": ["hindi", "hinglish"]},
    "kn": {"name": "Kannada", "scripts": ["kannada"], "aliases": ["kannada"]},
    "ks": {"name": "Kashmiri", "scripts": ["arabic", "devanagari"], "aliases": ["kashmiri"]},
    "kok": {"name": "Konkani", "scripts": ["devanagari", "latin"], "aliases": ["konkani"]},
    "mai": {"name": "Maithili", "scripts": ["devanagari"], "aliases": ["maithili"]},
    "ml": {"name": "Malayalam", "scripts": ["malayalam"], "aliases": ["malayalam"]},
    "mni": {"name": "Manipuri", "scripts": ["meitei", "bengali"], "aliases": ["manipuri", "meitei"]},
    "mr": {"name": "Marathi", "scripts": ["devanagari"], "aliases": ["marathi"]},
    "ne": {"name": "Nepali", "scripts": ["devanagari"], "aliases": ["nepali"]},
    "or": {"name": "Odia", "scripts": ["odia"], "aliases": ["odia", "oriya"]},
    "pa": {"name": "Punjabi", "scripts": ["gurmukhi"], "aliases": ["punjabi"]},
    "sa": {"name": "Sanskrit", "scripts": ["devanagari"], "aliases": ["sanskrit"]},
    "sat": {"name": "Santali", "scripts": ["ol_chiki"], "aliases": ["santali"]},
    "sd": {"name": "Sindhi", "scripts": ["arabic", "devanagari"], "aliases": ["sindhi"]},
    "ta": {"name": "Tamil", "scripts": ["tamil"], "aliases": ["tamil", "tanglish"]},
    "te": {"name": "Telugu", "scripts": ["telugu"], "aliases": ["telugu"]},
    "ur": {"name": "Urdu", "scripts": ["arabic"], "aliases": ["urdu"]},
}


SCHEDULED_LANGUAGE_CODES: list[str] = [
    "as",
    "bn",
    "brx",
    "doi",
    "gu",
    "hi",
    "kn",
    "ks",
    "kok",
    "mai",
    "ml",
    "mni",
    "mr",
    "ne",
    "or",
    "pa",
    "sa",
    "sat",
    "sd",
    "ta",
    "te",
    "ur",
]

ALL_SUPPORTED_LANGUAGE_CODES: list[str] = ["en", *SCHEDULED_LANGUAGE_CODES]

LANGDETECT_CODE_MAP: dict[str, str] = {
    "as": "as",
    "bn": "bn",
    "gu": "gu",
    "hi": "hi",
    "kn": "kn",
    "ml": "ml",
    "mr": "mr",
    "ne": "ne",
    "or": "or",
    "pa": "pa",
    "sa": "sa",
    "sd": "sd",
    "ta": "ta",
    "te": "te",
    "ur": "ur",
    "en": "en",
}

MAJOR_ROMANIZED_HINTS: dict[str, list[str]] = {
    "hi": ["hai", "nahi", "kya", "kyun", "yah", "yeh"],
    "ta": ["enna", "ungal", "illai", "inga", "ippadi"],
    "te": ["emi", "ledu", "meeru", "ikkada", "ante"],
    "bn": ["ki", "na", "hobe", "ache", "tumi"],
    "mr": ["ahe", "nahi", "tumhi", "kaay", "mhanje"],
    "gu": ["che", "nathi", "shu", "tame", "aapde"],
    "kn": ["illa", "enu", "neevu", "ivattu", "yaake"],
    "ml": ["illa", "entha", "ningal", "ivide", "aanu"],
    "pa": ["ki", "nahi", "tusi", "kida", "hai"],
    "ur": ["hai", "nahi", "kya", "kyun", "zaroor"],
}

SCRIPT_RANGES: dict[str, list[tuple[int, int]]] = {
    "devanagari": [(0x0900, 0x097F)],
    "bengali": [(0x0980, 0x09FF)],
    "gurmukhi": [(0x0A00, 0x0A7F)],
    "gujarati": [(0x0A80, 0x0AFF)],
    "odia": [(0x0B00, 0x0B7F)],
    "tamil": [(0x0B80, 0x0BFF)],
    "telugu": [(0x0C00, 0x0C7F)],
    "kannada": [(0x0C80, 0x0CFF)],
    "malayalam": [(0x0D00, 0x0D7F)],
    "arabic": [(0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF)],
    "meitei": [(0xABC0, 0xABFF)],
    "ol_chiki": [(0x1C50, 0x1C7F)],
    "latin": [(0x0041, 0x005A), (0x0061, 0x007A)],
}

SCRIPT_TO_LANGUAGE_CODES: dict[str, list[str]] = {
    "devanagari": ["hi", "mr", "ne", "sa", "mai", "kok", "doi", "brx", "ks", "sd"],
    "bengali": ["bn", "as", "mni"],
    "gurmukhi": ["pa"],
    "gujarati": ["gu"],
    "odia": ["or"],
    "tamil": ["ta"],
    "telugu": ["te"],
    "kannada": ["kn"],
    "malayalam": ["ml"],
    "arabic": ["ur", "ks", "sd"],
    "meitei": ["mni"],
    "ol_chiki": ["sat"],
}


def get_language_name(code_or_name: str | None) -> str:
    if not code_or_name:
        return "English"
    code = normalize_language_code(code_or_name)
    return LANGUAGE_METADATA.get(code, {}).get("name", str(code_or_name))


def normalize_language_code(code_or_name: str | None) -> str:
    if not code_or_name:
        return "en"
    value = str(code_or_name).strip().lower()
    if value in LANGUAGE_METADATA:
        return value
    for code, meta in LANGUAGE_METADATA.items():
        if value == str(meta["name"]).lower():
            return code
        if value in [str(alias).lower() for alias in meta.get("aliases", [])]:
            return code
    return value
