import pandas as pd
from functools import lru_cache
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@lru_cache(maxsize=1)
def load_commodity_volatility():
    # commodity, n_months, mean_index, std_index, mean_mom_change, std_mom_change, median_usdprice, cv_index
    df = pd.read_csv(os.path.join(DATA_DIR, "commodity_volatility.csv"))
    cat = load_commodity_category_map()
    if cat is not None:
        df = df.merge(cat, on="commodity", how="left")
    return df


@lru_cache(maxsize=1)
def load_country_volatility():
    # countryiso3, n_months, mean_index, std_index, mean_mom_change, std_mom_change, median_usdprice, cv_index
    return pd.read_csv(os.path.join(DATA_DIR, "country_volatility.csv"))


@lru_cache(maxsize=1)
def load_category_heatmap():
    # category, year_month, usdprice, base_price, price_index, mom_change_pct
    return pd.read_csv(os.path.join(DATA_DIR, "category_time_heatmap.csv"))


@lru_cache(maxsize=1)
def load_monthly_index():
    # countryiso3, commodity, year_month, usdprice, n_months, base_price, price_index, mom_change_pct
    return pd.read_csv(os.path.join(DATA_DIR, "monthly_pair_index.csv"))


@lru_cache(maxsize=1)
def load_scatter_base():
    # countryiso3, commodity, first_index, last_index, n_months, avg_usdprice, cv_index, long_term_increase_pct
    df = pd.read_csv(os.path.join(DATA_DIR, "pair_growth_scatter_base.csv"))
    cat = load_commodity_category_map()
    if cat is not None:
        df = df.merge(cat, on="commodity", how="left")
    return df


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
        return sorted(cat["category"].dropna().unique().tolist())
    hm = load_category_heatmap()
    return sorted(hm["category"].dropna().unique().tolist())


def get_unique_commodities():
    df = load_monthly_index()
    return sorted(df["commodity"].dropna().unique().tolist())


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
    monthly = monthly.sort_values("year_month")
    return monthly


def get_commodity_monthly_trend(commodities):
    df = load_monthly_index()
    filtered = df[df["commodity"].isin(commodities)]
    monthly = filtered.groupby(["commodity", "year_month"])["usdprice"].median().reset_index()
    return monthly.sort_values("year_month")


def get_country_detail(country_iso3):
    df = load_monthly_index()
    return df[df["countryiso3"] == country_iso3]
