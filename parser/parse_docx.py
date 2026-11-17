#!/usr/bin/env python3
"""Convert the pediatric drug reference DOCX into the bundled SQLite database.

The script is intentionally standalone: no SQLAlchemy, no PostgreSQL and no
imports from the mobile application. It writes the normalized SQLite schema
used by the app and stores dosing instructions as JSON text in
``drug_product.dosing_regimen``.

Typical usage
-------------

Fresh database from the document::

    python3 parser/parse_docx.py \
        --input "parser/Справочник Педиатрия 2017_2024.docx" \
        --output composeApp/src/commonMain/composeResources/files/med_expert.db

Verify the bundled file without changing it::

    python3 parser/parse_docx.py --verify
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

# Allow both ``python parser/parse_docx.py`` and ``python -m parser.parse_docx``.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parser.db_utils import Database, VerificationError, write_report
from parser.normalization import (
    Regimen,
    classify_heading,
    clean_dosage_form,
    clean_text,
    has_latin,
    is_group_heading,
    normalize_name_ru,
    parse_form_details,
    parse_mnn,
    split_regimens,
    split_trade_names,
)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
DEFAULT_INPUT = SCRIPT_DIR / "Справочник Педиатрия 2017_2024.docx"
DEFAULT_OUTPUT = ROOT / "composeApp/src/commonMain/composeResources/files/med_expert.db"

_SECTION_RE = re.compile(r"^(\d+\.\d+)\.\s*(.+)$")
_SECTION_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)*\.?\s*")


@dataclass
class ParsedProduct:
    trade_name: str
    trade_name_latin: Optional[str]
    substances: List[Tuple[str, Optional[str]]] = field(default_factory=list)
    group_path: Tuple[str, ...] = ()
    dosage_form: Optional[str] = None
    strength_value: Optional[float] = None
    strength_unit: Optional[str] = None
    regimens: List[Regimen] = field(default_factory=list)


@dataclass
class ParseStats:
    tables_total: int = 0
    drug_tables: int = 0
    rows: int = 0
    mnn_headings: int = 0
    group_headings: int = 0
    skipped_rows: int = 0
    products: int = 0
    products_without_strength: int = 0
    products_without_regimens: int = 0
    interactions: int = 0
    skipped_samples: List[dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def skip(self, reason: str, text: str = "") -> None:
        self.skipped_rows += 1
        if len(self.skipped_samples) < 40:
            self.skipped_samples.append(
                {"reason": reason, "text": clean_text(text)[:180]}
            )


@dataclass
class ParseResult:
    products: List[ParsedProduct]
    interactions: List[dict]
    stats: ParseStats


def _iter_block_items(document):  # type: ignore[no-untyped-def]
    """Yield paragraphs and tables in their original DOCX order."""

    from docx.document import Document as _Document
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    if isinstance(document, _Document):
        parent_elm = document.element.body
    else:
        parent_elm = document._tc

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def _semantic_columns(headers: Sequence[str]) -> List[str]:
    result: List[str] = []
    for header in headers:
        if not result or result[-1] != header:
            result.append(header)
    return result


def _group_consecutive(cells: Sequence[str]) -> List[str]:
    groups: List[List[str]] = []
    for cell in cells:
        if groups and groups[-1][0] == cell:
            groups[-1].append(cell)
        else:
            groups.append([cell])
    return [group[0] for group in groups]


def _role(header: str) -> Optional[str]:
    normalized = header.lower().strip()
    if "торговое" in normalized or "препарат" in normalized or "мнн" in normalized:
        return "trade"
    if "форма" in normalized:
        return "form"
    if "режим" in normalized or "дозиров" in normalized:
        return "regimen"
    if "курс" in normalized:
        return "course"
    return None


def _normalize_group_name(value: str) -> str:
    text = clean_text(value).strip(" .:;-–—")
    text = _SECTION_NUMBER_RE.sub("", text).strip()
    if not text:
        return ""
    if text.isupper():
        text = normalize_name_ru(text)
    if len(text) > 180:
        text = text[:177].rstrip(" ,;.-") + "…"
    return text


def _is_paragraph_group(value: str) -> bool:
    text = clean_text(value).strip(" .:;-–—")
    if not text or has_latin(text) or len(text) > 60:
        return False
    if is_group_heading(text):
        return True
    # The book also uses title-case single-word groups ("Бактериофаги").
    return (
        " " not in text
        and len(text) >= 6
        and text[:1].isupper()
        and text.lower().endswith(("и", "ы"))
    )


def _looks_like_form(value: str) -> bool:
    return bool(
        re.search(
            r"(табл|капс|порош|пор\.|раствор|р-р|суспенз|сусп\.|сироп|мазь|крем|"
            r"гель|капл|спрей|супп|гранул|гран\.|аэрозол|лиофил|лиоф\.|эмульс|"
            r"шампун|пастил|драже|концентрат|пластыр|жидкост|сбор|настойк|капсул)",
            value,
            re.IGNORECASE,
        )
    )


class DocxParser:
    def __init__(self) -> None:
        self.stats = ParseStats()
        self.products: Dict[tuple, ParsedProduct] = {}
        self.known_substances: Dict[str, Tuple[str, Optional[str]]] = {}
        self.interactions: List[dict] = []
        self.interaction_category: Optional[str] = None

        self.in_section_2 = False
        self.section_name: Optional[str] = None
        self.paragraph_group: Optional[str] = None
        self.table_group: Optional[str] = None
        self.current_substance: Optional[Tuple[str, Optional[str]]] = None

        self.previous_keys: List[tuple] = []
        self.previous_keys_by_name: Dict[str, List[tuple]] = {}
        self.previous_trade_names: List[Tuple[str, Optional[str]]] = []
        self.previous_form: Optional[str] = None
        self.previous_regimens: List[Regimen] = []

    # -- group / heading state ------------------------------------------
    def _group_path(self) -> Tuple[str, ...]:
        path: List[str] = []
        for value in (self.section_name, self.paragraph_group, self.table_group):
            if value and (not path or path[-1] != value):
                path.append(value)
        return tuple(path[:3])

    def _reset_row_state(self) -> None:
        self.previous_keys = []
        self.previous_keys_by_name = {}
        self.previous_trade_names = []
        self.previous_form = None
        self.previous_regimens = []

    # -- product storage ------------------------------------------------
    @staticmethod
    def _key(
        trade_name: str,
        dosage_form: Optional[str],
        strength_value: Optional[float],
        strength_unit: Optional[str],
    ) -> tuple:
        return (
            trade_name.casefold(),
            (dosage_form or "").casefold(),
            None if strength_value is None else round(float(strength_value), 4),
            (strength_unit or "").casefold(),
        )

    def _add_product(
        self,
        trade_name: str,
        trade_name_latin: Optional[str],
        group_path: Sequence[str],
        dosage_form: Optional[str],
        strength_value: Optional[float],
        strength_unit: Optional[str],
        regimens: Sequence[Regimen],
        substance: Optional[Tuple[str, Optional[str]]],
    ) -> Optional[tuple]:
        if not trade_name:
            return None

        key = self._key(trade_name, dosage_form, strength_value, strength_unit)
        product = self.products.get(key)
        if product is None:
            product = ParsedProduct(
                trade_name=trade_name,
                trade_name_latin=trade_name_latin,
                group_path=tuple(group_path),
                dosage_form=dosage_form,
                strength_value=strength_value,
                strength_unit=strength_unit,
            )
            self.products[key] = product
            self.stats.products += 1
            if strength_value is None:
                self.stats.products_without_strength += 1
        else:
            if not product.group_path and group_path:
                product.group_path = tuple(group_path)
            if product.dosage_form is None and dosage_form:
                product.dosage_form = dosage_form
            if product.trade_name_latin is None and trade_name_latin:
                product.trade_name_latin = trade_name_latin

        if substance and substance[0]:
            if all(name.casefold() != substance[0].casefold() for name, _ in product.substances):
                product.substances.append(substance)

        existing_texts = {item.regimen_text.casefold() for item in product.regimens}
        for regimen in regimens:
            if regimen.regimen_text.casefold() in existing_texts:
                continue
            existing_texts.add(regimen.regimen_text.casefold())
            product.regimens.append(regimen)

        if not product.regimens:
            self.stats.products_without_regimens += 1
        return key

    def _append_regimens(self, keys: Iterable[tuple], regimen_text: str, course_text: str) -> None:
        regimens = split_regimens(regimen_text, course_text)
        if not regimens:
            return
        for key in keys:
            product = self.products.get(key)
            if product is None:
                continue
            existing_texts = {item.regimen_text.casefold() for item in product.regimens}
            for regimen in regimens:
                if regimen.regimen_text.casefold() in existing_texts:
                    continue
                existing_texts.add(regimen.regimen_text.casefold())
                product.regimens.append(regimen)

    # -- row handling ---------------------------------------------------
    def _handle_heading(self, text: str) -> None:
        kind = classify_heading(text)
        if kind == "group":
            self.table_group = _normalize_group_name(text)
            self.current_substance = None
            self._reset_row_state()
            self.stats.group_headings += 1
        elif kind == "mnn":
            name_ru, name_latin = parse_mnn(text)
            if not name_ru:
                self.stats.skip("empty-mnn", text)
                return
            self.current_substance = (name_ru, name_latin)
            self.known_substances[name_ru.casefold()] = self.current_substance
            self._reset_row_state()
            self.stats.mnn_headings += 1
        else:
            self.stats.skip("heading-ignored", text)

    def _fallback_substance(
        self, trade_names: Sequence[Tuple[str, Optional[str]]]
    ) -> Optional[Tuple[str, Optional[str]]]:
        if self.current_substance:
            return self.current_substance
        for name, _ in trade_names:
            found = self.known_substances.get(name.casefold())
            if found:
                return found
        return None

    def _handle_data_row(
        self,
        trade_text: str,
        form_text: str,
        regimen_text: str,
        course_text: str,
    ) -> None:
        self.stats.rows += 1

        if "Rp.:" in trade_text or "Пример рецепта" in trade_text:
            self.stats.skip("recipe-example", trade_text)
            return
        if trade_text in {"-", "–", "—"}:
            self.stats.skip("empty-trade-name", trade_text)
            return

        # Continuation of the previous product's dosing block.
        if not trade_text and not form_text:
            if self.previous_keys and (regimen_text or course_text):
                self._append_regimens(self.previous_keys, regimen_text, course_text)
            else:
                self.stats.skip("empty-continuation", regimen_text)
            return

        trade_names: List[Tuple[str, Optional[str]]] = []
        if trade_text:
            trade_names = split_trade_names(trade_text)
            if not trade_names:
                self.stats.skip("unparseable-trade-name", trade_text)
                return

        # A form-only row continues the previous trade names, e.g.
        # "(амп.) 2 мл и 4 мл 250 мг/мл" after "Р-р для в/м и в/в введения".
        if not trade_text:
            if not self.previous_trade_names:
                self.stats.skip("form-without-product", form_text)
                return
            trade_names = list(self.previous_trade_names)

            if self.previous_form and (
                form_text.startswith("(") or not _looks_like_form(form_text)
            ):
                form_text = f"{self.previous_form} {form_text}".strip()
        elif not form_text:
            # The trade name repeats with a separate dosing block.
            name_keys = self.previous_keys_by_name.get(trade_names[0][0].casefold())
            if name_keys and regimen_text:
                self._append_regimens(name_keys, regimen_text, course_text)
                self.previous_keys = name_keys
                self.previous_trade_names = list(trade_names)
                self.previous_regimens = split_regimens(regimen_text, course_text)
                return
            form_text = self.previous_form or ""

        if not form_text:
            self.stats.skip("missing-dosage-form", trade_text)
            return

        details = parse_form_details(form_text)
        dosage_form = clean_dosage_form(details.base_form, fallback=self.previous_form)
        if dosage_form is None and not _looks_like_form(form_text):
            dosage_form = self.previous_form

        regimens = split_regimens(regimen_text, course_text)
        if not regimens and self.previous_regimens:
            # A form-only continuation row (e.g. additional strengths of the
            # previous product) inherits the dosing block above it.
            regimens = list(self.previous_regimens)
        substance = self._fallback_substance(trade_names)
        strengths = list(details.strengths) or [None]
        group_path = self._group_path()

        keys: List[tuple] = []
        keys_by_name: Dict[str, List[tuple]] = {}
        for trade_name, trade_name_latin in trade_names:
            for strength in strengths:
                key = self._add_product(
                    trade_name=trade_name,
                    trade_name_latin=trade_name_latin,
                    group_path=group_path,
                    dosage_form=dosage_form,
                    strength_value=None if strength is None else strength.value,
                    strength_unit=None if strength is None else strength.unit,
                    regimens=regimens,
                    substance=substance,
                )
                if key is None:
                    continue
                keys.append(key)
                keys_by_name.setdefault(trade_name.casefold(), []).append(key)

        if not keys:
            self.stats.skip("no-product-created", trade_text)
            return

        self.previous_keys = keys
        self.previous_keys_by_name = keys_by_name
        self.previous_trade_names = list(trade_names)
        self.previous_form = dosage_form or self.previous_form
        self.previous_regimens = list(regimens)

    # -- table handling -------------------------------------------------
    def _handle_table(self, table) -> None:  # type: ignore[no-untyped-def]
        self.stats.tables_total += 1
        if self._handle_interaction_table(table):
            return
        if not self.in_section_2:
            return
        if len(table.rows) < 2:
            return

        headers = [clean_text(cell.text) for cell in table.rows[0].cells]
        if not any(headers):
            return

        semantic = _semantic_columns(headers)
        roles = [_role(header) for header in semantic]
        if any(role is None for role in roles):
            return
        if not {"trade", "form", "regimen"}.issubset(set(roles)):
            return

        self.stats.drug_tables += 1
        role_first_index: Dict[str, int] = {}
        for index, header in enumerate(headers):
            role = _role(header)
            if role and role not in role_first_index:
                role_first_index[role] = index

        for row in table.rows[1:]:
            cells = [clean_text(cell.text) for cell in row.cells]
            if not any(cells):
                continue

            unique = set(cells)
            if len(unique) == 1 and cells[0]:
                self._handle_heading(cells[0])
                continue

            groups = _group_consecutive(cells)
            if len(groups) == len(semantic):
                values = dict(zip(roles, groups))
            else:
                values = {}
                for role, index in role_first_index.items():
                    values[role] = cells[index] if index < len(cells) else ""

            trade_text = clean_text(values.get("trade", ""))
            form_text = clean_text(values.get("form", ""))
            regimen_text = clean_text(values.get("regimen", ""))
            course_text = clean_text(values.get("course", ""))

            if (
                course_text
                and regimen_text
                and course_text == regimen_text
                and cells
                and cells[-1] != course_text
            ):
                course_text = cells[-1]

            self._handle_data_row(trade_text, form_text, regimen_text, course_text)

    def _handle_interaction_table(self, table) -> bool:  # type: ignore[no-untyped-def]
        if not table.rows:
            return False
        header = " ".join(clean_text(cell.text).lower() for cell in table.rows[0].cells)
        if "взаимодействующ" not in header or "результат" not in header:
            return False

        for row in table.rows[1:]:
            cells = [clean_text(cell.text) for cell in row.cells]
            values = list(dict.fromkeys(value for value in cells if value))
            if not values:
                continue
            if len(values) == 1:
                self.interaction_category = values[0]
                continue
            if len(values) < 3:
                self.stats.skip("interaction-row-unrecognized", " | ".join(values))
                continue
            self.interactions.append(
                {
                    "substance_a_name": values[0],
                    "substance_b_name": values[1],
                    "interaction_text": values[-1],
                    "category_name": self.interaction_category,
                }
            )
        self.stats.interactions = len(self.interactions)
        return True

    # -- paragraphs -----------------------------------------------------
    def _handle_paragraph(self, text: str) -> None:
        if not text:
            return

        if text.startswith("Раздел 2"):
            self.in_section_2 = True
            self.section_name = None
            self.paragraph_group = None
            self.table_group = None
            self.current_substance = None
            self._reset_row_state()
            return
        if re.match(r"^Раздел\s+[3-9]", text):
            self.in_section_2 = False
            return
        if not self.in_section_2:
            return

        section_match = _SECTION_RE.match(text)
        if section_match and section_match.group(1).startswith("2."):
            self.section_name = _normalize_group_name(section_match.group(2))
            self.paragraph_group = None
            self.table_group = None
            self.current_substance = None
            self._reset_row_state()
            return

        if _is_paragraph_group(text):
            group = _normalize_group_name(text)
            if group and group != self.paragraph_group:
                self.paragraph_group = group
                self.table_group = None
                self.current_substance = None
                self._reset_row_state()

    # -- public API -----------------------------------------------------
    def parse(self, path: Path) -> ParseResult:
        try:
            from docx import Document
        except ImportError as error:  # pragma: no cover - command line path
            raise RuntimeError(
                "python-docx is required to parse the source document. "
                "Install it with: python3 -m pip install -r parser/requirements.txt"
            ) from error

        document = Document(str(path))
        for block in _iter_block_items(document):
            if block.__class__.__name__ == "Paragraph":
                self._handle_paragraph(clean_text(block.text))
            else:
                self._handle_table(block)

        return ParseResult(
            products=list(self.products.values()),
            interactions=self.interactions,
            stats=self.stats,
        )


def parse_docx(path: Path | str) -> ParseResult:
    return DocxParser().parse(Path(path))


def build_database(
    input_path: Path | str,
    output_path: Path | str,
    report_path: Path | str | None = None,
) -> dict:
    started = time.time()
    parsed = parse_docx(input_path)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, staging_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".building", dir=destination.parent
    )
    os.close(descriptor)
    staging = Path(staging_name)

    try:
        with Database(staging, merge=False) as database:
            for product in parsed.products:
                database.save_product(
                    trade_name=product.trade_name,
                    trade_name_latin=product.trade_name_latin,
                    substances=product.substances,
                    group_path=product.group_path,
                    dosage_form=product.dosage_form,
                    strength_value=product.strength_value,
                    strength_unit=product.strength_unit,
                    regimens=product.regimens,
                )
            for interaction in parsed.interactions:
                database.add_interaction(**interaction)
            database.connection.commit()
            database.vacuum()
            verification = database.verify()
            verification["inserted_products"] = database.inserted_products
            verification["updated_products"] = database.updated_products
            verification["kept_curated_products"] = database.kept_curated_products

        os.replace(staging, destination)
        verification["path"] = str(destination)
    finally:
        for suffix in ("", "-wal", "-shm", "-journal"):
            candidate = Path(str(staging) + suffix)
            if candidate.exists():
                candidate.unlink()

    report = {
        "input": str(Path(input_path)),
        "output": str(Path(output_path)),
        "merge": False,
        "elapsed_seconds": round(time.time() - started, 2),
        "parse": {
            "tables_total": parsed.stats.tables_total,
            "drug_tables": parsed.stats.drug_tables,
            "rows": parsed.stats.rows,
            "mnn_headings": parsed.stats.mnn_headings,
            "group_headings": parsed.stats.group_headings,
            "skipped_rows": parsed.stats.skipped_rows,
            "products": parsed.stats.products,
            "products_without_strength": parsed.stats.products_without_strength,
            "products_without_regimens": parsed.stats.products_without_regimens,
            "interactions": parsed.stats.interactions,
            "skipped_samples": parsed.stats.skipped_samples,
            "warnings": parsed.stats.warnings,
        },
        "database": verification,
    }

    if report_path:
        write_report(report_path, report)
    return report


def verify_database(path: Path | str) -> dict:
    with Database(path, merge=True, readonly=True) as database:
        return database.verify()


def _print_report(report: dict) -> None:
    parse = report["parse"]
    database = report["database"]
    counts = database["counts"]
    print("")
    print("MedExpert parser")
    print("----------------")
    print(f"Input:                 {report['input']}")
    print(f"Output:                {report['output']}")
    print("Build mode:            fresh database from DOCX")
    print(f"Elapsed:               {report['elapsed_seconds']} s")
    print("")
    print(f"Tables total:          {parse['tables_total']}")
    print(f"Drug tables:           {parse['drug_tables']}")
    print(f"Rows seen:             {parse['rows']}")
    print(f"MNN headings:          {parse['mnn_headings']}")
    print(f"Group headings:        {parse['group_headings']}")
    print(f"Products parsed:       {parse['products']}")
    print(f"Skipped rows:          {parse['skipped_rows']}")
    print("")
    print(f"Trade names in DB:     {counts['trade_name']}")
    print(f"Substances in DB:      {counts['active_substance']}")
    print(f"Dosage forms in DB:    {counts['dosage_form']}")
    print(f"Pharmacologic groups:  {counts['pharmacologic_group']}")
    print(f"Products in DB:        {counts['drug_product']}")
    print(f"Substance links:       {counts['product_active_substance']}")
    print(f"Interactions in DB:    {counts['drug_interaction']}")
    print(
        "Inserted / updated:    "
        f"{database.get('inserted_products', 0)} / {database.get('updated_products', 0)}"
    )
    if database.get("kept_curated_products"):
        print(
            "Curated rows kept:     "
            f"{database['kept_curated_products']} (existing regimens preserved)"
        )
    print(f"user_version:          {database['user_version']}")
    print(f"integrity_check:       {database['integrity']}")
    print(
        "Products w/o regimens: "
        f"{database['products_without_regimens']} "
        "(row is still searchable, details show a placeholder)"
    )
    print("")
    print("Top trade names:")
    for row in database["top_trade_names"]:
        print(f"  {row['products']:>4}  {row['name']}")
    if parse["skipped_samples"]:
        print("")
        print("First skipped rows (for diagnostics):")
        for sample in parse["skipped_samples"][:10]:
            print(f"  [{sample['reason']}] {sample['text']}")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the bundled MedExpert SQLite database from the DOCX reference book."
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="source .docx file (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="output SQLite file (default: %(default)s)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="only verify an existing database; do not parse the DOCX",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="optional path for a JSON report",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="do not print the human-readable summary",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    output = Path(args.output)

    try:
        if args.verify:
            if not output.exists():
                print(f"Database not found: {output}", file=sys.stderr)
                return 1
            verification = verify_database(output)
            counts = verification["counts"]
            print(
                f"OK: {output} (user_version={verification['user_version']}, "
                f"integrity={verification['integrity']}, "
                f"{counts['drug_product']} products, "
                f"{counts['trade_name']} trade names, "
                f"{counts['active_substance']} substances)"
            )
            if args.report:
                write_report(args.report, {"database": verification})
            return 0

        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Input document not found: {input_path}", file=sys.stderr)
            return 1

        report = build_database(
            input_path=input_path,
            output_path=output,
            report_path=args.report,
        )
        if not args.quiet:
            _print_report(report)
        return 0
    except VerificationError as error:
        print(f"Verification failed: {error}", file=sys.stderr)
        return 1
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
