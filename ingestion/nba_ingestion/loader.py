import os
import pandas as pd
from databricks import sql as dbsql


TABLE_DDL = """
CREATE TABLE IF NOT EXISTS nba.{table_name} (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    player_id STRING,
    player STRING,
    age DECIMAL(5,2),
    team STRING,
    pos STRING,
    g DECIMAL(5,1),
    fg DECIMAL(7,1),
    fga DECIMAL(7,1),
    fg_pct DECIMAL(5,3),
    ft DECIMAL(7,1),
    fta DECIMAL(7,1),
    ft_pct DECIMAL(5,3),
    ast DECIMAL(7,1),
    pf DECIMAL(7,1),
    pts DECIMAL(7,1),
    awards STRING,
    season STRING,
    trb DECIMAL(7,1),
    mp DECIMAL(7,1),
    gs DECIMAL(5,1),
    orb DECIMAL(7,1),
    drb DECIMAL(7,1),
    stl DECIMAL(7,1),
    blk DECIMAL(7,1),
    tov DECIMAL(7,1),
    three_p DECIMAL(7,1),
    three_pa DECIMAL(7,1),
    three_p_pct DECIMAL(5,3),
    two_p DECIMAL(7,1),
    two_pa DECIMAL(7,1),
    two_p_pct DECIMAL(5,3),
    efg_pct DECIMAL(5,3),
    trp_dbl INT,
    created_at TIMESTAMP DEFAULT current_timestamp()
)
USING DELTA
"""


def _get_connection():
    """Open a Databricks SQL connection using env vars."""
    hostname = os.environ["DATABRICKS_SERVER_HOSTNAME"]
    http_path = os.environ["DATABRICKS_HTTP_PATH"]
    token = os.environ["DATABRICKS_TOKEN"]
    return dbsql.connect(
        server_hostname=hostname,
        http_path=http_path,
        access_token=token,
    )


def ensure_schema() -> None:
    """Create the nba schema if it does not exist."""
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS nba")


def ensure_table(table_name: str = "player_season_totals") -> None:
    """Create the player season totals Delta table if it does not exist."""
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(TABLE_DDL.format(table_name=table_name))


def get_last_loaded_year(table_name: str = "player_season_totals"):
    """Return the season end year of the most recently loaded season, or None if the table is empty."""
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT MAX(CAST(LEFT(season, 4) AS INT) + 1) FROM nba.{table_name}"
            )
            row = cur.fetchone()
            return row[0] if row else None


def write_to_db(df: pd.DataFrame, table_name: str = "player_season_totals") -> None:
    """Append a DataFrame to the target Delta table in chunks."""
    cols = [c for c in df.columns]
    placeholders = ", ".join(["?" for _ in cols])
    col_list = ", ".join(cols)
    insert_sql = f"INSERT INTO nba.{table_name} ({col_list}) VALUES ({placeholders})"

    with _get_connection() as conn:
        with conn.cursor() as cur:
            chunk_size = 500
            records = df.where(pd.notnull(df), None).values.tolist()
            for i in range(0, len(records), chunk_size):
                cur.executemany(insert_sql, records[i : i + chunk_size])
