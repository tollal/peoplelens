"""Türkiye modülü: kıdem ve ihbar tazminatı hesapları.

ÖNEMLİ: Bu modül bir hukuki veya aktüeryal danışmanlık değildir. Yasal tutarları
(tavan gibi) resmi kaynaktan doğrulayın; muhasebe karşılığı (TMS 19) için aktüeryal
hesap gerekir. Buradaki yükümlülük, "herkes bugün çıkarılsa" senaryosunun üst sınırıdır.
"""

import pandas as pd
from dateutil.relativedelta import relativedelta

from peoplelens.metrics import _active_mask

STAMP_TAX_RATE = 0.00759  # damga vergisi: binde 7,59

# Kıdem tazminatı tavanı (TL, brüt, hizmet yılı başına). Hazine ve Maliye Bakanlığı
# genelgeleri / Çalışma Genel Müdürlüğü. Ocak ve Temmuz'da değişir: yeni dönemi buraya ekleyin.
SEVERANCE_CEILING = [
    (pd.Timestamp("2025-07-01"), pd.Timestamp("2025-12-31"), 53_919.68),
    (pd.Timestamp("2026-01-01"), pd.Timestamp("2026-06-30"), 64_948.77),
    (pd.Timestamp("2026-07-01"), pd.Timestamp("2026-12-31"), 73_729.87),
]


def severance_ceiling(on_date) -> float:
    """Verilen fesih/hesap tarihinde geçerli kıdem tazminatı tavanı."""
    d = pd.Timestamp(on_date)
    for start, end, amount in SEVERANCE_CEILING:
        if start <= d <= end:
            return amount
    raise ValueError(
        f"{d.date()} için tavan tablosunda kayıt yok. SEVERANCE_CEILING listesine "
        "o dönemi ekleyin ya da ceiling parametresini elle verin."
    )


def service_years(hire_date, end_date) -> float:
    """Hizmet süresi (yıl): tam yıllar + kalan aylar/12 + kalan günler/365."""
    delta = relativedelta(pd.Timestamp(end_date), pd.Timestamp(hire_date))
    return max(0.0, delta.years + delta.months / 12 + delta.days / 365)


def severance_pay(monthly_gross: float, hire_date, end_date, ceiling: float | None = None) -> dict:
    """Brüt kıdem tazminatı = min(aylık brüt, tavan) x hizmet yılı. En az 1 yıl hizmet gerekir.

    Aylık brüt ücret olarak 'giydirilmiş' (yan haklar dahil) ücret verilmesi önerilir.
    Net = brüt - damga vergisi (gelir vergisi ve SGK kesilmez).
    """
    years = service_years(hire_date, end_date)
    if years < 1 or pd.isna(monthly_gross):
        empty = 0.0 if years < 1 else float("nan")
        return {"service_years": years, "eligible": years >= 1, "gross": empty, "stamp_tax": empty, "net": empty}
    cap = ceiling if ceiling is not None else severance_ceiling(end_date)
    gross = min(monthly_gross, cap) * years
    tax = gross * STAMP_TAX_RATE
    return {"service_years": years, "eligible": True, "gross": gross, "stamp_tax": tax, "net": gross - tax}


def notice_weeks(years: float) -> int:
    """İhbar süresi (4857 sayılı İş Kanunu md. 17): 6 aya kadar 2, 1,5 yıla kadar 4, 3 yıla kadar 6, sonrası 8 hafta."""
    if years < 0.5:
        return 2
    if years < 1.5:
        return 4
    if years < 3:
        return 6
    return 8


def notice_pay(monthly_gross: float, years: float) -> float:
    """Brüt ihbar tazminatı = ihbar haftası x 7 gün x günlük brüt ücret (aylık / 30)."""
    return notice_weeks(years) * 7 * (monthly_gross / 30)


def severance_liability(df: pd.DataFrame, as_of, ceiling: float | None = None, payout_probability: float = 1.0) -> pd.DataFrame:
    """Aktif çalışanlar bugün çıkarılsa ödenecek brüt kıdem tazminatı (çalışan bazında).

    payout_probability: 1.0 = üst sınır. Geçmişte ayrılanların kıdem ödemesi doğuran payı gibi
    bir oranla çarparak beklenen tutara yaklaşabilirsiniz (aktüeryal hesabın yerini tutmaz).
    """
    d = pd.Timestamp(as_of)
    cap = ceiling if ceiling is not None else severance_ceiling(d)
    act = df[_active_mask(df, d)].copy()
    act["service_years"] = [service_years(h, d) for h in act["hire_date"]]
    act["eligible"] = act["service_years"] >= 1
    act["ceiling_binding"] = act["monthly_salary"] > cap
    base = act["monthly_salary"].clip(upper=cap)
    act["gross_liability"] = (base * act["service_years"]).where(act["eligible"], 0.0) * payout_probability
    cols = ["employee_id", "department", "hire_date", "monthly_salary", "service_years",
            "eligible", "ceiling_binding", "gross_liability"]
    return act[cols].reset_index(drop=True)


def liability_summary(liability: pd.DataFrame, by: str = "department") -> pd.DataFrame:
    """Yükümlülüğü bir kırılıma göre özetler."""
    out = liability.groupby(by).agg(
        headcount=("employee_id", "size"),
        eligible=("eligible", "sum"),
        ceiling_binding=("ceiling_binding", "sum"),
        gross_liability=("gross_liability", "sum"),
    )
    return out.sort_values("gross_liability", ascending=False).reset_index()


def severance_cost(df: pd.DataFrame, start, end, eligible_types=("involuntary",)) -> pd.DataFrame:
    """[start, end] arasında ayrılanlar için, fesih tarihindeki tavanla hesaplanan brüt kıdem tazminatı.

    Varsayılan: yalnızca işveren kaynaklı (involuntary) çıkışlar. Emeklilik gibi istifa sayılsa
    da kıdem doğuran durumlar için eligible_types'ı genişletin.
    """
    mask = df["termination_date"].between(pd.Timestamp(start), pd.Timestamp(end))
    mask &= df["termination_type"].isin(list(eligible_types))
    rows = []
    for _, r in df[mask].iterrows():
        p = severance_pay(r["monthly_salary"], r["hire_date"], r["termination_date"])
        rows.append({"employee_id": r["employee_id"], "department": r["department"],
                     "termination_date": r["termination_date"], **p})
    cols = ["employee_id", "department", "termination_date", "service_years", "eligible", "gross", "stamp_tax", "net"]
    return pd.DataFrame(rows, columns=cols)