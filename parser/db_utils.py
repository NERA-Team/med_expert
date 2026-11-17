"""SQLite helpers for the MedExpert DOCX -> database ETL.

The schema mirrors ``composeApp/src/commonMain/sqldelight/com/medexpert/db/Drug.sq``
exactly.  The generated file is copied from Compose resources into the app
sandbox on first launch, therefore it must contain ``PRAGMA user_version = 1``
and must not depend on journal/WAL sidecar files.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from parser.normalization import Regimen, decode_regimens, regimens_to_json

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE trade_name (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    name_latin TEXT,
    is_original INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dosage_form (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    route TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE active_substance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL DEFAULT 'active',
    name_ru TEXT NOT NULL UNIQUE,
    name_latin TEXT,
    name_en TEXT,
    description TEXT,
    atc_code TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pharmacologic_group (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER,
    name_ru TEXT NOT NULL,
    name_en TEXT,
    level INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(parent_id) REFERENCES pharmacologic_group(id),
    UNIQUE(parent_id, name_ru)
);

CREATE TABLE drug_product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_name_id INTEGER NOT NULL,
    dosage_form_id INTEGER,
    strength_value REAL,
    strength_unit TEXT,
    package_size REAL,
    pack_unit TEXT,
    age_min_months INTEGER,
    age_max_months INTEGER,
    notes TEXT,
    dosing_regimen TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(trade_name_id) REFERENCES trade_name(id),
    FOREIGN KEY(dosage_form_id) REFERENCES dosage_form(id),
    UNIQUE(trade_name_id, dosage_form_id, strength_value, strength_unit)
);

CREATE TABLE product_group (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_product_id INTEGER NOT NULL,
    pharmacologic_group_id INTEGER NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(drug_product_id) REFERENCES drug_product(id) ON DELETE CASCADE,
    FOREIGN KEY(pharmacologic_group_id) REFERENCES pharmacologic_group(id),
    UNIQUE(drug_product_id, pharmacologic_group_id)
);

CREATE TABLE product_active_substance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_product_id INTEGER NOT NULL,
    active_substance_id INTEGER NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,
    component_dose_value REAL,
    component_dose_unit TEXT,
    FOREIGN KEY(drug_product_id) REFERENCES drug_product(id) ON DELETE CASCADE,
    FOREIGN KEY(active_substance_id) REFERENCES active_substance(id),
    UNIQUE(drug_product_id, active_substance_id)
);

CREATE TABLE drug_interaction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    substance_a_id INTEGER,
    substance_b_id INTEGER,
    group_a_id INTEGER,
    group_b_id INTEGER,
    interaction_level TEXT,
    clinical_consequence TEXT,
    management_recommendation TEXT,
    substance_a_name TEXT NOT NULL,
    substance_b_name TEXT NOT NULL,
    category_name TEXT,
    interaction_text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(substance_a_id) REFERENCES active_substance(id),
    FOREIGN KEY(substance_b_id) REFERENCES active_substance(id),
    FOREIGN KEY(group_a_id) REFERENCES pharmacologic_group(id),
    FOREIGN KEY(group_b_id) REFERENCES pharmacologic_group(id),
    UNIQUE(substance_a_name, substance_b_name, interaction_text)
);

CREATE INDEX idx_drug_product_trade_name ON drug_product(trade_name_id);
CREATE INDEX idx_drug_product_dosage_form ON drug_product(dosage_form_id);
CREATE INDEX idx_product_group_group ON product_group(pharmacologic_group_id);
CREATE INDEX idx_product_active_substance_substance ON product_active_substance(active_substance_id);
CREATE INDEX idx_drug_interaction_substance_a ON drug_interaction(substance_a_id);
CREATE INDEX idx_drug_interaction_substance_b ON drug_interaction(substance_b_id);
"""

REQUIRED_TABLES = {
    "trade_name",
    "dosage_form",
    "active_substance",
    "pharmacologic_group",
    "drug_product",
    "product_group",
    "product_active_substance",
    "drug_interaction",
}


class VerificationError(RuntimeError):
    """Raised when the generated database does not satisfy the app contract."""


def _normalize_optional(value: Optional[str]) -> str:
    return (value or "").strip()


def _infer_route(dosage_form: str) -> Optional[str]:
    value = dosage_form.casefold()
    if any(token in value for token in ("инъекц", "инфуз", "ампул", "в/м", "в/в")):
        return "парентеральный"
    if any(token in value for token in ("суппозитор", "ректальн", "клизм")):
        return "ректальный"
    if any(token in value for token in ("глазн", "ушн", "назальн", "ингаляц", "спрей")):
        return "местный"
    if any(token in value for token in ("таблет", "капсул", "порошок", "суспенз", "сироп", "раствор", "капли")):
        return "пероральный"
    return None


class Database:
    """Small SQLite repository with idempotent upserts."""

    def __init__(
        self, path: Path | str, merge: bool = False, readonly: bool = False
    ) -> None:
        self.path = Path(path)
        self.merge = merge
        self.readonly = readonly
        self.inserted_products = 0
        self.updated_products = 0
        self.kept_curated_products = 0

        if not merge and not readonly:
            for suffix in ("", "-wal", "-shm", "-journal"):
                candidate = Path(str(self.path) + suffix)
                if candidate.exists():
                    candidate.unlink()

        if readonly:
            if not self.path.exists():
                raise FileNotFoundError(f"Database not found: {self.path}")
            self.connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.pre_existing_product_ids = {
                int(row[0])
                for row in self.connection.execute("SELECT id FROM drug_product")
            }
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = DELETE")

        if merge and self._has_schema():
            existing_tables = {
                str(row[0])
                for row in self.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if not REQUIRED_TABLES.issubset(existing_tables):
                raise VerificationError(
                    "Cannot merge the old database schema; rebuild without merge mode."
                )
            self._create_missing_indexes()
        else:
            self.connection.executescript(SCHEMA)

        self.connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self.connection.commit()
        self.pre_existing_product_ids = {
            int(row[0]) for row in self.connection.execute("SELECT id FROM drug_product")
        }

    # -- schema ---------------------------------------------------------
    def _has_schema(self) -> bool:
        row = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='drug_product'"
        ).fetchone()
        return row is not None

    def _create_missing_indexes(self) -> None:
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_drug_product_trade_name ON drug_product(trade_name_id)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_drug_product_dosage_form ON drug_product(dosage_form_id)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_product_group_group ON product_group(pharmacologic_group_id)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_product_active_substance_substance "
            "ON product_active_substance(active_substance_id)"
        )

    # -- reference rows -------------------------------------------------
    def get_or_create_group(
        self, name: str, parent_id: Optional[int] = None, level: int = 1
    ) -> int:
        name = " ".join(name.split()).strip()
        if not name:
            raise ValueError("group name must not be empty")
        if len(name) > 200:
            name = name[:197].rstrip(" ,;.-") + "…"

        row = self.connection.execute(
            "SELECT id FROM pharmacologic_group WHERE name_ru = ? AND parent_id IS ?",
            (name, parent_id),
        ).fetchone()
        if row is not None:
            return int(row["id"])

        cursor = self.connection.execute(
            "INSERT INTO pharmacologic_group (parent_id, name_ru, level) VALUES (?, ?, ?)",
            (parent_id, name, level),
        )
        return int(cursor.lastrowid)

    def ensure_group_path(self, path: Sequence[str]) -> Optional[int]:
        parent: Optional[int] = None
        for level, name in enumerate(path, start=1):
            if not name:
                continue
            parent = self.get_or_create_group(name, parent, level)
        return parent

    def ensure_group_path_ids(self, path: Sequence[str]) -> List[int]:
        parent: Optional[int] = None
        group_ids: List[int] = []
        for level, name in enumerate(path, start=1):
            if not name:
                continue
            parent = self.get_or_create_group(name, parent, level)
            group_ids.append(parent)
        return group_ids

    def find_group_id(self, name: str) -> Optional[int]:
        normalized = " ".join(name.casefold().split())
        for row in self.connection.execute(
            "SELECT id, name_ru FROM pharmacologic_group"
        ):
            if " ".join(str(row["name_ru"]).casefold().split()) == normalized:
                return int(row["id"])
        return None

    def get_or_create_substance(
        self, name_ru: str, name_latin: Optional[str] = None
    ) -> Optional[int]:
        name_ru = " ".join((name_ru or "").split()).strip(" ,;.:-")
        if not name_ru:
            return None
        if len(name_ru) > 200:
            name_ru = name_ru[:197].rstrip(" ,;.:-") + "…"
        name_latin = (name_latin or "").strip(" ,;.:-") or None

        row = self.connection.execute(
            "SELECT id, name_latin FROM active_substance WHERE name_ru = ?", (name_ru,)
        ).fetchone()
        if row is not None:
            if name_latin and not row["name_latin"]:
                self.connection.execute(
                    "UPDATE active_substance SET name_latin = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (name_latin, row["id"]),
                )
            return int(row["id"])

        cursor = self.connection.execute(
            "INSERT INTO active_substance (name_ru, name_latin, atc_code) VALUES (?, ?, NULL)",
            (name_ru, name_latin),
        )
        return int(cursor.lastrowid)

    def find_substance_id(self, name: str) -> Optional[int]:
        normalized = " ".join(name.casefold().split()).strip(" ,;.:-«»\"")
        for row in self.connection.execute("SELECT id, name_ru FROM active_substance"):
            if " ".join(str(row["name_ru"]).casefold().split()) == normalized:
                return int(row["id"])
        return None

    def get_or_create_dosage_form(self, name: Optional[str]) -> Optional[int]:
        normalized = " ".join((name or "").split()).strip(" ,;.")
        if not normalized:
            return None
        route = _infer_route(normalized)
        row = self.connection.execute(
            "SELECT id FROM dosage_form WHERE name = ?", (normalized,)
        ).fetchone()
        if row is not None:
            if route:
                self.connection.execute(
                    "UPDATE dosage_form SET route = COALESCE(route, ?), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (route, row["id"]),
                )
            return int(row["id"])
        cursor = self.connection.execute(
            "INSERT INTO dosage_form (name, route) VALUES (?, ?)",
            (normalized, route),
        )
        return int(cursor.lastrowid)

    def add_interaction(
        self,
        substance_a_name: str,
        substance_b_name: str,
        interaction_text: str,
        category_name: Optional[str] = None,
    ) -> None:
        substance_a_name = " ".join(substance_a_name.split()).strip()
        substance_b_name = " ".join(substance_b_name.split()).strip()
        interaction_text = " ".join(interaction_text.split()).strip()
        if not substance_a_name or not substance_b_name or not interaction_text:
            return
        self.connection.execute(
            """INSERT OR IGNORE INTO drug_interaction
                    (substance_a_id, substance_b_id, group_a_id, group_b_id,
                interaction_level, clinical_consequence, management_recommendation,
                substance_a_name, substance_b_name, category_name, interaction_text)
               VALUES (?, ?, ?, ?, NULL, ?, NULL, ?, ?, ?, ?)""",
            (
                self.find_substance_id(substance_a_name),
                self.find_substance_id(substance_b_name),
                self.find_group_id(substance_a_name),
                self.find_group_id(substance_b_name),
                interaction_text,
                substance_a_name,
                substance_b_name,
                category_name,
                interaction_text,
            ),
        )

    def get_or_create_trade_name(
        self, name: str, name_latin: Optional[str] = None
    ) -> Optional[int]:
        name = " ".join((name or "").split()).strip(" ,;.:-«»\"")
        if not name:
            return None
        if len(name) > 200:
            name = name[:197].rstrip(" ,;.:-") + "…"
        name_latin = (name_latin or "").strip(" ,;.:-") or None

        row = self.connection.execute(
            "SELECT id, name_latin FROM trade_name WHERE name = ?", (name,)
        ).fetchone()
        if row is not None:
            if name_latin and not row["name_latin"]:
                self.connection.execute(
                    "UPDATE trade_name SET name_latin = ? WHERE id = ?",
                    (name_latin, row["id"]),
                )
            return int(row["id"])

        cursor = self.connection.execute(
            "INSERT INTO trade_name (name, name_latin, is_original) VALUES (?, ?, 0)",
            (name, name_latin),
        )
        return int(cursor.lastrowid)

    # -- products -------------------------------------------------------
    def _find_product(
        self,
        trade_name_id: int,
        dosage_form_id: Optional[int],
        strength_value: Optional[float],
        strength_unit: Optional[str],
    ) -> Optional[sqlite3.Row]:
        return self.connection.execute(
            """
                        SELECT id, dosage_form_id, dosing_regimen
            FROM drug_product
            WHERE trade_name_id = ?
                            AND IFNULL(dosage_form_id, -1) = ?
              AND IFNULL(strength_value, -1.0) = ?
              AND IFNULL(strength_unit, '') = ?
            LIMIT 1
            """,
            (
                trade_name_id,
                -1 if dosage_form_id is None else dosage_form_id,
                -1.0 if strength_value is None else float(strength_value),
                _normalize_optional(strength_unit),
            ),
        ).fetchone()

    def _link_substance(self, product_id: int, substance_id: Optional[int]) -> None:
        if substance_id is None:
            return
        self.connection.execute(
            "INSERT OR IGNORE INTO product_active_substance "
            "(drug_product_id, active_substance_id) VALUES (?, ?)",
            (product_id, substance_id),
        )

    def _merge_regimens(
        self,
        product_id: int,
        regimens: Sequence[Regimen],
        preserve_existing: bool,
    ) -> None:
        row = self.connection.execute(
            "SELECT dosing_regimen FROM drug_product WHERE id = ?", (product_id,)
        ).fetchone()
        raw = row["dosing_regimen"] if row is not None else None
        existing = decode_regimens(raw)

        if preserve_existing and existing:
            self.kept_curated_products += 1
            return
        if raw and not existing:
            # Malformed legacy payload: replace it instead of keeping garbage.
            existing = []

        seen = {str(item.get("regimen_text", "")).casefold() for item in existing}
        merged: List[dict] = list(existing)
        for regimen in regimens:
            payload = regimen.as_dict()
            key = payload["regimen_text"].casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(payload)

        self.connection.execute(
            "UPDATE drug_product SET dosing_regimen = ? WHERE id = ?",
            (regimens_to_json_payload(merged), product_id),
        )

    def add_regimens(
        self,
        product_ids: Iterable[int],
        regimens: Sequence[Regimen],
        preserve_existing: bool = False,
    ) -> None:
        for product_id in product_ids:
            self._merge_regimens(product_id, regimens, preserve_existing)

    def save_product(
        self,
        trade_name: str,
        trade_name_latin: Optional[str],
        substances: Sequence[Tuple[str, Optional[str]]],
        group_path: Sequence[str],
        dosage_form: Optional[str],
        strength_value: Optional[float],
        strength_unit: Optional[str],
        regimens: Sequence[Regimen],
        interactions: Optional[Sequence[dict]] = None,
    ) -> Optional[int]:
        trade_id = self.get_or_create_trade_name(trade_name, trade_name_latin)
        if trade_id is None:
            return None

        group_ids = self.ensure_group_path_ids(group_path)
        group_id = group_ids[-1] if group_ids else None
        dosage_form_id = self.get_or_create_dosage_form(dosage_form)
        existing = self._find_product(trade_id, dosage_form_id, strength_value, strength_unit)
        preserve_existing = bool(
            existing is not None and int(existing["id"]) in self.pre_existing_product_ids
        )

        if existing is None:
            regimen_ages = [
                age
                for regimen in regimens
                for age in (regimen.age_min_months,)
                if age is not None
            ]
            age_min = min(regimen_ages) if regimen_ages else None
            age_max = (
                None
                if any(regimen.age_max_months is None for regimen in regimens)
                else max(
                    (regimen.age_max_months for regimen in regimens if regimen.age_max_months is not None),
                    default=None,
                )
            )
            cursor = self.connection.execute(
                """
                INSERT INTO drug_product
                    (trade_name_id, dosage_form_id, strength_value, strength_unit,
                     age_min_months, age_max_months, dosing_regimen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade_id,
                    dosage_form_id,
                    None if strength_value is None else float(strength_value),
                    _normalize_optional(strength_unit) or None,
                    age_min,
                    age_max,
                    regimens_to_json(regimens),
                ),
            )
            product_id = int(cursor.lastrowid)
            self.inserted_products += 1
        else:
            product_id = int(existing["id"])
            self._merge_regimens(product_id, regimens, preserve_existing)
            self.updated_products += 1

        for related_group_id in group_ids:
            self.connection.execute(
                """INSERT OR IGNORE INTO product_group
                   (drug_product_id, pharmacologic_group_id, is_primary)
                   VALUES (?, ?, ?)""",
                (product_id, related_group_id, int(related_group_id == group_id)),
            )

        for index, (name_ru, name_latin) in enumerate(substances):
            substance_id = self.get_or_create_substance(name_ru, name_latin)
            if substance_id is not None:
                self.connection.execute(
                    """INSERT OR IGNORE INTO product_active_substance
                       (drug_product_id, active_substance_id, is_primary)
                       VALUES (?, ?, ?)""",
                    (product_id, substance_id, int(index == 0)),
                )
        for interaction in interactions or ():
            self.add_interaction(**interaction)
        return product_id

    # -- output ---------------------------------------------------------
    def counts(self) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for table in (
            "trade_name",
            "dosage_form",
            "active_substance",
            "pharmacologic_group",
            "drug_product",
            "product_group",
            "product_active_substance",
            "drug_interaction",
        ):
            result[table] = int(
                self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            )
        return result

    def verify(self) -> dict:
        counts = self.counts()
        problems: List[str] = []

        integrity = [
            str(row[0]) for row in self.connection.execute("PRAGMA integrity_check")
        ]
        if integrity != ["ok"]:
            problems.append(f"integrity_check failed: {integrity}")

        version = int(self.connection.execute("PRAGMA user_version").fetchone()[0])
        if version != SCHEMA_VERSION:
            problems.append(f"user_version is {version}, expected {SCHEMA_VERSION}")

        tables = {
            str(row[0])
            for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        missing_tables = sorted(REQUIRED_TABLES - tables)
        if missing_tables:
            problems.append(f"missing tables: {missing_tables}")

        orphan_products = int(
            self.connection.execute(
                """
                SELECT COUNT(*) FROM drug_product dp
                LEFT JOIN trade_name tn ON tn.id = dp.trade_name_id
                WHERE tn.id IS NULL
                """
            ).fetchone()[0]
        )
        if orphan_products:
            problems.append(f"{orphan_products} products reference a missing trade name")

        orphan_substance_links = int(
            self.connection.execute(
                """
                SELECT COUNT(*) FROM product_active_substance pas
                LEFT JOIN drug_product dp ON dp.id = pas.drug_product_id
                LEFT JOIN active_substance ast ON ast.id = pas.active_substance_id
                WHERE dp.id IS NULL OR ast.id IS NULL
                """
            ).fetchone()[0]
        )
        if orphan_substance_links:
            problems.append(f"{orphan_substance_links} broken substance links")

        orphan_groups = int(
            self.connection.execute(
                """
                SELECT COUNT(*) FROM pharmacologic_group child
                LEFT JOIN pharmacologic_group parent ON parent.id = child.parent_id
                WHERE child.parent_id IS NOT NULL AND parent.id IS NULL
                """
            ).fetchone()[0]
        )
        if orphan_groups:
            problems.append(f"{orphan_groups} groups reference a missing parent")

        duplicate_products = int(
            self.connection.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT 1 FROM drug_product
                    GROUP BY trade_name_id, IFNULL(dosage_form_id, -1),
                             IFNULL(strength_value, -1.0), IFNULL(strength_unit, '')
                    HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0]
        )
        if duplicate_products:
            problems.append(f"{duplicate_products} duplicate product keys")

        malformed: List[int] = []
        without_regimens = 0
        for row in self.connection.execute(
            "SELECT id, dosing_regimen FROM drug_product ORDER BY id"
        ):
            raw = row["dosing_regimen"]
            if not raw:
                without_regimens += 1
                continue
            try:
                payload = json.loads(raw)
            except (TypeError, ValueError):
                malformed.append(int(row["id"]))
                continue
            if not isinstance(payload, list):
                malformed.append(int(row["id"]))
                continue
            for item in payload:
                if not isinstance(item, dict) or not isinstance(
                    item.get("regimen_text"), str
                ):
                    malformed.append(int(row["id"]))
                    break
                for key in ("age_min_months", "age_max_months"):
                    value = item.get(key)
                    if value is not None and not isinstance(value, int):
                        malformed.append(int(row["id"]))
                        break
        if malformed:
            problems.append(f"{len(malformed)} malformed dosing_regimen rows: {malformed[:10]}")

        if counts["drug_product"] == 0:
            problems.append("drug_product is empty")

        if problems:
            raise VerificationError("; ".join(problems))

        top_trade_names = [
            {"name": str(row["name"]), "products": int(row["products"])}
            for row in self.connection.execute(
                """
                SELECT tn.name, COUNT(dp.id) AS products
                FROM trade_name tn
                JOIN drug_product dp ON dp.trade_name_id = tn.id
                GROUP BY tn.id
                ORDER BY products DESC, tn.name
                LIMIT 10
                """
            )
        ]

        return {
            "path": str(self.path),
            "user_version": version,
            "integrity": integrity[0] if integrity else "unknown",
            "counts": counts,
            "products_without_regimens": without_regimens,
            "top_trade_names": top_trade_names,
        }

    def vacuum(self) -> None:
        self.connection.commit()
        self.connection.execute("VACUUM")
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self.close()


def regimens_to_json_payload(items: Sequence[dict]) -> str:
    """Encode an already-merged ``dosing_regimen`` JSON list."""

    return json.dumps(list(items), ensure_ascii=False, separators=(",", ":"))


def write_report(path: Path | str, payload: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
