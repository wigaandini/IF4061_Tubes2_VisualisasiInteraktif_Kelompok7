import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from translations import COMMODITY_ID, CATEGORY_ID, translate_commodity, translate_category

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RAW_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR = os.path.join(BASE_DIR, "data", "processed")
os.makedirs(OUT_DIR, exist_ok=True)


def log(msg):
    print(f"  → {msg}")


def load_raw_data():
    print("\n[1/6] Memuat data mentah...")

    path = os.path.join(RAW_DIR, "wfp_food_prices_final_dataset.csv")
    df = pd.read_csv(path, parse_dates=["date"])
    log(f"Loaded: {len(df):,} baris, {df['commodity'].nunique()} komoditas, {df['countryiso3'].nunique()} negara")

    cat_path = os.path.join(RAW_DIR, "wfp_commodities_global.csv")
    if os.path.exists(cat_path):
        cat_df = pd.read_csv(cat_path)[["commodity", "category"]].drop_duplicates()
        if "category" not in df.columns:
            df = df.merge(cat_df, on="commodity", how="left")
        log(f"Kategori dimuat: {df['category'].nunique()} kategori")

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["year_month"] = df["date"].dt.to_period("M").astype(str)

    return df


def apply_translations(df):
    print("\n[2/6] Menerapkan terjemahan Bahasa Indonesia...")

    df = df.copy()
    df["commodity"] = df["commodity"].map(lambda x: translate_commodity(x))
    if "category" in df.columns:
        df["category"] = df["category"].map(lambda x: translate_category(x))

    translated_comm = sum(1 for c in df["commodity"].unique() if c in COMMODITY_ID.values())
    total_comm = df["commodity"].nunique()
    untranslated = [c for c in df["commodity"].unique() if c not in COMMODITY_ID.values()]
    log(f"Komoditas diterjemahkan: {translated_comm}/{total_comm}")

    if untranslated:
        log(f"Belum diterjemahkan ({len(untranslated)}): {untranslated[:10]}{'...' if len(untranslated) > 10 else ''}")

    return df


def compute_monthly_pair_index(df):
    print("\n[3/6] Menghitung indeks bulanan per pasangan negara-komoditas...")

    pairs = df.groupby(["countryiso3", "commodity", "year_month"])["usdprice"].median().reset_index()
    pairs = pairs.sort_values(["countryiso3", "commodity", "year_month"])

    base = pairs.groupby(["countryiso3", "commodity"]).first().reset_index()[["countryiso3", "commodity", "usdprice"]]
    base.columns = ["countryiso3", "commodity", "base_price"]
    pairs = pairs.merge(base, on=["countryiso3", "commodity"])

    pairs["price_index"] = (pairs["usdprice"] / pairs["base_price"]) * 100

    pairs["mom_change_pct"] = pairs.groupby(["countryiso3", "commodity"])["price_index"].pct_change() * 100

    n_months = pairs.groupby(["countryiso3", "commodity"])["year_month"].nunique().reset_index(name="n_months")
    pairs = pairs.merge(n_months, on=["countryiso3", "commodity"])

    out = os.path.join(OUT_DIR, "monthly_pair_index.csv")
    pairs.to_csv(out, index=False)
    log(f"Disimpan: {out} ({len(pairs):,} baris)")

    return pairs


def compute_commodity_volatility(pairs):
    print("\n[4/6] Menghitung volatilitas per komoditas...")

    cv = pairs.groupby("commodity").agg(
        n_months=("year_month", "nunique"),
        mean_index=("price_index", "mean"),
        std_index=("price_index", "std"),
        mean_mom_change=("mom_change_pct", "mean"),
        std_mom_change=("mom_change_pct", "std"),
        median_usdprice=("usdprice", "median"),
    ).reset_index()

    cv["cv_index"] = cv["std_index"] / cv["mean_index"]
    cv = cv.dropna(subset=["cv_index"]).sort_values("cv_index", ascending=False)

    out = os.path.join(OUT_DIR, "commodity_volatility.csv")
    cv.to_csv(out, index=False)
    log(f"Disimpan: {out} ({len(cv)} komoditas)")

    top5 = cv.nlargest(5, "cv_index")
    for _, row in top5.iterrows():
        log(f"  {row['commodity']}: CV = {row['cv_index']:.3f}")

    return cv


def compute_country_volatility(pairs):
    print("\n[5/6] Menghitung volatilitas per negara...")

    cv = pairs.groupby("countryiso3").agg(
        n_months=("year_month", "nunique"),
        mean_index=("price_index", "mean"),
        std_index=("price_index", "std"),
        mean_mom_change=("mom_change_pct", "mean"),
        std_mom_change=("mom_change_pct", "std"),
        median_usdprice=("usdprice", "median"),
    ).reset_index()

    cv["cv_index"] = cv["std_index"] / cv["mean_index"]
    cv = cv.dropna(subset=["cv_index"]).sort_values("cv_index", ascending=False)

    out = os.path.join(OUT_DIR, "country_volatility.csv")
    cv.to_csv(out, index=False)
    log(f"Disimpan: {out} ({len(cv)} negara)")

    top5 = cv.nlargest(5, "cv_index")
    for _, row in top5.iterrows():
        log(f"  {row['countryiso3']}: CV = {row['cv_index']:.3f}")

    return cv


def compute_category_heatmap(df):
    print("\n[6/6] Menghitung heatmap kategori × waktu...")

    if "category" not in df.columns:
        log("SKIP — kolom 'category' tidak ditemukan")
        return None

    monthly_cat = df.groupby(["category", "year_month"])["usdprice"].median().reset_index()
    monthly_cat = monthly_cat.sort_values(["category", "year_month"])

    base = monthly_cat.groupby("category").first().reset_index()[["category", "usdprice"]]
    base.columns = ["category", "base_price"]
    monthly_cat = monthly_cat.merge(base, on="category")

    monthly_cat["price_index"] = (monthly_cat["usdprice"] / monthly_cat["base_price"]) * 100
    monthly_cat["mom_change_pct"] = monthly_cat.groupby("category")["price_index"].pct_change() * 100

    out = os.path.join(OUT_DIR, "category_time_heatmap.csv")
    monthly_cat.to_csv(out, index=False)
    log(f"Disimpan: {out} ({len(monthly_cat)} baris, {monthly_cat['category'].nunique()} kategori)")

    return monthly_cat


def main():
    print("=" * 60)
    print("  PROCESSING DATA UNTUK DASHBOARD")
    print("=" * 60)

    df = load_raw_data()
    df = apply_translations(df)
    pairs = compute_monthly_pair_index(df)
    compute_commodity_volatility(pairs)
    compute_country_volatility(pairs)
    compute_category_heatmap(df)

    print("\n" + "=" * 60)
    print("  SELESAI — Semua file tersimpan di data/processed/")
    print("=" * 60)

    print("\nFile yang dihasilkan:")
    for f in sorted(os.listdir(OUT_DIR)):
        if f.endswith(".csv"):
            size = os.path.getsize(os.path.join(OUT_DIR, f))
            print(f"  {f:40s} {size/1024:>8.1f} KB")


if __name__ == "__main__":
    main()