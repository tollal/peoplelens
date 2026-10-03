"""Temel İK metrikleri. Her metriğin tanımı docstring'inde yazılıdır.

Kural: termination_date = son çalışma günü. Çalışan o gün dahil aktif sayılır.
"""

import pandas as pd


def _active_mask(df: pd.DataFrame, as_of) -> pd.Series:
    d = pd.Timestamp(as_of)
    return (df["hire_date"] <= d) & (
        df["termination_date"].isna() | (df["termination_date"] >= d)
    )


def headcount(df: pd.DataFrame, as_of) -> int:
    """Verilen tarihte aktif çalışan sayısı."""
    return int(_active_mask(df, as_of).sum())


def fte_count(df: pd.DataFrame, as_of) -> float:
    """Verilen tarihte aktif çalışanların FTE toplamı."""
    return float(df.loc[_active_mask(df, as_of), "fte"].sum())


def hires(df: pd.DataFrame, start, end) -> int:
    """[start, end] aralığında (uçlar dahil) işe giren sayısı."""
    return int(df["hire_date"].between(pd.Timestamp(start), pd.Timestamp(end)).sum())


def terminations(df: pd.DataFrame, start, end, termination_type: str | None = None) -> int:
    """[start, end] aralığında ayrılan sayısı. İstenirse gönüllü/gönülsüz süzülür."""
    mask = df["termination_date"].between(pd.Timestamp(start), pd.Timestamp(end))
    if termination_type is not None:
        mask &= df["termination_type"] == termination_type
    return int(mask.sum())


def turnover_rate(
    df: pd.DataFrame,
    start,
    end,
    termination_type: str | None = None,
    annualize: bool = False,
) -> float:
    """Ayrılma oranı = dönemdeki ayrılanlar / ortalama headcount.

    Ortalama headcount = (dönem başı + dönem sonu headcount) / 2.
    Dönem başı = start tarihinden bir gün önceki headcount.
    annualize=True: oran 365 / dönem gün sayısı ile yıllığa çevrilir.
    """
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    opening = headcount(df, s - pd.Timedelta(days=1))
    closing = headcount(df, e)
    avg = (opening + closing) / 2
    if avg == 0:
        return float("nan")
    rate = terminations(df, s, e, termination_type) / avg
    if annualize:
        rate *= 365 / ((e - s).days + 1)
    return rate


def turnover_by(
    df: pd.DataFrame,
    start,
    end,
    by: str = "department",
    termination_type: str | None = None,
    annualize: bool = False,
) -> pd.DataFrame:
    """Turnover'ı bir kırılıma (varsayılan: departman) göre hesaplar."""
    rows = []
    for key, group in df.groupby(by):
        rows.append(
            {
                by: key,
                "headcount_end": headcount(group, end),
                "terminations": terminations(group, start, end, termination_type),
                "turnover_rate": turnover_rate(
                    group, start, end, termination_type, annualize
                ),
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values("turnover_rate", ascending=False).reset_index(drop=True)