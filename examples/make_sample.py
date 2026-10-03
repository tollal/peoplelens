"""Gerçek bir Türk şirketinin İK çıktısına benzeyen, kirli ve Türkçe örnek dosya üretir."""

from pathlib import Path

import pandas as pd

from peoplelens.synthetic import generate_company, make_dirty


def tr_number(v):
    if pd.isna(v):
        return None
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


here = Path(__file__).parent
clean = generate_company(n_employees=600, seed=11)
dirty, _ = make_dirty(clean, seed=5)

reasons = {"voluntary": "İstifa", "involuntary": "İşten Çıkarma"}
raw = pd.DataFrame(
    {
        "Sicil No": dirty["employee_id"],
        "İşe Giriş Tarihi": dirty["hire_date"].dt.strftime("%d.%m.%Y"),
        "Çıkış Tarihi": dirty["termination_date"].dt.strftime("%d.%m.%Y"),
        "Çıkış Nedeni": dirty["termination_type"].map(reasons),
        "Departman": dirty["department"],
        "Unvan": dirty["job_title"],
        "Yönetici Sicil No": dirty["manager_id"],
        "Brüt Maaş": dirty["monthly_salary"].map(tr_number),
    }
)
raw.to_csv(here / "sirket_a_ham.csv", sep=";", index=False, encoding="utf-8-sig")
print(f"Örnek dosya yazıldı: {len(raw)} satır")