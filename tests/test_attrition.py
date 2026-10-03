import math

import pytest

from peoplelens.attrition import kaplan_meier, retention_table
from peoplelens.synthetic import DEPARTMENTS, WEIBULL_SHAPE, generate_company

AS_OF = "2026-09-30"
COHORT = "2021-10-01"


def test_kaplan_meier_matches_hand_calculation():
    curve = kaplan_meier([1, 2, 3, 4], [True, False, True, False]).set_index("day")
    assert curve.loc[1, "survival"] == pytest.approx(0.75)
    assert curve.loc[2, "survival"] == pytest.approx(0.75)  # 2. gün sansürlü, düşüş yok
    assert curve.loc[3, "survival"] == pytest.approx(0.375)
    assert curve.loc[4, "at_risk"] == 1


def test_estimate_matches_true_generator_curve():
    # Üreteç Weibull ayrılma süresi kullanıyor; gerçek eğri biliniyor, tahmin ona yaklaşmalı.
    df = generate_company(n_employees=8000, seed=2)
    table = retention_table(df, AS_OF, COHORT, months=(12,)).set_index("department")
    hazard = DEPARTMENTS["Sales"][1]
    scale = (1 / hazard) / math.gamma(1 + 1 / WEIBULL_SHAPE)
    true_12m = math.exp(-((365 / 30.44) / scale) ** WEIBULL_SHAPE)
    assert table.loc["Sales", "retention_12m"] == pytest.approx(true_12m, abs=0.05)


def test_table_has_all_row_and_ordering():
    df = generate_company(n_employees=3000, seed=4)
    table = retention_table(df, AS_OF, COHORT)
    assert table.iloc[0]["department"] == "All"
    assert {"hires", "exits", "retention_6m", "retention_12m", "retention_24m"} <= set(table.columns)
    rest = table.iloc[1:]["retention_6m"].dropna()
    assert rest.is_monotonic_increasing


def test_voluntary_only_retains_more_than_all_exits():
    df = generate_company(n_employees=3000, seed=4)
    all_exits = retention_table(df, AS_OF, COHORT, months=(12,)).iloc[0]["retention_12m"]
    voluntary = retention_table(df, AS_OF, COHORT, months=(12,), event_type="voluntary").iloc[0]["retention_12m"]
    assert voluntary >= all_exits