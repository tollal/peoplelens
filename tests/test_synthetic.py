from peoplelens.synthetic import generate_company


def test_generates_valid_company():
    df = generate_company(n_employees=500, seed=1)
    assert len(df) > 300
    assert df["employee_id"].is_unique


def test_same_seed_gives_same_data():
    a = generate_company(n_employees=200, seed=7)
    b = generate_company(n_employees=200, seed=7)
    assert a.equals(b)


def test_has_both_active_and_terminated():
    df = generate_company(n_employees=500, seed=1)
    assert df["termination_date"].isna().any()
    assert df["termination_date"].notna().any()