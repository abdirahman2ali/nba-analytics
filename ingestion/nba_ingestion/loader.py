import os
import pandas as pd
from sqlalchemy import create_engine, text


TABLE_DDL = """
CREATE TABLE IF NOT EXISTS nba.{table_name} (
    id SERIAL PRIMARY KEY,
    player_id VARCHAR(50),
    player VARCHAR(255),
    age DECIMAL(5,2),
    team VARCHAR(10),
    pos VARCHAR(10),
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
    awards TEXT,
    season VARCHAR(10),
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
    trp_dbl INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_player_id ON nba.{table_name}(player_id);
CREATE INDEX IF NOT EXISTS idx_player_id_season ON nba.{table_name}(player_id, season);
CREATE INDEX IF NOT EXISTS idx_player_season ON nba.{table_name}(player, season);
CREATE INDEX IF NOT EXISTS idx_season ON nba.{table_name}(season);
"""


def get_connection_string(direct: bool = False) -> str:
    """Return the Neon connection string from NBA_DATABASE_URL(_DIRECT)."""
    var = "NBA_DATABASE_URL_DIRECT" if direct else "NBA_DATABASE_URL"
    url = os.getenv(var)
    if not url:
        raise ValueError(f"{var} environment variable is required")
    return url


def get_engine(direct: bool = False):
    """Create and return a SQLAlchemy engine. Pass direct=True for DDL/migrations."""
    return create_engine(get_connection_string(direct=direct))


def ensure_schema(engine) -> None:
    """Create the nba schema if it does not exist."""
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS nba"))
        conn.commit()


def ensure_table(engine, table_name: str = "player_season_totals") -> None:
    """Create the player season totals table and indexes if they do not exist."""
    with engine.connect() as conn:
        conn.execute(text(TABLE_DDL.format(table_name=table_name)))
        conn.commit()


def get_last_loaded_year(engine, table_name: str = "player_season_totals"):
    """Return the season end year of the most recently loaded season, or None if the table is empty."""
    with engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT MAX(CAST(LEFT(season, 4) AS INT) + 1) FROM nba.{table_name}")
        )
        return result.fetchone()[0]


def write_to_db(df: pd.DataFrame, engine, table_name: str = "player_season_totals") -> None:
    """Append a DataFrame to the target table."""
    df.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
        schema="nba",
    )
