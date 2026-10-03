"""Canonical (standart) çalışan tablosu şeması."""

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series


class EmployeeSchema(pa.DataFrameModel):
    """Her şirketin verisi bu forma çevrilecek."""

    employee_id: Series[str] = pa.Field(unique=True, nullable=False)
    hire_date: Series[pd.Timestamp] = pa.Field(nullable=False)
    termination_date: Series[pd.Timestamp] = pa.Field(nullable=True)
    termination_type: Series[str] = pa.Field(
        nullable=True, isin=["voluntary", "involuntary"]
    )
    department: Series[str] = pa.Field(nullable=False)
    job_title: Series[str] = pa.Field(nullable=True)
    manager_id: Series[str] = pa.Field(nullable=True)
    fte: Series[float] = pa.Field(ge=0, le=1, nullable=False)
    monthly_salary: Series[float] = pa.Field(ge=0, nullable=True)

    @pa.dataframe_check
    def termination_after_hire(cls, df: pd.DataFrame) -> pd.Series:
        """Çıkış tarihi, işe giriş tarihinden önce olamaz."""
        return df["termination_date"].isna() | (
            df["termination_date"] >= df["hire_date"]
        )


def validate_employees(df: pd.DataFrame) -> pd.DataFrame:
    """Tabloyu kontrol eder, tüm hataları tek seferde raporlar."""
    return EmployeeSchema.validate(df, lazy=True)