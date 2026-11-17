"""Pure text-normalisation helpers used by the DOCX -> SQLite ETL.

The source document is a Word reference book.  Its tables contain merged
cells, several trade names in one cell and run-on dosing instructions, so the
parser needs a small set of deterministic heuristics.  Everything in this
module is free of ``python-docx`` / database dependencies and can be unit
tested on its own.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Generic cleaning
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")
_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def clean_text(value: Optional[str]) -> str:
    """Collapse all whitespace (including non-breaking spaces) to one space."""

    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", value.replace("\xa0", " ")).strip()


def has_cyrillic(value: str) -> bool:
    return bool(_CYRILLIC_RE.search(value))


def has_latin(value: str) -> bool:
    return bool(_LATIN_RE.search(value))


def normalize_name_ru(value: str) -> str:
    """Turn ``"АМИКАЦИН"`` into ``"Амикацин"`` without touching ``+`` groups."""

    value = clean_text(value).strip(" ,;.:-")
    if not value:
        return ""

    def fix_word(word: str) -> str:
        if not word:
            return word
        if word.isupper():
            # Keep short abbreviations such as "МНН" untouched.
            if len(word) <= 3 and "." in word:
                return word
            return word[:1] + word[1:].lower()
        return word[:1].upper() + word[1:]

    parts = re.split(r"(\s+)", value)
    return "".join(fix_word(part) if part and not part.isspace() else part for part in parts)


# ---------------------------------------------------------------------------
# Table headings: MNN vs pharmacotherapeutic group
# ---------------------------------------------------------------------------

# Words that almost always end a group name in this reference book.  A row
# where all cells are equal and that contains one of these suffixes is a group
# heading, not an active substance.
_GROUP_SUFFIXES = (
    "МИЦИНЫ",
    "ЦИЛЛИНЫ",
    "СПОРИНЫ",
    "ЛИДЫ",
    "ХИНОЛОНЫ",
    "ФУРАНЫ",
    "АМИДЫ",
    "АЗОЛЫ",
    "ГЛИКОЗИДЫ",
    "ГОРМОНЫ",
    "ВИТАМИНЫ",
    "ФЕРМЕНТЫ",
    "СРЕДСТВА",
    "ПРЕПАРАТЫ",
    "БЛОКАТОРЫ",
    "АНТАЦИДЫ",
    "ДИУРЕТИКИ",
    "ИНСУЛИНЫ",
    "АНТИКОАГУЛЯНТЫ",
    "ТРАНКВИЛИЗАТОРЫ",
    "НООТРОПЫ",
    "АНТИОКСИДАНТ",
    "АНТИАГРЕГАНТ",
    "ГАСТРОПРОТЕКТОР",
    "МУКОЛИТИКИ",
    "БРОНХОЛИТИКИ",
    "ПРОТИВОКАШЛЕВЫЕ",
)

_GROUP_EXACT = {
    "БАКТЕРИОФАГИ",
    "ПРОТИВОМИКРОБНЫЕ ПРЕПАРАТЫ",
    "ПРОТИВОПАРАЗИТАРНЫЕ ПРЕПАРАТЫ",
    "ПРОТИВОТУБЕРКУЛЕЗНЫЕ ПРЕПАРАТЫ",
    "ПРОТИВОГРИБКОВЫЕ ПРЕПАРАТЫ",
    "ПРОТИВОВИРУСНЫЕ ПРЕПАРАТЫ",
    "ГЛЮКОКОРТИКОСТЕРОИДЫ",
    "СЕРДЕЧНЫЕ ГЛИКОЗИДЫ",
    "ПИЩЕВАРИТЕЛЬНЫЕ ФЕРМЕНТЫ",
    "СЛАБИТЕЛЬНЫЕ ПРЕПАРАТЫ",
    "ВЕТРОГОННЫЕ ПРЕПАРАТЫ",
    "ПОЛИВИТАМИНЫ",
    "ПРЕПАРАТЫ ЖЕЛЕЗА",
    "ПРЕПАРАТЫ ЙОДА",
    "ИНСУЛИНЫ",
    "АНТИКОАГУЛЯНТЫ ПРЯМОГО ДЕЙСТВИЯ",
    "АКТИВАТОР АГРЕГАЦИИ ТРОМБОЦИТОВ",
}


def is_group_heading(value: str) -> bool:
    """Heuristically decide whether an all-caps line is a group heading."""

    text = clean_text(value)
    if not text or has_latin(text):
        return False
    if text in _GROUP_EXACT:
        return True

    stripped = text.strip(" .:-")
    if not stripped or not has_cyrillic(stripped):
        return False
    if not stripped.isupper():
        return False
    if len(stripped) > 90:
        return False
    if stripped.endswith("."):
        return False

    upper = stripped.upper()
    if any(upper.endswith(suffix) for suffix in _GROUP_SUFFIXES):
        return True

    # Most plural group names end in "Ы"/"И" (ПЕНИЦИЛЛИНЫ, АМИНОГЛИКОЗИДЫ,
    # НИТРОФУРАНЫ, ТРАНКВИЛИЗАТОРЫ).  A single all-caps word with such an
    # ending is far more likely a group than an INN.
    words = re.findall(r"[А-ЯЁ\-]+", upper)
    if len(words) == 1 and len(words[0]) >= 7 and words[0].endswith(("Ы", "И")):
        return True
    return False


def classify_heading(value: str) -> str:
    """Return ``"mnn"``, ``"group"`` or ``"ignore"`` for a repeated row."""

    text = clean_text(value)
    if not text or text in {"-", "–", "—"}:
        return "ignore"
    if text == "не применяется" or text.lower() == "не применяются":
        return "ignore"

    if has_cyrillic(text) and has_latin(text):
        return "mnn"
    if is_group_heading(text):
        return "group"
    if has_latin(text) and not has_cyrillic(text):
        return "mnn"
    if len(text) <= 120 and has_cyrillic(text):
        return "mnn"
    return "ignore"


def parse_mnn(value: str) -> Tuple[str, Optional[str]]:
    """Split ``"АМИКАЦИН Amikacinum"`` into Russian and Latin names."""

    text = clean_text(value)
    if not text:
        return "", None

    latin_match = _LATIN_RE.search(text)
    if not latin_match:
        return normalize_name_ru(text), None

    latin_start = latin_match.start()
    russian = text[:latin_start].strip(" ,;.:-+[]()")
    latin = text[latin_start:].strip()

    # Drop trailing explanatory brackets after the Latin name.
    latin = re.split(r"\s*[\[(]", latin, maxsplit=1)[0].strip(" ,;.:-+")
    latin = re.sub(r"\s+", " ", latin)

    if not russian:
        # A Latin-only heading is still a valid INN.
        return normalize_name_ru(latin), latin

    # Combination headings often contain "[...]" in the Russian part.
    russian = re.split(r"\s*\[", russian, maxsplit=1)[0]
    russian = russian.strip(" ,;.:-+")
    return normalize_name_ru(russian), latin or None


# ---------------------------------------------------------------------------
# Trade names
# ---------------------------------------------------------------------------

_TRADE_NAME_REJECT_RE = re.compile(
    r"(расч[её]т\s+суточной\s+дозы|пример\s+рецепта|rp\.?:)",
    re.IGNORECASE,
)


def _split_outside_parentheses(value: str) -> List[str]:
    parts: List[str] = []
    current: List[str] = []
    depth = 0
    for char in value:
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        if char in ",;" and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return parts


def split_trade_names(value: str) -> List[Tuple[str, Optional[str]]]:
    """Return ``(name, latin_name)`` pairs from a trade-name table cell.

    Cells such as ``"Амоксициллин, Флемоксин Солютаб"`` contain several trade
    names; cells such as ``"Интести-бактериофаг Bacteriophagum intestinalis"``
    contain a Russian name followed by the Latin INN.
    """

    text = clean_text(value)
    if not text or text in {"-", "–", "—"}:
        return []
    if _TRADE_NAME_REJECT_RE.search(text):
        return []
    if len(text) > 250:
        return []

    first_latin = _LATIN_RE.search(text)
    latin_name: Optional[str] = None
    names_part = text

    if first_latin and first_latin.start() > 0 and has_cyrillic(text[: first_latin.start()]):
        names_part = text[: first_latin.start()].strip(" ,;.:-")
        latin_name = text[first_latin.start():].strip(" ,;.:-")
        latin_name = re.sub(r"\s+", " ", latin_name)
        if len(latin_name) < 3 or not _LATIN_RE.search(latin_name):
            latin_name = None

    names_part = names_part.strip(" ,;.:-")
    if not names_part:
        return []

    result: List[Tuple[str, Optional[str]]] = []
    seen = set()
    for index, part in enumerate(_split_outside_parentheses(names_part)):
        name = clean_text(part).strip(" ,;.:-\"«»")
        if not name or len(name) > 100:
            continue
        if name.lower() in {"-", "не применяется", "не применяются"}:
            continue
        if not (has_cyrillic(name) or has_latin(name)):
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append((name, latin_name if index == 0 else None))
    return result


# ---------------------------------------------------------------------------
# Dosage forms and strengths
# ---------------------------------------------------------------------------

_NUM = r"\d+(?:[.,]\d+)?"
_UNIT = r"(?:мкг|мг|мл|г|МЕ|ЕД|%|доз(?:а|ы)?)"

_STRENGTH_TOKEN_RE = re.compile(
    rf"(?<![\w,])(?P<num>{_NUM})\s*"
    rf"(?P<scale>тыс\.?|млн\.?)?\s*"
    rf"(?P<unit>{_UNIT})?"
    rf"(?:\s*/\s*(?P<den_num>{_NUM})?\s*(?P<den_unit>мл|г|мг|доз(?:а|ы)?))?",
    re.IGNORECASE,
)

_EXTRA_DENOMINATOR_RE = re.compile(
    rf"\s*/\s*(?P<num>{_NUM})?\s*(?P<unit>мл|г|мг|доз(?:а|ы)?)",
    re.IGNORECASE,
)

_MASS_UNITS = {"мг", "мкг", "г"}


def _paren_depth(text: str, position: int) -> int:
    depth = 0
    for char in text[:position]:
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
    return depth


def _consume_extra_denominators(text: str, position: int) -> Tuple[str, int]:
    """Consume ``/5 мл`` tails such as ``125 мг/31,25 мг/5 мл``."""

    suffix = ""
    cursor = position
    while True:
        match = _EXTRA_DENOMINATOR_RE.match(text, cursor)
        if not match:
            break
        number = match.group("num")
        unit = match.group("unit")
        suffix += f"/{number + ' ' if number else ''}{unit}"
        cursor = match.end()
    return suffix, cursor


@dataclass(frozen=True)
class Strength:
    value: float
    unit: str
    start: int
    end: int


@dataclass(frozen=True)
class FormDetails:
    base_form: str
    strengths: Tuple[Strength, ...] = field(default_factory=tuple)

    @property
    def first_strength_start(self) -> Optional[int]:
        return self.strengths[0].start if self.strengths else None


def _is_plain_volume(unit: Optional[str], den_unit: Optional[str]) -> bool:
    return bool(unit) and unit.lower().rstrip(".") == "мл" and not den_unit


def _build_unit_label(
    scale: Optional[str],
    unit: str,
    den_num: Optional[str],
    den_unit: Optional[str],
) -> str:
    scale_label = (scale or "").lower().rstrip(".")
    unit_label = unit.replace(".", "").strip()
    if scale_label:
        unit_label = f"{scale_label} {unit_label}"

    if den_unit:
        den_unit_label = den_unit.replace(".", "").strip()
        if den_num:
            denominator = f"{den_num} {den_unit_label}"
        else:
            denominator = den_unit_label
        if den_unit_label.lower() in _MASS_UNITS:
            unit_label = f"{unit_label} + {denominator}"
        else:
            unit_label = f"{unit_label}/{denominator}"
    return _WHITESPACE_RE.sub(" ", unit_label).strip()


def _strength_from_match(
    number: str,
    scale: Optional[str],
    unit: str,
    den_num: Optional[str],
    den_unit: Optional[str],
    start: int,
    end: int,
) -> Strength:
    value = float(number.replace(",", "."))
    return Strength(
        value=value,
        unit=_build_unit_label(scale, unit, den_num, den_unit),
        start=start,
        end=end,
    )


def parse_form_details(value: str) -> FormDetails:
    """Extract the dosage form and all strengths from a "Форма выпуска" cell.

    Examples::

        "Табл. 250 мг, 500 мг"                    -> base "Табл.", 250/500 мг
        "Пор. ... 125 мг/5 мл, 250 мг/5 мл"       -> two concentrations
        "Пор. ... 600 тыс., 1,2 млн., 2,4 млн. ЕД" -> three amounts
        "Капли назальные 0,05% и 0,1% (10 мл)"    -> two percentages
    """

    text = _AGE_PAREN_RE.sub(" ", clean_text(value))
    if not text:
        return FormDetails(base_form="", strengths=())

    matches = list(_STRENGTH_TOKEN_RE.finditer(text))
    strengths: List[Strength] = []
    pending: List[Tuple[str, Optional[str], int, int]] = []
    last_end: Optional[int] = None

    def flush_pending(unit: str, den_num: Optional[str], den_unit: Optional[str]) -> None:
        nonlocal last_end
        for pnum, pscale, pstart, pend in pending:
            strengths.append(
                _strength_from_match(pnum, pscale, unit, den_num, den_unit, pstart, pend)
            )
            last_end = pend
        pending.clear()

    for match in matches:
        if _paren_depth(text, match.start()) > 0:
            # Package / age details in brackets are not strengths.
            continue

        number = match.group("num")
        scale = match.group("scale")
        unit = match.group("unit")
        den_num = match.group("den_num")
        den_unit = match.group("den_unit")

        if _is_plain_volume(unit, den_unit):
            # Package volume, not a strength.  It also terminates any pending
            # number list ("1,5-2 мл").
            pending.clear()
            continue

        if not unit and not den_unit:
            pending.append((number, scale, match.start(), match.end()))
            continue

        assert unit is not None  # den_unit implies a unit in the regex
        flush_pending(unit, den_num, den_unit)

        candidate = _strength_from_match(
            number, scale, unit, den_num, den_unit, match.start(), match.end()
        )
        extra_suffix, extra_end = _consume_extra_denominators(text, match.end())
        if extra_suffix:
            candidate = Strength(
                value=candidate.value,
                unit=f"{candidate.unit}{extra_suffix}",
                start=candidate.start,
                end=extra_end,
            )

        # Combine "500 мг + 125 мг", "25 мкг + 50 мкг/доза",
        # "125000 МЕ + 5 мг" into one combination product.
        if (
            strengths
            and last_end is not None
            and _WHITESPACE_RE.sub("", text[last_end: match.start()]) == "+"
        ):
            previous = strengths[-1]
            strengths[-1] = Strength(
                value=previous.value,
                unit=f"{previous.unit} + {candidate.unit}",
                start=previous.start,
                end=candidate.end,
            )
            last_end = candidate.end
            continue

        strengths.append(candidate)
        last_end = candidate.end

    # Deduplicate identical value/unit pairs while keeping the source order.
    deduped: List[Strength] = []
    seen = set()
    for item in strengths:
        key = (item.value, item.unit.casefold())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    # "200 доз" in an inhaler cell is the package size, not the strength.
    # Keep it only when it is the sole numeric value (e.g. probiotics "5 доз").
    if any(not _is_dose_count(item.unit) for item in deduped):
        deduped = [item for item in deduped if not _is_dose_count(item.unit)]

    first_start = deduped[0].start if deduped else None
    base = text if first_start is None else text[:first_start]
    base = base.strip(" ,;.:-–—")
    return FormDetails(base_form=base, strengths=tuple(deduped))


def _is_dose_count(unit: str) -> bool:
    normalized = unit.casefold().strip()
    return normalized in {"доз", "доза", "дозы", "доз."}


_FORM_KEYWORDS_RE = re.compile(
    r"(табл|капс|порош|пор\.|раствор|р-р|суспенз|сусп\.|сироп|мазь|крем|гель|капл|"
    r"спрей|супп|гранул|гран\.|аэрозол|аэр\.|лиофил|лиоф\.|эмульс|шампун|паст|драже|"
    r"концентрат|пластыр|карандаш|плёнк|пленк|жидкост|сбор|настойк|капсул)",
    re.IGNORECASE,
)

_FORM_REPLACEMENTS = (
    (r"\bтабл\.,\s*покр\.\s*обол\.?", "Таблетки, покрытые оболочкой"),
    (r"\bтабл\.,\s*покр\.\s*об(?:\.(?![\wа-яёА-ЯЁ])|(?=\s|,|$))", "Таблетки, покрытые оболочкой"),
    (r"\bтабл\.\s*покр\.\s*кишечнорастворимой\s*обол\.?", "Таблетки, покрытые кишечнорастворимой оболочкой"),
    (r"\bтабл\.\s*покр\.\s*пленочной\s*оболочкой", "Таблетки, покрытые плёночной оболочкой"),
    (r"\bтабл\.\s*покр\.\s*плёночной\s*оболочкой", "Таблетки, покрытые плёночной оболочкой"),
    (r"\bтабл\.,\s*покр\.\s*пленочной\s*оболочкой", "Таблетки, покрытые плёночной оболочкой"),
    (r"\bтабл\.,\s*покр\.\s*плёночной\s*оболочкой", "Таблетки, покрытые плёночной оболочкой"),
    (r"\bтабл\.\s*диспергируемые", "Таблетки диспергируемые"),
    (r"\bтабл\.\s*для\s*рассасывания", "Таблетки для рассасывания"),
    (r"\bд/приг\.\s*сусп\.", "для приготовления суспензии"),
    (r"\bд/приг\.\s*р-ра", "для приготовления раствора"),
    (r"\bд/приг\.", "для приготовления"),
    (r"\bд/приема\b", "для приёма"),
    (r"\bд/ингал\s+доз\.?", "для ингаляций дозированный"),
    (r"\bд/инг\.\s*доз\.?", "для ингаляций дозированный"),
    (r"\bд/ингал\b", "для ингаляций"),
    (r"\bд/инг\.", "для ингаляций"),
    (r"\bд/инг\b", "для ингаляций"),
    (r"\bд/ин\.", "для инъекций"),
    (r"\bпри[её]ма\s+п/о\b", "приёма внутрь"),
    (r"\bп/о\b", "приёма внутрь"),
    (r"\bаэр\.", "Аэрозоль"),
    (r"\bаэр\b", "Аэрозоль"),
    (r"\bпокр\.\s*обол\.?", "покрытые оболочкой"),
    (r"\bпокр\.\s*об(?:\.(?![\wа-яёА-ЯЁ])|(?=\s|,|$))", "покрытые оболочкой"),
    (r"\bтабл\.", "Таблетки"),
    (r"\bтабл\b", "Таблетки"),
    (r"\bкапс\.", "Капсулы"),
    (r"\bкапс\b", "Капсулы"),
    (r"\bпор\.", "Порошок"),
    (r"\bпор\b", "Порошок"),
    (r"\bр-ра\b", "раствора"),
    (r"\bр-р\b", "раствор"),
    (r"\bсусп\.", "суспензия"),
    (r"\bсусп\b", "суспензия"),
    (r"\bсупп\.", "Суппозитории"),
    (r"\bсупп\b", "Суппозитории"),
    (r"\bгран\.", "Гранулы"),
    (r"\bгран\b", "Гранулы"),
    (r"\bсир\.", "Сироп"),
    (r"\bсир\b", "Сироп"),
    (r"\bлиоф\.", "Лиофилизат"),
    (r"\bлиоф\b", "Лиофилизат"),
    (r"\bаэроз\.", "Аэрозоль"),
    (r"\bаэроз\b", "Аэрозоль"),
    (r"\bрект\.", "ректальные"),
    (r"\bрект\b", "ректальные"),
    (r"\bвагин\.", "вагинальные"),
    (r"\bвагин\b", "вагинальные"),
    (r"\bназал\.", "назальные"),
    (r"\bназал\b", "назальные"),
    (r"\bдозир\.", "дозированный"),
    (r"\bдозир\b", "дозированный"),
    (r"\bнаруж\.", "наружного"),
    (r"\bнаруж\b", "наружного"),
    (r"\bместн\.", "местного"),
    (r"\bместн\b", "местного"),
    (r"\bпримен\.", "применения"),
    (r"\bпримен\b", "применения"),
    (r"\bраств\.", "раствор"),
    (r"\bраств\b", "раствор"),
)

_PACKAGE_PAREN_RE = re.compile(
    r"\((?:[^()]*(?:флак|амп|туб|пакет|пакетик|флакон|тюбик|шприц|контейнер|банк|"
    r"бутыл|саше|стрип|уп\.|упак|кор\.|пач|блистер|капельниц|дозатор)[^()]*)\)",
    re.IGNORECASE,
)
_AGE_PAREN_RE = re.compile(
    r"\([^()]*(?:\bлет\b|\bгод\b|\bгода\b|\bмес\b|\bмесяц)[^()]*\)",
    re.IGNORECASE,
)
_TRAILING_PACKAGE_RE = re.compile(
    r"[,;]?\s*(?:фл\.(?!\w)|флак\.(?!\w)|амп\.(?!\w)|туб\.(?!\w)|флакон\w*|ампул\w*|туб\w*|"
    r"уп\.(?!\w)|упак\w*|пачк\w*|блистер\w*)(?!\w).*$",
    re.IGNORECASE,
)
_TRAILING_QUANTITY_RE = re.compile(
    r"(?:[,;\s]*(?:\d+(?:[.,]\d+)?\s*(?:(?:или|и)\s*)?)+"
    r"(?:мл|доз(?:а|ы)?|табл\w*|капс\w*|шт\w*))+[,;\s]*$",
    re.IGNORECASE,
)


def clean_dosage_form(base_form: str, fallback: Optional[str] = None) -> Optional[str]:
    """Expand common abbreviations and remove package / age brackets."""

    value = clean_text(base_form)
    if not value:
        return fallback

    value = _AGE_PAREN_RE.sub(" ", value)
    value = _PACKAGE_PAREN_RE.sub(" ", value)
    # The source document occasionally truncates a bracket ("(флак. 100,150 и").
    value = re.sub(r"\([^()]*$", " ", value)
    value = re.sub(r"\([^()]*\)", " ", value)
    value = re.sub(r"\s*[,;]\s*", ", ", value)

    for pattern, replacement in _FORM_REPLACEMENTS:
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)

    value = _TRAILING_PACKAGE_RE.sub(" ", value)
    value = _TRAILING_QUANTITY_RE.sub(" ", value)
    value = clean_text(value).strip(" ,;.:-–—")
    value = re.sub(r"^[А-ЯЁа-яё]", lambda m: m.group(0).upper(), value)
    value = re.sub(r"\s+", " ", value)

    if not value or not _FORM_KEYWORDS_RE.search(value):
        return fallback
    if len(value) > 140:
        value = value[:137].rstrip(" ,;.-") + "…"
    return value


# ---------------------------------------------------------------------------
# Age ranges and regimen splitting
# ---------------------------------------------------------------------------

_MONTH_PATTERNS = (
    re.compile(
        r"от\s+(\d+(?:[.,]\d+)?)\s*(мес[а-яё]*|год[а-яё]*|лет)\s+до\s+"
        r"(\d+(?:[.,]\d+)?)\s*(мес[а-яё]*|год[а-яё]*|лет)",
        re.IGNORECASE,
    ),
    re.compile(
        r"с\s+(\d+(?:[.,]\d+)?)\s*(мес[а-яё]*|год[а-яё]*|лет)\s+до\s+"
        r"(\d+(?:[.,]\d+)?)\s*(мес[а-яё]*|год[а-яё]*|лет)",
        re.IGNORECASE,
    ),
    re.compile(
        r"от\s+(\d+(?:[.,]\d+)?)\s+до\s+(\d+(?:[.,]\d+)?)\s*"
        r"(мес[а-яё]*|год[а-яё]*|лет)",
        re.IGNORECASE,
    ),
    re.compile(
        r"с\s+(\d+(?:[.,]\d+)?)\s+до\s+(\d+(?:[.,]\d+)?)\s*"
        r"(мес[а-яё]*|год[а-яё]*|лет)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d+(?:[.,]\d+)?)\s*(мес[а-яё]*|год[а-яё]*|лет)\s*[-–—]\s*"
        r"(\d+(?:[.,]\d+)?)\s*(мес[а-яё]*|год[а-яё]*|лет)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*"
        r"(мес[а-яё]*|год[а-яё]*|лет)",
        re.IGNORECASE,
    ),
)

_MIN_AGE_RE = re.compile(
    r"(?:старше|с|от)\s+(\d+(?:[.,]\d+)?)\s*(мес[а-яё]*|год[а-яё]*|лет)",
    re.IGNORECASE,
)
_MAX_AGE_RE = re.compile(
    r"до\s+(\d+(?:[.,]\d+)?)\s*(мес[а-яё]*|год[а-яё]*|лет)",
    re.IGNORECASE,
)
_SINGLE_AGE_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(мес[а-яё]*|год[а-яё]*|лет)", re.IGNORECASE
)


def _to_months(number: str, unit: str) -> int:
    value = float(number.replace(",", "."))
    normalized = unit.lower()
    if normalized.startswith("мес"):
        return int(round(value))
    return int(round(value * 12))


def parse_age_range(value: str) -> Tuple[Optional[int], Optional[int]]:
    """Return ``(age_min_months, age_max_months)`` from a regimen sentence."""

    text = clean_text(value).lower().replace("ё", "е")
    if not text:
        return None, None

    for pattern in _MONTH_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 3:
            low, high, unit = groups
            return _to_months(low, unit), _to_months(high, unit)
        low, low_unit, high, high_unit = groups
        return _to_months(low, low_unit), _to_months(high, high_unit)

    match = _MAX_AGE_RE.search(text)
    if match:
        return 0, _to_months(match.group(1), match.group(2))

    match = _MIN_AGE_RE.search(text)
    if match:
        return _to_months(match.group(1), match.group(2)), None

    if "с рождения" in text:
        return 0, None
    if "новорожденн" in text or "новорождённ" in text or "недоношенн" in text:
        return 0, 1
    if "взросл" in text:
        return 216, None
    if "нет возрастных ограничений" in text:
        return None, None

    match = _SINGLE_AGE_RE.search(text)
    if match:
        return _to_months(match.group(1), match.group(2)), None
    return None, None


_AGE_MARKER_RE = re.compile(
    r"(?i)(?:"
    r"(?:детям?\s+)?(?:старше|от|с)\s+\d+(?:[.,]\d+)?\s*(?:мес[а-яё]*|год[а-яё]*|лет)"
    r"|(?:дет(?:и|ям)\s+)?\d+(?:[.,]\d+)?\s*[-–—]\s*\d+(?:[.,]\d+)?\s*"
    r"(?:мес[а-яё]*|год[а-яё]*|лет)"
    r"|(?:взрослые|взрослым|новорождённые|новорожденные|недоношенные|недоношенным)\b"
    r")"
)


def _split_age_blocks(text: str) -> List[str]:
    """Split on non-overlapping age markers without zero-width regex issues."""

    starts = [match.start() for match in _AGE_MARKER_RE.finditer(text)]
    if not starts:
        return [text]

    parts: List[str] = []
    if starts[0] > 0:
        parts.append(text[: starts[0]])
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        parts.append(text[start:end])
    return parts


@dataclass(frozen=True)
class Regimen:
    age_min_months: Optional[int]
    age_max_months: Optional[int]
    regimen_text: str
    course_note: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "age_min_months": self.age_min_months,
            "age_max_months": self.age_max_months,
            "regimen_text": self.regimen_text,
            "course_note": self.course_note,
        }


def split_regimens(regimen_text: str, course_text: Optional[str] = None) -> List[Regimen]:
    """Split a run-on "Режим дозирования" cell into age-specific entries."""

    text = clean_text(regimen_text)
    if not text:
        return []
    if len(text) > 4000:
        text = text[:3997].rstrip(" ,;.-") + "…"

    course = clean_text(course_text or "") or None
    parts = [part.strip() for part in _split_age_blocks(text) if part.strip()]

    if not parts:
        parts = [text]

    # A leading instruction without an age ("Внутрь, после еды...") belongs to
    # the first age block rather than becoming a separate "all ages" entry.
    if len(parts) > 1 and parse_age_range(parts[0]) == (None, None):
        parts[1] = f"{parts[0]} {parts[1]}".strip()
        parts.pop(0)

    result: List[Regimen] = []
    seen = set()
    for part in parts:
        part = clean_text(part).strip(" ,;.-")
        if not part:
            continue
        if len(part) < 6 and not re.search(r"\d", part):
            continue
        key = part.casefold()
        if key in seen:
            continue
        seen.add(key)
        age_min, age_max = parse_age_range(part)
        result.append(
            Regimen(
                age_min_months=age_min,
                age_max_months=age_max,
                regimen_text=part,
                course_note=course,
            )
        )
    if not result:
        result.append(
            Regimen(
                age_min_months=None,
                age_max_months=None,
                regimen_text=text,
                course_note=course,
            )
        )
    return result


def regimens_to_json(regimens: Iterable[Regimen]) -> str:
    return json.dumps(
        [regimen.as_dict() for regimen in regimens],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def decode_regimens(raw_json: Optional[str]) -> List[dict]:
    """Decode and validate a ``dosing_regimen`` JSON payload (used by tests)."""

    if not raw_json:
        return []
    try:
        payload = json.loads(raw_json)
    except (TypeError, ValueError):
        return []
    if not isinstance(payload, list):
        return []
    valid: List[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        text = item.get("regimen_text")
        if not isinstance(text, str) or not text.strip():
            continue
        valid.append(item)
    return valid
