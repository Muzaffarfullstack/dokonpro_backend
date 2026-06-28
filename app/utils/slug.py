import re
import unicodedata

CYRILLIC_TRANSLITERATION = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "j",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "x",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sh",
    "ъ": "",
    "ы": "i",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
    "ў": "o",
    "қ": "q",
    "ғ": "g",
    "ҳ": "h",
}

UZBEK_LATIN_REPLACEMENTS = {
    "ʻ": "",
    "ʼ": "",
    "'": "",
    "`": "",
    "’": "",
}


def _transliterate(value: str) -> str:
    chars: list[str] = []
    for char in value.lower():
        chars.append(CYRILLIC_TRANSLITERATION.get(char, UZBEK_LATIN_REPLACEMENTS.get(char, char)))
    return "".join(chars)


def slugify(value: str) -> str:
    value = _transliterate(value.strip())
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")
