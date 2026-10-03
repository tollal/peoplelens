from peoplelens.quality import quality_score, run_checks
from peoplelens.synthetic import generate_company, make_dirty

AS_OF = "2026-09-30"


def test_clean_company_has_no_issues():
    clean = generate_company(n_employees=500, seed=1)
    assert run_checks(clean, AS_OF)["rows"].sum() == 0
    assert quality_score(clean, AS_OF) == 1.0


def test_every_injected_error_is_found():
    clean = generate_company(n_employees=500, seed=1)
    dirty, injected = make_dirty(clean, seed=3)
    report = run_checks(dirty, AS_OF).set_index("check")
    for check, expected in injected.items():
        assert report.loc[check, "rows"] == expected, check


def test_dirty_data_scores_lower():
    clean = generate_company(n_employees=500, seed=1)
    dirty, _ = make_dirty(clean, seed=3)
    assert quality_score(dirty, AS_OF) < quality_score(clean, AS_OF)