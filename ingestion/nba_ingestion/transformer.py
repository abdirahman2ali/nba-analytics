import pandas as pd


def add_season_column(df: pd.DataFrame, season_end_year: int) -> pd.DataFrame:
    """Add a SEASON column in 'YYYY-YY' format (e.g., '2023-24')."""
    df = df.copy()
    df["SEASON"] = f"{season_end_year - 1}-{str(season_end_year)[-2:]}"
    return df


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names for PostgreSQL compatibility.

    Applies lowercase, replaces Basketball Reference shorthand with full names,
    and removes special characters.
    """
    df = df.copy()
    df.columns = (
        df.columns
        .str.lower()
        .str.replace("%", "_pct", regex=False)
        .str.replace("3p", "three_p", regex=False)
        .str.replace("2p", "two_p", regex=False)
        .str.replace("-", "_", regex=False)
    )
    return df


def prepare_for_db(df: pd.DataFrame, season_end_year: int) -> pd.DataFrame:
    """Add season column and clean column names for database insertion."""
    df = add_season_column(df, season_end_year)
    df = clean_column_names(df)
    return df
