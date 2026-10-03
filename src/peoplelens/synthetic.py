"""Sentetik (sahte ama gerçekçi) şirket veri üreteci."""

import math

import numpy as np
import pandas as pd

from peoplelens.schema import validate_employees

# departman: (çalışan ağırlığı, aylık ayrılma oranı, ortalama maaş, rol)
DEPARTMENTS = {
    "Sales": (0.25, 0.022, 45000, "Sales Representative"),
    "Customer Support": (0.20, 0.030, 32000, "Support Agent"),
    "IT": (0.15, 0.015, 65000, "Software Engineer"),
    "Finance": (0.10, 0.010, 55000, "Accountant"),
    "HR": (0.05, 0.010, 48000, "HR Specialist"),
    "Operations": (0.20, 0.018, 38000, "Operations Specialist"),
    "Marketing": (0.05, 0.020, 50000, "Marketing Specialist"),
}
LEVELS = [("Junior", 0.8), ("Specialist", 1.0), ("Senior", 1.4)]
WEIBULL_SHAPE = 0.8  # 1'den küçük: yeni çalışanlar daha erken ayrılır

COLUMNS = [
    "employee_id", "hire_date", "termination_date", "termination_type",
    "department", "job_title", "manager_id", "fte", "monthly_salary",
]


def generate_company(
    n_employees: int = 1500,
    years: int = 5,
    end_date: str = "2026-09-30",
    seed: int = 42,
) -> pd.DataFrame:
    """Şemaya uygun sahte bir şirket çalışan tablosu üretir.

    Aynı seed her zaman aynı veriyi verir. Pencereden önce ayrılanlar
    elendiği için dönen satır sayısı n_employees'ten biraz azdır.
    """
    rng = np.random.default_rng(seed)
    end = pd.Timestamp(end_date)
    start = end - pd.DateOffset(years=years)

    names = list(DEPARTMENTS)
    weights = np.array([DEPARTMENTS[d][0] for d in names])
    dept = rng.choice(names, size=n_employees, p=weights / weights.sum())

    # İşe girişler: pencereden 3 yıl öncesinden bitişe kadar
    earliest = start - pd.DateOffset(years=3)
    span_days = (end - earliest).days - 1
    hire = earliest + pd.to_timedelta(rng.integers(0, span_days, n_employees), unit="D")

    # Ayrılma: departmana göre değişen, erken dönemde yüksek risk
    hazard = np.array([DEPARTMENTS[d][1] for d in dept])
    scale_months = (1 / hazard) / math.gamma(1 + 1 / WEIBULL_SHAPE)
    tenure_months = scale_months * rng.weibull(WEIBULL_SHAPE, n_employees)
    term = (hire + pd.to_timedelta(tenure_months * 30.44, unit="D")).normalize()

    df = pd.DataFrame(
        {"department": dept, "hire_date": hire, "termination_date": term}
    )
    df.loc[df["termination_date"] > end, "termination_date"] = pd.NaT  # hâlâ çalışıyor
    df = df[~(df["termination_date"] < start)]  # pencereden önce ayrılanlar
    df = df.sort_values("hire_date").reset_index(drop=True)
    n = len(df)

    df["employee_id"] = [f"E{i + 1:05d}" for i in range(n)]

    # Ayrılma tipi: %70 gönüllü, %30 işveren kaynaklı
    ttype = pd.Series(
        np.where(rng.random(n) < 0.7, "voluntary", "involuntary"), dtype=object
    )
    ttype[df["termination_date"].isna()] = None
    df["termination_type"] = ttype

    # Kıdeme göre seviye, seviyeye göre maaş
    ref_date = df["termination_date"].fillna(end)
    tenure_years = (ref_date - df["hire_date"]).dt.days / 365.25
    level_idx = np.where(tenure_years < 1.5, 0, np.where(tenure_years < 4, 1, 2))
    roles = [DEPARTMENTS[d][3] for d in df["department"]]
    df["job_title"] = [f"{LEVELS[i][0]} {r}" for i, r in zip(level_idx, roles)]
    base = np.array([DEPARTMENTS[d][2] for d in df["department"]])
    mult = np.array([LEVELS[i][1] for i in level_idx])
    df["monthly_salary"] = (base * mult * rng.lognormal(0, 0.12, n)).round(-2)

    df["fte"] = rng.choice([1.0, 0.8, 0.5], size=n, p=[0.9, 0.06, 0.04])

    # Yöneticiler: her departmanın en eski %8'i
    manager_id = pd.Series([None] * n, dtype=object)
    for d in df["department"].unique():
        idx = df.index[df["department"] == d]
        n_mgr = max(1, int(len(idx) * 0.08))
        mgr_ids = df.loc[idx[:n_mgr], "employee_id"].to_numpy()
        manager_id.loc[idx[n_mgr:]] = rng.choice(mgr_ids, size=len(idx) - n_mgr)
    df["manager_id"] = manager_id

    df["hire_date"] = df["hire_date"].astype("datetime64[ns]")
    df["termination_date"] = df["termination_date"].astype("datetime64[ns]")
    return validate_employees(df[COLUMNS])

def make_dirty(
    df: pd.DataFrame, seed: int = 0, end_date: str = "2026-09-30"
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Temiz tabloya bilerek hata ekler (veri kalitesi motorunu test etmek için).

    Döndürür: (kirli_tablo, {kontrol_adı: eklenen_hata_sayısı}).
    Hatalar farklı satırlara eklenir, böylece sayılar birebir kontrol edilebilir.
    """
    rng = np.random.default_rng(seed)
    d = df.copy().reset_index(drop=True)
    free = pd.Series(True, index=d.index)
    terminated = d["termination_date"].notna()

    def take(k: int, cond: pd.Series | None = None) -> pd.Index:
        pool = d.index[free & (cond if cond is not None else True)]
        chosen = pd.Index(rng.choice(pool, size=k, replace=False))
        free.loc[chosen] = False
        return chosen

    injected: dict[str, int] = {}

    idx = take(10)
    d.loc[idx, "department"] = None
    injected["missing_department"] = len(idx)

    idx = take(15, d["department"].notna())
    d.loc[idx, "department"] = d.loc[idx, "department"].str.lower()
    injected["department_spelling_variants"] = len(idx)

    idx = take(5)
    d.loc[idx, "monthly_salary"] = -d.loc[idx, "monthly_salary"]
    injected["salary_non_positive"] = len(idx)

    idx = take(4)
    d.loc[idx, "monthly_salary"] = d.loc[idx, "monthly_salary"] * 12
    injected["salary_outlier"] = len(idx)

    idx = take(6)
    d.loc[idx, "fte"] = 1.5
    injected["fte_out_of_range"] = len(idx)

    idx = take(8, terminated)
    d.loc[idx, "termination_date"] = d.loc[idx, "hire_date"] - pd.Timedelta(days=30)
    injected["termination_before_hire"] = len(idx)

    idx = take(7, terminated)
    d.loc[idx, "termination_type"] = None
    injected["terminated_without_type"] = len(idx)

    idx = take(5, ~terminated)
    d.loc[idx, "termination_type"] = "voluntary"
    injected["type_without_termination_date"] = len(idx)

    idx = take(6)
    d.loc[idx, "manager_id"] = "E99999"
    injected["manager_not_found"] = len(idx)

    idx = take(3)
    d.loc[idx, "manager_id"] = d.loc[idx, "employee_id"]
    injected["self_manager"] = len(idx)

    idx = take(4, ~terminated)
    d.loc[idx, "hire_date"] = pd.Timestamp(end_date) + pd.Timedelta(days=60)
    injected["future_hire_date"] = len(idx)

    # Çift kayıt: temiz tablodan 10 satırın birebir kopyası sona eklenir
    copies = df.sample(n=10, random_state=seed)
    d = pd.concat([d, copies], ignore_index=True)
    injected["duplicate_employee_id"] = len(copies)

    return d, injected