"""README için grafikleri üretir (hepsi sentetik şirket üzerinde)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from peoplelens.metrics import headcount, turnover_by
from peoplelens.quality import run_checks
from peoplelens.synthetic import generate_company, make_dirty

out = Path(__file__).resolve().parent.parent / "docs"
out.mkdir(exist_ok=True)
AS_OF = "2026-09-30"
BLUE, RED, ORANGE = "#2E5597", "#C0392B", "#E08E0B"

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
company = generate_company()


def save(fig, name):
    fig.tight_layout()
    fig.savefig(out / name, dpi=150)
    plt.close(fig)
    print("yazıldı:", name)


# 1) Aylık headcount
months = pd.date_range("2021-09-30", AS_OF, freq="ME")
hc = [headcount(company, m) for m in months]
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(months, hc, color=BLUE, linewidth=2)
ax.set_title("Ay sonu headcount (sentetik şirket)", loc="left", fontweight="bold")
ax.set_ylabel("Aktif çalışan")
ax.grid(axis="y", alpha=0.3)
save(fig, "headcount_trend.png")

# 2) Departman bazlı turnover (son 12 ay)
t = turnover_by(company, "2025-10-01", AS_OF).sort_values("turnover_rate")
fig, ax = plt.subplots(figsize=(8, 4))
bars = ax.barh(t["department"], t["turnover_rate"] * 100, color=BLUE)
ax.bar_label(bars, fmt="%.1f%%", padding=3)
ax.set_title("Departman bazlı 12 aylık turnover", loc="left", fontweight="bold")
ax.set_xlabel("Turnover oranı (%)")
ax.set_xlim(0, t["turnover_rate"].max() * 100 * 1.15)
save(fig, "turnover_by_department.png")

# 3) Veri kalitesi: bilerek kirletilmiş veride bulunan sorunlar
dirty, _ = make_dirty(company, seed=3)
rep = run_checks(dirty, AS_OF)
rep = rep[rep["rows"] > 0].sort_values("rows")
colors = [RED if s == "error" else ORANGE for s in rep["severity"]]
fig, ax = plt.subplots(figsize=(8, 4.5))
bars = ax.barh(rep["check"], rep["rows"], color=colors)
ax.bar_label(bars, padding=3)
ax.set_title("Veri kalitesi: kirli veride bulunan sorunlar", loc="left", fontweight="bold")
ax.set_xlabel("Etkilenen satır (kırmızı = hata, turuncu = uyarı)")
save(fig, "data_quality_report.png")