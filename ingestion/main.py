import time
from dotenv import load_dotenv

from nba_ingestion.scraper import get_season_stats
from nba_ingestion.transformer import prepare_for_db
from nba_ingestion.loader import get_engine, ensure_schema, ensure_table, write_to_db

load_dotenv()

START_YEAR = 1950
END_YEAR = 2025
TABLE_NAME = "player_season_totals"
REQUEST_DELAY = 6       # seconds between successful requests
RETRY_DELAY = 120       # seconds to wait after a 429 before retrying
MAX_RETRIES = 3


def fetch_with_retry(year: int) -> object:
    """Fetch season stats with retry logic on 429 rate-limit responses."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return get_season_stats(year)
        except Exception as e:
            if "429" in str(e) and attempt < MAX_RETRIES:
                print(f"rate limited — waiting {RETRY_DELAY}s (attempt {attempt}/{MAX_RETRIES})... ", end="", flush=True)
                time.sleep(RETRY_DELAY)
            else:
                raise


def run(start_year: int = START_YEAR, end_year: int = END_YEAR, table_name: str = TABLE_NAME):
    engine = get_engine()
    ensure_schema(engine)
    ensure_table(engine, table_name)

    successful = 0
    failed = []

    for year in range(start_year, end_year + 1):
        try:
            print(f"Fetching {year - 1}-{str(year)[-2:]} season... ", end="", flush=True)
            df = fetch_with_retry(year)

            if df is None or df.empty:
                print("no data")
                failed.append(year)
                time.sleep(REQUEST_DELAY)
                continue

            df_db = prepare_for_db(df, year)
            write_to_db(df_db, engine, table_name)
            print(f"{len(df):,} players saved")
            successful += 1
            time.sleep(REQUEST_DELAY)

        except Exception as e:
            print(f"error: {e}")
            failed.append(year)
            time.sleep(REQUEST_DELAY)

    total = end_year - start_year + 1
    print(f"\nDone. {successful}/{total} seasons loaded.")
    if failed:
        print(f"Failed seasons: {failed}")


if __name__ == "__main__":
    import sys
    start = int(sys.argv[1]) if len(sys.argv) > 1 else START_YEAR
    run(start_year=start)
