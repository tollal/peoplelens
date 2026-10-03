from peoplelens.attrition import retention_curves
from peoplelens.clean import basic_clean
from peoplelens.quality import quality_score, run_checks
from peoplelens.synthetic import generate_company, make_dirty

AS_OF = "2026-09-30"
ERROR_CHECKS = [
    "duplicate_employee_id", "missing_department", "termination_before_hire",
    "salary_non_positive", "fte_out_of_range", "self_manager", "department_spelling_variants",
    "manager_not_found",
]


def test_cleaning_removes_all_error_level_problems():
    dirty, _ = make_dirty(generate_company(n_employees=500, seed=1), seed=3)
    cleaned, notes = basic_clean(dirty)
    report = run_checks(cleaned, AS_OF).set_index("check")
    for check in ERROR_CHECKS:
        assert report.loc[check, "rows"] == 0, check
    assert quality_score(cleaned, AS_OF) == 1.0
    assert quality_score(dirty, AS_OF) < 1.0
    assert len(notes) >= 6


def test_cleaning_clean_data_changes_nothing():
    clean = generate_company(n_employees=300, seed=5)
    cleaned, notes = basic_clean(clean)
    assert notes == []
    assert len(cleaned) == len(clean)


def test_retention_curves_shape_and_monotonic():
    df = generate_company(n_employees=3000, seed=4)
    curves = retention_curves(df, AS_OF, "2021-10-01", groups=["All", "Sales"])
    assert list(curves.columns) == ["All", "Sales"]
    assert curves.loc[0, "All"] > 0.99  # ilk gün çok az kişi ayrılır
    series = curves["All"].dropna()
    assert series.is_monotonic_decreasing