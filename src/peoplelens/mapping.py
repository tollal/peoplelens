"""Mapping motoru: bir şirketin ham verisini standart (canonical) şemaya çevirir.

Her şirket için bir YAML dosyası yazılır; kod değişmez.
"""

import re
from pathlib import Path

import pandas as pd
import yaml

CANONICAL = [
    "employee_id", "hire_date", "termination_date", "termination_type",
    "department", "job_title", "manager_id", "fte", "monthly_salary",
]
REQUIRED = ["employee_id", "hire_date", "department"]
DATE_COLS = ["hire_date", "termination_date"]
NUMBER_COLS = ["fte", "monthly_salary"]
ID_COLS = ["employee_id", "manager_id"]


def load_mapping(path) -> dict:
    """YAML mapping dosyasını okur."""
    with open(path, encoding="utf-8-sig") as f:
        return yaml.safe_load(f)


def read_raw(path) -> pd.DataFrame:
    """CSV veya Excel dosyasını, hiçbir şeyi çevirmeden (hepsi metin) okur."""
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(p, dtype=object)
    return pd.read_csv(p, sep=None, engine="python", encoding="utf-8-sig", dtype=object)


def _norm(name) -> str:
    return str(name).strip().casefold()


def _to_text(s: pd.Series, is_id: bool = False) -> pd.Series:
    def conv(v):
        if v is None or (not isinstance(v, str) and pd.isna(v)):
            return None
        t = str(v).strip()
        if is_id and re.fullmatch(r"\d+\.0", t):  # Excel'in 1001.0 yapması
            t = t[:-2]
        return t or None

    return s.map(conv)


def _to_date(s: pd.Series, fmt: str | None) -> tuple[pd.Series, int]:
    text = _to_text(s)
    filled = text.notna()
    parsed = pd.to_datetime(text, format=fmt, errors="coerce") if fmt else pd.Series(pd.NaT, index=s.index)
    todo = filled & parsed.isna()
    if todo.any():  # biçime uymayanlar için esnek ikinci deneme (ISO, Excel tarihi vb.)
        parsed = parsed.where(~todo, pd.to_datetime(text.where(todo), format="mixed", errors="coerce"))
    failed = int((filled & parsed.isna()).sum())
    return parsed.astype("datetime64[ns]"), failed


def _to_number(s: pd.Series, decimal: str, thousands: str) -> tuple[pd.Series, int]:
    def conv(v):
        if v is None or (not isinstance(v, str) and pd.isna(v)):
            return None
        if isinstance(v, (int, float)):
            return float(v)
        t = str(v).strip().replace(" ", "")
        if not t:
            return None
        if thousands:
            t = t.replace(thousands, "")
        if decimal != ".":
            t = t.replace(decimal, ".")
        try:
            return float(t)
        except ValueError:
            return float("nan")

    result = pd.to_numeric(s.map(conv), errors="coerce").astype(float)
    failed = int((_to_text(s).notna() & result.isna()).sum())
    return result, failed


def apply_mapping(raw: pd.DataFrame, mapping: dict) -> tuple[pd.DataFrame, list[str]]:
    """Ham tabloyu standart şemaya çevirir. (tablo, notlar) döndürür.

    Notlar, dönüşümde olan her şeyi söyler: eksik sütun, çevrilemeyen değer vb.
    """
    cols = mapping.get("columns", {})
    defaults = mapping.get("defaults", {}) or {}
    numbers = mapping.get("numbers", {}) or {}
    decimal, thousands = numbers.get("decimal", "."), numbers.get("thousands", "")
    lookup = {_norm(c): c for c in raw.columns}
    notes: list[str] = []

    for c in REQUIRED:
        if c not in cols or _norm(cols[c]) not in lookup:
            raise ValueError(
                f"Zorunlu alan '{c}' için sütun bulunamadı (aranan: {cols.get(c)!r}). "
                f"Dosyadaki sütunlar: {list(raw.columns)}"
            )

    out = pd.DataFrame(index=raw.index)
    for c in CANONICAL:
        if c in cols and _norm(cols[c]) in lookup:
            src = raw[lookup[_norm(cols[c])]]
        elif c in defaults:
            src = pd.Series([defaults[c]] * len(raw), index=raw.index, dtype=object)
            notes.append(f"{c}: sütun yok, varsayılan değer kullanıldı ({defaults[c]})")
        else:
            src = pd.Series([None] * len(raw), index=raw.index, dtype=object)
            notes.append(f"{c}: sütun yok, boş bırakıldı")

        if c in DATE_COLS:
            out[c], failed = _to_date(src, mapping.get("date_format"))
            if failed:
                notes.append(f"{c}: {failed} değer tarihe çevrilemedi, boş bırakıldı")
        elif c in NUMBER_COLS:
            out[c], failed = _to_number(src, decimal, thousands)
            if failed:
                notes.append(f"{c}: {failed} değer sayıya çevrilemedi, boş bırakıldı")
        else:
            out[c] = _to_text(src, is_id=c in ID_COLS)

    tmap = mapping.get("termination_type_map")
    if tmap:
        values = {_norm(v): k for k, vals in tmap.items() for v in vals}
        t = out["termination_type"]
        mapped = t.map(lambda v: values.get(_norm(v)) if isinstance(v, str) else None)
        unmapped = t.notna() & mapped.isna()
        if unmapped.any():
            examples = sorted(set(t[unmapped]))[:5]
            notes.append(f"termination_type: {int(unmapped.sum())} satır eşleşmedi, örnekler: {examples}")
        out["termination_type"] = mapped

    return out[CANONICAL], notes


def load_company(data_path, mapping_path) -> tuple[pd.DataFrame, list[str]]:
    """Dosya + mapping YAML -> standart tablo ve dönüşüm notları (tek adım)."""
    return apply_mapping(read_raw(data_path), load_mapping(mapping_path))