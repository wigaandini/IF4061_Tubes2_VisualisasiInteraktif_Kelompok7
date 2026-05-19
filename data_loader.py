import pandas as pd
from functools import lru_cache
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

CATEGORY_ID = {
    "cereals and tubers": "Serealia & Umbi",
    "meat, fish and eggs": "Daging, Ikan & Telur",
    "vegetables and fruits": "Sayuran & Buah",
    "pulses and nuts": "Kacang-kacangan",
    "oil and fats": "Minyak & Lemak",
    "milk and dairy": "Susu & Olahan Susu",
    "miscellaneous food": "Pangan Lainnya",
}


def translate_category(df, col="category"):
    if col in df.columns:
        df = df.copy()
        df[col] = df[col].map(CATEGORY_ID).fillna(df[col])
    return df


@lru_cache(maxsize=1)
def load_commodity_volatility():
    df = pd.read_csv(os.path.join(DATA_DIR, "commodity_volatility.csv"))
    cat = load_commodity_category_map()
    if cat is not None:
        df = df.merge(cat, on="commodity", how="left")
    return translate_category(df)


@lru_cache(maxsize=1)
def load_country_volatility():
    return pd.read_csv(os.path.join(DATA_DIR, "country_volatility.csv"))


@lru_cache(maxsize=1)
def load_category_heatmap():
    df = pd.read_csv(os.path.join(DATA_DIR, "category_time_heatmap.csv"))
    return translate_category(df)


@lru_cache(maxsize=1)
def load_monthly_index():
    return pd.read_csv(os.path.join(DATA_DIR, "monthly_pair_index.csv"))


@lru_cache(maxsize=1)
def load_scatter_base():
    df = pd.read_csv(os.path.join(DATA_DIR, "pair_growth_scatter_base.csv"))
    cat = load_commodity_category_map()
    if cat is not None:
        df = df.merge(cat, on="commodity", how="left")
    return translate_category(df)


@lru_cache(maxsize=1)
def load_commodity_category_map():
    path = os.path.join(DATA_DIR, "wfp_commodities_global.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    if "commodity" in df.columns and "category" in df.columns:
        return df[["commodity", "category"]].drop_duplicates()
    return None


def get_unique_categories():
    cat = load_commodity_category_map()
    if cat is not None:
        translated = cat["category"].map(CATEGORY_ID).dropna().unique()
        return sorted(translated.tolist())
    hm = load_category_heatmap()
    return sorted(hm["category"].dropna().unique().tolist())


def get_unique_countries():
    df = load_country_volatility()
    return sorted(df["countryiso3"].dropna().unique().tolist())


def get_year_range():
    df = load_monthly_index()
    years = pd.to_datetime(df["year_month"]).dt.year
    return int(years.min()), int(years.max())


def get_global_monthly_trend(year_range=None):
    df = load_monthly_index()
    if year_range:
        df = df.copy()
        df["_year"] = pd.to_datetime(df["year_month"]).dt.year
        df = df[(df["_year"] >= year_range[0]) & (df["_year"] <= year_range[1])]
    monthly = df.groupby("year_month")["usdprice"].median().reset_index(name="median_price")
    return monthly.sort_values("year_month")


def get_commodity_monthly_trend(commodities):
    df = load_monthly_index()
    filtered = df[df["commodity"].isin(commodities)]
    monthly = filtered.groupby(["commodity", "year_month"])["usdprice"].median().reset_index()
    return monthly.sort_values("year_month")


def get_country_detail(country_iso3):
    df = load_monthly_index()
    return df[df["countryiso3"] == country_iso3]
