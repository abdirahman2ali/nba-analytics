# nba-analytics

End-to-end NBA analytics pipeline: scraping, transformation, and dashboard. Data flows from Basketball Reference (1950–present) through a Postgres warehouse and dbt transformation layer into a static dashboard.

## Components

| Directory | What it does |
|-----------|--------------|
| [`ingestion/`](ingestion/) | Python scraper — Basketball Reference → Postgres (`nba.player_season_averages`) |
| [`transform/`](transform/) | dbt pipeline — staging → intermediate → marts with advanced metrics |
| [`dashboard/`](dashboard/) | Static HTML dashboard generated from mart data, deployed to GitHub Pages |

## Architecture

```
Basketball Reference
        ↓
  ingestion/          (Python + SQLAlchemy + BeautifulSoup)
        ↓
  Postgres (Neon)     nba.player_season_averages
        ↓
  transform/          (dbt: staging → int → fct/dim)
        ↓
  dashboard/          (generate.py → index.html → GitHub Pages)
```

## Live dashboard

[abdirahman2ali.github.io/nba-dashboard](https://abdirahman2ali.github.io/nba-dashboard)

## CI/CD

- `ingestion/` changes trigger lint + test via `ingestion-ci.yml`
- `transform/` changes trigger dbt compile + run + test via `transform-ci.yml`
- `dashboard/` changes trigger a deploy to the GitHub Pages host via `dashboard-deploy.yml`
- Seasonal data load (ingestion → dbt run) runs every September 1st

## See also

- [ingestion/README.md](ingestion/README.md)
- [transform/README.md](transform/README.md)
