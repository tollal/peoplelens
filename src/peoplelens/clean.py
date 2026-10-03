"""Temel temizlik: kalite motorunun bulduğu 'error' düzeyindeki sorunları güvenle onarır.

Her adım bir not üretir, hiçbir şey sessizce değişmez. Emin olunamayan satırlar
(çıkış tarihi girişten önce olanlar) tahmin edilmez, tablodan çıkarılır.
"""

import pandas as pd


def basic_clean(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """(temiz_tablo, notlar) döndürür."""
    d = df.copy()
    notes: list[str] = []

    dup = d["employee_id"].notna() & d["employee_id"].duplicated(keep="first")
    if dup.any():
        d = d[~dup]
        notes.append(f"{int(dup.sum())} tekrar eden kayıt çıkarıldı (ilk kayıt tutuldu)")

    norm = d["department"].str.strip().str.casefold()
    canon = d.groupby(norm)["department"].transform(lambda s: s.mode().iat[0])
    changed = d["department"].notna() & (d["department"] != canon)
    if changed.any():
        d.loc[changed, "department"] = canon[changed]
        notes.append(f"{int(changed.sum())} departman adı en sık yazıma eşitlendi")

    missing = d["department"].isna()
    if missing.any():
        d.loc[missing, "department"] = "Unknown"
        notes.append(f"{int(missing.sum())} boş departman 'Unknown' yapıldı")

    bad = d["termination_date"].notna() & (d["termination_date"] < d["hire_date"])
    if bad.any():
        d = d[~bad]
        notes.append(f"{int(bad.sum())} satır çıkarıldı: çıkış tarihi işe girişten önce (düzeltmek için tahmin gerekir)")

    neg = d["monthly_salary"].notna() & (d["monthly_salary"] <= 0)
    if neg.any():
        d.loc[neg, "monthly_salary"] = float("nan")
        notes.append(f"{int(neg.sum())} sıfır/negatif maaş boş bırakıldı")

    bad_fte = d["fte"].notna() & ~d["fte"].between(0, 1)
    if bad_fte.any():
        d.loc[bad_fte, "fte"] = float("nan")
        notes.append(f"{int(bad_fte.sum())} geçersiz FTE boş bırakıldı")

    selfm = d["manager_id"].notna() & (d["manager_id"] == d["employee_id"])
    unknown = d["manager_id"].notna() & ~d["manager_id"].isin(d["employee_id"])
    fix = selfm | unknown
    if fix.any():
        d.loc[fix, "manager_id"] = None
        notes.append(f"{int(fix.sum())} geçersiz yönetici bilgisi (kendisi/bulunamayan) boş bırakıldı")

    return d.reset_index(drop=True), notes