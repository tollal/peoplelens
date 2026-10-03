import pandas as pd
import pytest

from peoplelens.mapping import apply_mapping, load_mapping
from peoplelens.quality import run_checks

MAPPING = {
    "columns": {
        "employee_id": "Sicil No",
        "hire_date": "İşe Giriş",
        "termination_date": "Çıkış",
        "termination_type": "Neden",
        "department": "Bölüm",
        "monthly_salary": "Maaş",
    },
    "date_format": "%d.%m.%Y",
    "numbers": {"decimal": ",", "thousands": "."},
    "termination_type_map": {"voluntary": ["İstifa"], "involuntary": ["Fesih"]},
    "defaults": {"fte": 1.0},
}


def raw_df(reason="İstifa"):
    return pd.DataFrame(
        {
            "Sicil No": ["1001", "1002"],
            "İşe Giriş": ["15.03.2022", "01.07.2023"],
            "Çıkış": ["30.06.2024", None],
            "Neden": [reason, None],
            "Bölüm": ["Satış", "BT"],
            "Maaş": ["45.000,50", "60.000,00"],
        }
    )


def test_columns_dates_and_numbers_are_converted():
    df, _ = apply_mapping(raw_df(), MAPPING)
    assert df["employee_id"].tolist() == ["1001", "1002"]
    assert df.loc[0, "hire_date"] == pd.Timestamp("2022-03-15")
    assert df.loc[0, "monthly_salary"] == 45000.5
    assert df["fte"].tolist() == [1.0, 1.0]
    assert df.loc[0, "termination_type"] == "voluntary"


def test_missing_required_column_raises():
    raw = raw_df().drop(columns=["Bölüm"])
    with pytest.raises(ValueError):
        apply_mapping(raw, MAPPING)


def test_unmapped_termination_type_is_reported():
    _, notes = apply_mapping(raw_df(reason="Kovuldu"), MAPPING)
    assert any("termination_type" in n and "eşleşmedi" in n for n in notes)


def test_mapped_output_passes_quality_checks():
    df, _ = apply_mapping(raw_df(), MAPPING)
    assert run_checks(df, "2026-09-30")["rows"].sum() == 0


def test_load_mapping_reads_turkish_yaml(tmp_path):
    f = tmp_path / "m.yaml"
    f.write_text('columns:\n  employee_id: "Sicil Numarası"\n', encoding="utf-8")
    assert load_mapping(f)["columns"]["employee_id"] == "Sicil Numarası"