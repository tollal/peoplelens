"""Ham şirket dosyası -> dönüşüm -> kalite raporu -> metrikler (uçtan uca)."""

from pathlib import Path

from peoplelens.mapping import load_company
from peoplelens.metrics import headcount, turnover_by
from peoplelens.quality import quality_score, run_checks

here = Path(__file__).parent
df, notes = load_company(here / "sirket_a_ham.csv", here / "sirket_a.yaml")

print(f"\n1) Dönüşüm: {len(df)} satır okundu")
for n in notes:
    print("   -", n)

AS_OF = "2026-09-30"
report = run_checks(df, AS_OF)
print(f"\n2) Veri kalitesi skoru: {quality_score(df, AS_OF):.1%}")
print(report[report["rows"] > 0][["check", "severity", "rows"]].to_string(index=False))

# Basit temizlik: tekrar kayıtları çıkar, departman yazımlarını en sık yazıma eşitle
df = df.drop_duplicates("employee_id")
norm = df["department"].str.strip().str.casefold()
df["department"] = df.groupby(norm)["department"].transform(lambda s: s.mode().iat[0])
print(f"\n3) Temizlik sonrası {headcount(df, AS_OF)} aktif çalışan. Son 12 ay turnover:")
print(turnover_by(df, "2025-10-01", AS_OF).round(3).to_string(index=False))