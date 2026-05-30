import pandas as pd
from functools import lru_cache
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed")


@lru_cache(maxsize=1)
def load_commodity_volatility():
    return pd.read_csv(os.path.join(DATA_DIR, "commodity_volatility.csv"))


@lru_cache(maxsize=1)
def load_country_volatility():
    return pd.read_csv(os.path.join(DATA_DIR, "country_volatility.csv"))


@lru_cache(maxsize=1)
def load_category_heatmap():
    return pd.read_csv(os.path.join(DATA_DIR, "category_time_heatmap.csv"))


@lru_cache(maxsize=1)
def load_monthly_index():
    return pd.read_csv(os.path.join(DATA_DIR, "monthly_pair_index.csv"))


def get_unique_categories():
    df = load_category_heatmap()
    return sorted(df["category"].dropna().unique().tolist())


def get_unique_countries():
    df = load_country_volatility()
    return sorted(df["countryiso3"].dropna().unique().tolist())


def get_unique_commodities():
    df = load_commodity_volatility()
    return sorted(df["commodity"].dropna().unique().tolist())


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


def compute_kpis(year_range=None):
    df = load_monthly_index()

    if year_range:
        df = df.copy()
        df["_year"] = pd.to_datetime(df["year_month"]).dt.year
        df = df[(df["_year"] >= year_range[0]) & (df["_year"] <= year_range[1])]

    n_commodities = df["commodity"].nunique()
    n_countries = df["countryiso3"].nunique()

    monthly_global = df.groupby("year_month")["usdprice"].median()
    if len(monthly_global) > 0:
        puncak = monthly_global.max()
        lembah = monthly_global.min()
        lonjakan_pct = ((puncak - lembah) / lembah * 100) if lembah > 0 else 0
    else:
        lonjakan_pct = 0

    cv_per_commodity = df.groupby("commodity")["price_index"].agg(["std", "mean"])
    cv_per_commodity["cv"] = cv_per_commodity["std"] / cv_per_commodity["mean"]
    top_volatile = cv_per_commodity["cv"].idxmax() if len(cv_per_commodity) > 0 else "-"

    cv_per_country = df.groupby("countryiso3")["price_index"].agg(["std", "mean"])
    cv_per_country["cv"] = cv_per_country["std"] / cv_per_country["mean"]
    top_country_iso = cv_per_country["cv"].idxmax() if len(cv_per_country) > 0 else "-"

    try:
        import pycountry
        c = pycountry.countries.get(alpha_3=top_country_iso)
        top_country = f"{c.name} ({top_country_iso})" if c else top_country_iso
    except Exception:
        top_country = top_country_iso

    cat_hm = load_category_heatmap()
    if year_range:
        cat_hm = cat_hm.copy()
        cat_hm["_year"] = pd.to_datetime(cat_hm["year_month"]).dt.year
        cat_hm = cat_hm[(cat_hm["_year"] >= year_range[0]) & (cat_hm["_year"] <= year_range[1])]
    if "mom_change_pct" in cat_hm.columns and len(cat_hm) > 0:
        top_category = cat_hm.groupby("category")["mom_change_pct"].std().idxmax()
    else:
        top_category = "-"

    return {
        "lonjakan_pct": lonjakan_pct,
        "top_volatile": top_volatile,
        "top_country": top_country,
        "top_category": top_category,
    }