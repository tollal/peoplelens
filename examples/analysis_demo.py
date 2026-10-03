"""Türkiye modülü + elde tutma analizi: sentetik şirket üzerinde uçtan uca örnek."""

import pandas as pd

from peoplelens.attrition import retention_table
from peoplelens.synthetic import generate_company
from peoplelens.turkey import liability_summary, severance_cost, severance_liability

pd.options.display.float_format = "{:,.2f}".format
AS_OF = "2026-09-30"
df = generate_company()

# 1) Bilançodaki kıdem tazminatı yükümlülüğü (üst sınır: herkes bugün çıkarılsa)
liab = severance_liability(df, AS_OF)
print(f"\n1) Kıdem tazminatı yükümlülüğü (üst sınır) - {AS_OF}")
print(f"   Aktif çalışan: {len(liab)}, kıdeme hak kazanan: {int(liab['eligible'].sum())}")
print(f"   Toplam brüt yükümlülük: {liab['gross_liability'].sum():,.0f} TL")
print(f"   Tavanın devrede olduğu çalışan: {int(liab['ceiling_binding'].sum())}")
print(liability_summary(liab).to_string(index=False))

# 2) Son 12 ayda işveren kaynaklı çıkışların kıdem maliyeti
cost = severance_cost(df, "2025-10-01", AS_OF)
print(f"\n2) Son 12 ay işveren kaynaklı çıkışlar: {len(cost)} kişi, "
      f"{int(cost['eligible'].sum())} kişi kıdeme hak kazandı")
print(f"   Brüt kıdem maliyeti: {cost['gross'].sum():,.0f} TL (net: {cost['net'].sum():,.0f} TL)")

# 3) Elde tutma: işe girenlerin yüzde kaçı 6/12/24. ayda hâlâ şirkette?
table = retention_table(df, AS_OF, cohort_start="2021-10-01")
print("\n3) Elde tutma oranları (2021-10-01 sonrası işe girenler)")
print(table.to_string(index=False, float_format=lambda v: f"{v:.1%}"))