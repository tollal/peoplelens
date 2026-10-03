"""Elde tutma (retention) analizi: Kaplan-Meier ile "çalışanlar ne kadar kalıyor?".

Yöntem sade ve şeffaftır: her çalışanın işe girişten ayrılışa (veya bugüne) kadar geçen
günü ve ayrılıp ayrılmadığı bilinir. Hâlâ çalışanlar "sansürlü" sayılır (henüz ayrılmadı).

ÖNEMLİ: Yalnızca analiz penceresinin başından sonra işe girenler (cohort) kullanılır.
Pencereden önce ayrılanlar tabloda yoksa eski çalışanları dahil etmek hayatta kalma
yanlılığı (survivorship bias) yaratır. Veriyi önce kalite motorundan geçirin.
"""

import pandas as pd


def kaplan_meier(durations, events) -> pd.DataFrame:
    """Kaplan-Meier hayatta kalma eğrisi. Sütunlar: day, at_risk, events, survival."""
    t = pd.DataFrame(
        {"t": pd.Series(durations).to_numpy(), "e": pd.Series(events).astype(int).to_numpy()}
    )
    g = t.groupby("t")["e"].agg(events="sum", leaving="size").reset_index()
    g["at_risk"] = len(t) - g["leaving"].cumsum().shift(fill_value=0)
    g["survival"] = (1 - g["events"] / g["at_risk"]).cumprod()
    return g.rename(columns={"t": "day"})[["day", "at_risk", "events", "survival"]]


def survival_at(curve: pd.DataFrame, day: int) -> float:
    """Eğrinin verilen günde elde tutma oranı (hiç ayrılma olmadıysa 1.0)."""
    if curve.empty:
        return float("nan")
    done = curve[curve["day"] <= day]
    return 1.0 if done.empty else float(done["survival"].iloc[-1])


def _cohort(df, as_of, cohort_start, event_type):
    d, c = pd.Timestamp(as_of), pd.Timestamp(cohort_start)
    x = df[(df["hire_date"] >= c) & (df["hire_date"] <= d)]
    ended = x["termination_date"].notna() & (x["termination_date"] <= d)
    end = x["termination_date"].where(ended, d)
    dur = (end - x["hire_date"]).dt.days
    ok = dur >= 0  # bozuk tarihli satırlar (çıkış < giriş) dışarıda kalır
    event = ended if event_type is None else ended & (x["termination_type"] == event_type)
    return x[ok], dur[ok], event[ok]


def retention_table(
    df: pd.DataFrame,
    as_of,
    cohort_start,
    by: str = "department",
    months=(6, 12, 24),
    event_type: str | None = None,
    min_at_risk: int = 20,
) -> pd.DataFrame:
    """Gruplara göre elde tutma oranları (örn. 12. ayda çalışanların yüzde kaçı hâlâ şirkette).

    event_type: "voluntary" verirsen yalnızca istifalar "ayrılma" sayılır.
    min_at_risk: Ufukta 20'den az kişi gözlenmişse sonuç güvenilmez, NaN döner.
    """
    x, dur, ev = _cohort(df, as_of, cohort_start, event_type)

    def row(label, d, e):
        curve = kaplan_meier(d, e)
        out = {by: label, "hires": int(len(d)), "exits": int(e.sum())}
        for m in months:
            h = round(m * 30.44)
            out[f"retention_{m}m"] = survival_at(curve, h) if (d >= h).sum() >= min_at_risk else float("nan")
        return out

    rows = [row("All", dur, ev)]
    for key, idx in x.groupby(by).groups.items():
        rows.append(row(key, dur.loc[idx], ev.loc[idx]))
    table = pd.DataFrame(rows)
    first = f"retention_{months[0]}m"
    rest = table.iloc[1:].sort_values(first)
    return pd.concat([table.iloc[:1], rest], ignore_index=True)

def retention_curves(
    df: pd.DataFrame,
    as_of,
    cohort_start,
    by: str = "department",
    groups=None,
    event_type: str | None = None,
    step: int = 30,
    max_days: int = 1095,
    min_at_risk: int = 20,
) -> pd.DataFrame:
    """Grafik için elde tutma eğrileri: satırlar gün (step aralıklı), sütunlar gruplar.

    Bir ufukta 20'den az kişi gözlenmişse o noktadan sonrası boş (NaN) bırakılır.
    """
    x, dur, ev = _cohort(df, as_of, cohort_start, event_type)
    days = list(range(0, max_days + 1, step))
    members = {"All": x.index}
    for key, idx in x.groupby(by).groups.items():
        members[key] = idx
    out = {}
    for key, idx in members.items():
        if groups is not None and key not in groups:
            continue
        d, e = dur.loc[idx], ev.loc[idx]
        curve = kaplan_meier(d, e)
        out[key] = [survival_at(curve, t) if (d >= t).sum() >= min_at_risk else float("nan") for t in days]
    return pd.DataFrame(out, index=pd.Index(days, name="day"))