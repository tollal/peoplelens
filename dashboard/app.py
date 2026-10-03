"""peoplelens dashboard.

Çalıştır:  uv run --extra dashboard streamlit run dashboard/app.py
Uygulama yerelde çalışır; yüklenen dosyalar bu bilgisayardan çıkmaz.
"""

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from peoplelens.attrition import retention_curves, retention_table
from peoplelens.clean import basic_clean
from peoplelens.mapping import load_company
from peoplelens.metrics import fte_count, headcount, hires, terminations, turnover_by, turnover_rate
from peoplelens.quality import quality_score, run_checks
from peoplelens.synthetic import generate_company, make_dirty
from peoplelens.turkey import liability_summary, severance_ceiling, severance_cost, severance_liability

st.set_page_config(page_title="peoplelens", layout="wide")
st.title("peoplelens · HR analytics")

TYPE_OPTIONS = {"Tümü": None, "Gönüllü": "voluntary", "Gönülsüz": "involuntary"}


@st.cache_data
def demo_data(dirty: bool) -> pd.DataFrame:
    df = generate_company()
    return make_dirty(df, seed=3)[0] if dirty else df


def load_uploaded(data_file, yaml_file):
    with tempfile.TemporaryDirectory() as tmp:
        data_path = Path(tmp) / ("data" + Path(data_file.name).suffix)
        yaml_path = Path(tmp) / "mapping.yaml"
        data_path.write_bytes(data_file.getvalue())
        yaml_path.write_bytes(yaml_file.getvalue())
        return load_company(data_path, yaml_path)


# ---------------------------------------------------------------- kenar çubuğu
notes: list[str] = []
with st.sidebar:
    st.header("Veri")
    source = st.radio("Kaynak", ["Demo şirketi (sentetik)", "Kendi dosyam"])
    if source.startswith("Demo"):
        dirty = st.checkbox("Veriyi bilerek kirlet (kalite motorunu göster)", value=True)
        raw = demo_data(dirty)
        default_as_of = pd.Timestamp("2026-09-30")
    else:
        data_file = st.file_uploader("İK dosyası (CSV / Excel)", type=["csv", "xlsx"])
        yaml_file = st.file_uploader("Mapping dosyası (YAML)", type=["yaml", "yml"])
        if not (data_file and yaml_file):
            st.info("Dosyayı ve mapping YAML'ını yükleyin. Örnek: examples/sirket_a.yaml")
            st.stop()
        try:
            raw, notes = load_uploaded(data_file, yaml_file)
        except Exception as e:
            st.error(f"Dosya okunamadı: {e}")
            st.stop()
        default_as_of = pd.Timestamp.today().normalize()

    clean_on = st.checkbox("Temel temizlik uygula", value=True)
    as_of = pd.Timestamp(st.date_input("Analiz tarihi", value=default_as_of))
    min_group = st.number_input("Minimum grup büyüklüğü (gizlilik)", min_value=1, max_value=50, value=5)
    st.caption("Bu büyüklükten küçük gruplar tablolarda gizlenir.")

report_raw = run_checks(raw, as_of)
score_raw = quality_score(raw, as_of)
clean_notes: list[str] = []
df = raw
if clean_on:
    df, clean_notes = basic_clean(raw)
start = as_of - pd.DateOffset(years=1) + pd.Timedelta(days=1)  # son 12 ay

tab_overview, tab_quality, tab_retention, tab_turkey = st.tabs(
    ["Genel bakış", "Veri kalitesi", "Elde tutma", "Türkiye: kıdem"]
)

# ------------------------------------------------------------------ genel bakış
with tab_overview:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Headcount", f"{headcount(df, as_of):,}")
    c2.metric("FTE", f"{fte_count(df, as_of):,.1f}")
    c3.metric("İşe giren (12 ay)", f"{hires(df, start, as_of):,}")
    c4.metric("Ayrılan (12 ay)", f"{terminations(df, start, as_of):,}")
    c5.metric("Turnover (12 ay)", f"{turnover_rate(df, start, as_of):.1%}")

    st.subheader("Aylık headcount")
    months = list(pd.date_range(end=as_of, periods=36, freq="ME"))
    if not months or months[-1] != as_of:
        months.append(as_of)
    st.line_chart(pd.Series([headcount(df, m) for m in months], index=months, name="headcount"))

    st.subheader("Departman bazlı turnover (son 12 ay)")
    kind = st.radio("Ayrılma türü", list(TYPE_OPTIONS), horizontal=True, key="turnover_kind")
    t = turnover_by(df, start, as_of, termination_type=TYPE_OPTIONS[kind])
    hidden = int((t["headcount_end"] < min_group).sum())
    t = t[t["headcount_end"] >= min_group].copy()
    t["turnover_pct"] = (t["turnover_rate"] * 100).round(1)
    st.bar_chart(t.set_index("department")["turnover_pct"])
    st.dataframe(t[["department", "headcount_end", "terminations", "turnover_pct"]])
    if hidden:
        st.caption(f"{hidden} küçük grup gizlilik kuralı nedeniyle gösterilmedi.")

# ---------------------------------------------------------------- veri kalitesi
with tab_quality:
    errors = report_raw[(report_raw["severity"] == "error") & (report_raw["rows"] > 0)]
    c1, c2, c3 = st.columns(3)
    c1.metric("Kalite skoru (ham veri)", f"{score_raw:.1%}")
    c2.metric("Hatalı kontrol türü (error)", len(errors))
    c3.metric("Temizlik sonrası skor", f"{quality_score(df, as_of):.1%}")
    found = report_raw[report_raw["rows"] > 0]
    if found.empty:
        st.success("Hiçbir sorun bulunmadı.")
    else:
        st.dataframe(found[["check", "severity", "description", "rows", "pct", "examples"]])
    if notes:
        st.subheader("Dönüşüm notları")
        for n in notes:
            st.write("- " + n)
    if clean_notes:
        st.subheader("Uygulanan temizlik adımları")
        for n in clean_notes:
            st.write("- " + n)
    st.download_button(
        "Temizlenmiş veriyi indir (CSV)",
        df.to_csv(index=False).encode("utf-8-sig"),
        "temiz_veri.csv",
        "text/csv",
    )

# ------------------------------------------------------------------ elde tutma
with tab_retention:
    st.write("İşe girenlerin yüzde kaçı 6, 12 ve 24. ayda hâlâ şirkette? (Kaplan-Meier)")
    cohort_start = pd.Timestamp(
        st.date_input("Cohort başlangıcı (bu tarihten sonra işe girenler)", value=as_of - pd.DateOffset(years=5))
    )
    kind_r = st.radio("Ayrılma türü", list(TYPE_OPTIONS), horizontal=True, key="retention_kind")
    etype = TYPE_OPTIONS[kind_r]
    table = retention_table(df, as_of, cohort_start, event_type=etype)
    table = table[(table["department"] == "All") | (table["hires"] >= min_group)].copy()
    for col in [c for c in table.columns if c.startswith("retention_")]:
        table[col] = (table[col] * 100).round(1)
    st.dataframe(table)
    st.caption("Boş (NaN) hücre: o ufukta 20'den az kişi gözlendi, sonuç güvenilmez.")
    options = list(table["department"])
    chosen = st.multiselect("Eğrisini göster", options, default=options[:3])
    if chosen:
        curves = retention_curves(df, as_of, cohort_start, groups=chosen, event_type=etype)
        st.line_chart(curves)

# ----------------------------------------------------------------- Türkiye modülü
with tab_turkey:
    try:
        ceiling = severance_ceiling(as_of)
        st.caption(f"{as_of.date()} için kıdem tazminatı tavanı: {ceiling:,.2f} TL")
    except ValueError as e:
        st.warning(str(e))
        ceiling = st.number_input("Tavan tutarını (TL) elle girin", min_value=0.0, value=0.0, step=100.0)

    if ceiling > 0:
        prob = st.slider("Ödeme olasılığı (1.0 = üst sınır)", 0.0, 1.0, 1.0, 0.05)
        liab = severance_liability(df, as_of, ceiling=ceiling, payout_probability=prob)
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam brüt yükümlülük", f"{liab['gross_liability'].sum():,.0f} TL")
        c2.metric("Kıdeme hak kazanan", f"{int(liab['eligible'].sum()):,}")
        c3.metric("Tavanın devrede olduğu", f"{int(liab['ceiling_binding'].sum()):,}")

        summary = liability_summary(liab)
        summary = summary[summary["headcount"] >= min_group].copy()
        summary["gross_liability"] = summary["gross_liability"].round(0)
        st.bar_chart(summary.set_index("department")["gross_liability"])
        st.dataframe(summary)

        try:
            cost = severance_cost(df, start, as_of)
            st.write(
                f"Son 12 ayda işveren kaynaklı çıkışların brüt kıdem maliyeti: "
                f"**{cost['gross'].sum():,.0f} TL** ({int(cost['eligible'].sum())} kişi)"
            )
        except ValueError as e:
            st.info(f"Geçmiş maliyet hesaplanamadı: {e}")
    st.caption(
        "Yükümlülük 'herkes bugün çıkarılsa' üst sınırıdır; aktüeryal TMS 19 hesabı ve "
        "hukuki görüş yerine geçmez. Maaş, giydirilmiş brüt kabul edilir."
    )