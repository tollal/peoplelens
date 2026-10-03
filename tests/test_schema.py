import pandas as pd
import pandera.pandas as pa
import pytest

from peoplelens.schema import validate_employees


def make_df(**overrides):
    data = {
        "employee_id": ["E1", "E2"],
        "hire_date": pd.to_datetime(["2022-01-10", "2023-03-01"]),
        "termination_date": pd.to_datetime(["2024-05-01", None]),
        "termination_type": ["voluntary", None],
        "department": ["Sales", "IT"],
        "job_title": ["Analyst", None],
        "manager_id": [None, "E1"],
        "fte": [1.0, 0.5],
        "monthly_salary": [50000.0, None],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_valid_data_passes():
    validate_employees(make_df())


def test_duplicate_employee_id_fails():
    with pytest.raises(pa.errors.SchemaErrors):
        validate_employees(make_df(employee_id=["E1", "E1"]))


def test_termination_before_hire_fails():
    df = make_df(termination_date=pd.to_datetime(["2021-01-01", None]))
    with pytest.raises(pa.errors.SchemaErrors):
        validate_employees(df)