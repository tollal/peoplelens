import pandas as pd
import pytest

from peoplelens.metrics import (
    fte_count,
    headcount,
    hires,
    terminations,
    turnover_by,
    turnover_rate,
)


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "employee_id": ["E1", "E2", "E3", "E4"],
            "hire_date": pd.to_datetime(
                ["2024-01-01", "2024-01-01", "2024-03-01", "2024-07-01"]
            ),
            "termination_date": pd.to_datetime(
                ["2024-06-30", None, "2024-09-15", None]
            ),
            "termination_type": ["voluntary", None, "involuntary", None],
            "department": ["Sales", "Sales", "IT", "IT"],
            "fte": [1.0, 0.5, 1.0, 1.0],
        }
    )


def test_headcount(df):
    assert headcount(df, "2024-02-01") == 2
    assert headcount(df, "2024-06-30") == 3  # son çalışma günü dahil
    assert headcount(df, "2024-07-01") == 3
    assert headcount(df, "2024-12-31") == 2


def test_fte_count(df):
    assert fte_count(df, "2024-02-01") == 1.5


def test_hires_and_terminations(df):
    assert hires(df, "2024-01-01", "2024-12-31") == 4
    assert terminations(df, "2024-01-01", "2024-12-31") == 2
    assert terminations(df, "2024-01-01", "2024-12-31", "voluntary") == 1


def test_turnover_rate(df):
    # 2. yarıyıl: başlangıç 3, bitiş 2, ortalama 2.5, ayrılan 1
    assert turnover_rate(df, "2024-07-01", "2024-12-31") == pytest.approx(0.4)
    assert turnover_rate(df, "2024-07-01", "2024-12-31", "voluntary") == 0.0


def test_turnover_annualized(df):
    rate = turnover_rate(df, "2024-07-01", "2024-12-31", annualize=True)
    assert rate == pytest.approx(0.4 * 365 / 184)


def test_turnover_by_department(df):
    result = turnover_by(df, "2024-07-01", "2024-12-31")
    assert result.iloc[0]["department"] == "IT"
    assert result.iloc[0]["turnover_rate"] == pytest.approx(1.0)