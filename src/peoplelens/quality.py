"""Veri kalitesi motoru: çalışan tablosundaki hataları bulur ve raporlar.

Bu motor, şemadan ÖNCE çalışır. Şema bozuk veriyi reddeder; kalite motoru ise
neyin, kaç satırda ve hangi çalışanlarda bozuk olduğunu söyler.
"""

import pandas as pd

ERROR = "error"      # analizi bozar, düzeltilmeden güvenilmez
WARNING = "warning"  # şüpheli, kontrol edilmeli


def _checks(df: pd.DataFrame, as_of: pd.Timestamp) -> list[tuple[str, str, str, pd.Series]]:
    """(ad, önem, açıklama, hatalı_satır_maskesi) listesi döndürür."""
    term_both = df["termination_date"].notna() & df["hire_date"].notna()

    # Departman yazım varyantları: "sales", "SALES " gibi. En sık yazım doğru kabul edilir.
    norm = df["department"].str.strip().str.casefold()
    canon = df.groupby(norm)["department"].transform(lambda s: s.mode().iat[0])
    dept_variant = df["department"].notna() & (df["department"] != canon)

    # Maaş aykırı değeri: kendi departmanının medyanının 5 katından büyük
    dept_median = df.groupby(norm)["monthly_salary"].transform("median")
    salary_outlier = df["monthly_salary"].notna() & (df["monthly_salary"] > 5 * dept_median)

    return [
        ("duplicate_employee_id", ERROR, "Aynı çalışan numarası birden fazla satırda",
         df["employee_id"].notna() & df["employee_id"].duplicated(keep="first")),
        ("missing_employee_id", ERROR, "Çalışan numarası boş", df["employee_id"].isna()),
        ("missing_hire_date", ERROR, "İşe giriş tarihi boş", df["hire_date"].isna()),
        ("missing_department", ERROR, "Departman boş", df["department"].isna()),
        ("termination_before_hire", ERROR, "Çıkış tarihi işe girişten önce",
         term_both & (df["termination_date"] < df["hire_date"])),
        ("self_manager", ERROR, "Çalışan kendi yöneticisi görünüyor",
         df["manager_id"].notna() & (df["manager_id"] == df["employee_id"])),
        ("salary_non_positive", ERROR, "Maaş sıfır veya negatif",
         df["monthly_salary"].notna() & (df["monthly_salary"] <= 0)),
        ("fte_out_of_range", ERROR, "FTE 0-1 aralığı dışında",
         df["fte"].notna() & ~df["fte"].between(0, 1)),
        ("terminated_without_type", WARNING, "Çıkış tarihi var, çıkış tipi yok",
         df["termination_date"].notna() & df["termination_type"].isna()),
        ("type_without_termination_date", WARNING, "Çıkış tipi var, çıkış tarihi yok",
         df["termination_date"].isna() & df["termination_type"].notna()),
        ("future_hire_date", WARNING, "İşe giriş tarihi gelecekte", df["hire_date"] > as_of),
        ("manager_not_found", WARNING, "Yönetici numarası tabloda yok",
         df["manager_id"].notna() & ~df["manager_id"].isin(df["employee_id"])),
        ("salary_outlier", WARNING, "Maaş, departman medyanının 5 katından yüksek", salary_outlier),
        ("department_spelling_variants", WARNING, "Departman adı farklı yazılmış", dept_variant),
    ]


def run_checks(df: pd.DataFrame, as_of=None) -> pd.DataFrame:
    """Tüm kontrolleri çalıştırır, her kontrol için bir satır döner."""
    as_of = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.today().normalize()
    rows = []
    for name, severity, description, mask in _checks(df, as_of):
        rows.append(
            {
                "check": name,
                "severity": severity,
                "description": description,
                "rows": int(mask.sum()),
                "pct": round(100 * mask.mean(), 2) if len(df) else 0.0,
                "examples": ", ".join(df.loc[mask, "employee_id"].astype(str).head(3)),
            }
        )
    return pd.DataFrame(rows)


def quality_score(df: pd.DataFrame, as_of=None) -> float:
    """Hiç 'error' içermeyen satırların oranı (0-1). 1.0 = tertemiz."""
    as_of = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.today().normalize()
    bad = pd.Series(False, index=df.index)
    for _, severity, _, mask in _checks(df, as_of):
        if severity == ERROR:
            bad |= mask
    return float(1 - bad.mean()) if len(df) else float("nan")