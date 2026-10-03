import pandas as pd
import pytest

from peoplelens.turkey import (
    liability_summary,
    notice_pay,
    notice_weeks,
    service_years,
    severance_ceiling,
    severance_cost,
    severance_liability,
    severance_pay,
)


def test_ceiling_periods():
    assert severance_ceiling("2026-09-30") == 73_729.87
    assert severance_ceiling("2026-03-01") == 64_948.77
    assert severance_ceiling("2025-08-15") == 53_919.68


def test_unknown_period_raises_instead_of_guessing():
    with pytest.raises(ValueError):
        severance_ceiling("2027-02-01")


def test_ceiling_binds_for_high_salary():
    # 10 yıl, aylık 100.000 TL: tavan devreye girer -> 73.729,87 x 10
    r = severance_pay(100_000, "2016-09-30", "2026-09-30")
    assert r["service_years"] == 10
    assert r["gross"] == pytest.approx(737_298.70, abs=0.01)
    assert r["net"] == pytest.approx(731_702.60, abs=0.1)  # damga vergisi binde 7,59


def test_below_ceiling_uses_actual_salary_and_partial_years():
    years = service_years("2023-03-15", "2026-09-30")
    r = severance_pay(40_000, "2023-03-15", "2026-09-30")
    assert r["gross"] == pytest.approx(40_000 * years)
    assert 3.5 < years < 3.6


def test_under_one_year_gets_nothing():
    r = severance_pay(50_000, "2026-03-01", "2026-09-30")
    assert r["eligible"] is False
    assert r["gross"] == 0


def test_notice_weeks_boundaries():
    assert [notice_weeks(y) for y in (0.3, 0.5, 1.4, 1.5, 2.9, 3, 10)] == [2, 4, 4, 6, 6, 8, 8]


def test_notice_pay():
    assert notice_pay(30_000, 2) == pytest.approx(6 * 7 * 1_000)


def _active_df():
    return pd.DataFrame(
        {
            "employee_id": ["E1", "E2", "E3"],
            "department": ["IT", "IT", "Sales"],
            "hire_date": pd.to_datetime(["2026-03-01", "2024-09-30", "2021-09-30"]),
            "termination_date": pd.to_datetime([None, None, None]),
            "monthly_salary": [50_000.0, 50_000.0, 100_000.0],
        }
    )


def test_liability_per_employee_and_totals():
    liab = severance_liability(_active_df(), "2026-09-30")
    by_id = liab.set_index("employee_id")
    assert by_id.loc["E1", "gross_liability"] == 0  # 1 yıldan az
    assert by_id.loc["E2", "gross_liability"] == pytest.approx(100_000)
    assert by_id.loc["E3", "gross_liability"] == pytest.approx(73_729.87 * 5)
    assert bool(by_id.loc["E3", "ceiling_binding"]) is True
    assert liab["gross_liability"].sum() == pytest.approx(100_000 + 73_729.87 * 5)


def test_liability_probability_and_summary():
    liab = severance_liability(_active_df(), "2026-09-30", payout_probability=0.5)
    assert liab["gross_liability"].sum() == pytest.approx(0.5 * (100_000 + 73_729.87 * 5))
    summary = liability_summary(liab).set_index("department")
    assert summary.loc["Sales", "ceiling_binding"] == 1


def test_severance_cost_counts_only_eligible_types():
    df = pd.DataFrame(
        {
            "employee_id": ["A", "B"],
            "department": ["IT", "IT"],
            "hire_date": pd.to_datetime(["2020-01-01", "2020-01-01"]),
            "termination_date": pd.to_datetime(["2026-08-31", "2026-08-31"]),
            "termination_type": ["involuntary", "voluntary"],
            "monthly_salary": [50_000.0, 50_000.0],
        }
    )
    cost = severance_cost(df, "2026-07-01", "2026-09-30")
    assert cost["employee_id"].tolist() == ["A"]
    assert cost.loc[0, "gross"] == pytest.approx(50_000 * service_years("2020-01-01", "2026-08-31"))