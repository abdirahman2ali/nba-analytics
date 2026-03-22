import time
from dotenv import load_dotenv

from nba_ingestion.scraper import get_season_stats
from nba_ingestion.transformer import prepare_for_db
from nba_ingestion.loader import get_engine, ensure_schema, ensure_table, write_to_db

load_dotenv()

START_YEAR = 1950
END_YEAR = 2025
TABLE_NAME = "player_season_totals"


def run(start_year: int = START_YEAR, end_year: int = END_YEAR, table_name: str = TABLE_NAME):
    engine = get_engine()
    ensure_schema(engine)
    ensure_table(engine, table_name)

    successful = 0
    failed = []

    for year in range(start_year, end_year + 1):
        try:
            print(f"Fetching {year - 1}-{str(year)[-2:]} season... ", end="", flush=True)
            df = get_season_stats(year)

            if df is None or df.empty:
                print("no data")
                failed.append(year)
                time.sleep(1)
                continue

            df_db = prepare_for_db(df, year)
            write_to_db(df_db, engine, table_name)
            print(f"{len(df):,} players saved")
            successful += 1
            time.sleep(1)

        except Exception as e:
            print(f"error: {e}")
            failed.append(year)
            time.sleep(3)

    total = end_year - start_year + 1
    print(f"\nDone. {successful}/{total} seasons loaded.")
    if failed:
        print(f"Failed seasons: {failed}")


if __name__ == "__main__":
    run()
