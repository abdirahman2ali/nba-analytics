# 🏀 NBA Analytics dbt Project

A comprehensive data transformation pipeline for NBA player statistics, built with dbt (data build tool). This project transforms raw NBA player data into clean, analytics-ready datasets for advanced basketball analysis and insights.

## 📊 Project Overview

This dbt project processes NBA player season statistics through a multi-layered transformation pipeline. It handles complex scenarios like mid-season trades, calculates advanced metrics, and prepares data for downstream analytics and reporting.

### What This Project Does

- **Standardizes raw NBA data** with consistent naming conventions and data types
- **Handles multi-team seasons** when players are traded during a season
- **Calculates advanced metrics** like PER, true shooting percentage, and efficiency ratings
- **Creates analytics-ready datasets** for dashboards, reports, and machine learning models
- **Maintains data quality** through comprehensive testing and validation

### Use Cases

- **Player Performance Analysis**: Compare players across seasons and teams
- **Team Analytics**: Evaluate team composition and player contributions
- **Fantasy Basketball**: Generate rankings and projections
- **Contract Evaluation**: Assess player value using advanced metrics
- **Historical Trends**: Track player development and career trajectories
- **Predictive Modeling**: Build ML models for performance forecasting

## 🏗️ Data Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Raw Data Source (nba.player_season_averages)               │
│  - Player statistics from NBA API ingestion pipeline        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGING LAYER                                              │
│  ├─ stg_player_season_averages                             │
│  │  - Renames columns to clear, descriptive names          │
│  │  - Standardizes data types                              │
│  │  - Light cleaning (e.g., g → games_played)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  INTERMEDIATE LAYER                                         │
│  ├─ int_player_season_stats                                │
│  │  - Consolidates multi-team season records (2TM)         │
│  │  - One record per player per season                     │
│  │  - Handles traded players correctly                     │
│  │  - Business logic and data quality filters              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  MARTS LAYER (Coming Soon)                                 │
│  ├─ Player performance analytics                           │
│  ├─ Team aggregations                                      │
│  ├─ Position comparisons                                   │
│  └─ Historical trends                                      │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
nba-dbt/
├── models/
│   ├── staging/                    # Raw data cleaning layer
│   │   ├── sources.yml            # Source table definitions
│   │   ├── schema.yml             # Model documentation & tests
│   │   └── stg_player_season_averages.sql
│   │
│   ├── intermediate/               # Business logic layer
│   │   ├── schema.yml
│   │   └── int_player_season_stats.sql
│   │
│   └── marts/                      # Analytics-ready datasets
│       └── schema.yml
│
├── tests/                          # Custom data tests
├── macros/                         # Reusable SQL functions
├── seeds/                          # Static reference data (CSV)
├── snapshots/                      # Slowly changing dimensions
├── analyses/                       # Ad-hoc analytical queries
│
├── dbt_project.yml                # Project configuration
├── packages.yml                    # dbt package dependencies
└── profiles.yml                    # Database connection config
```
```

## 📈 Data Models

### Staging Models

#### `stg_player_season_averages`
- **Materialization**: View
- **Purpose**: Standardizes raw player statistics with clear column names
- **Key Transformations**:
  - Renames cryptic abbreviations (e.g., `fg` → `field_goals_made`)
  - Maintains all original statistics for full traceability
  - No filtering or aggregation at this stage

### Intermediate Models

#### `int_player_season_stats`
- **Materialization**: Table
- **Purpose**: One clean record per player per season
- **Key Logic**:
  - **Multi-Team Season Handling**: When players are traded mid-season, NBA records show:
    - Individual stats for each team
    - A combined "2TM" (two-team) record with season totals
  - This model selects the "2TM" aggregate for traded players
  - Ensures no double-counting in downstream analytics
- **Filters**: Excludes players with 0 games played

### Marts Models (Coming Soon)

Planned analytics models:
- `fct_player_performance`: Advanced metrics and efficiency ratings
- `dim_players`: Player dimension with career stats
- `agg_team_stats`: Team-level aggregations
- `top_scorers_by_season`: Rankings and leaderboards

## 🧪 Data Quality & Testing

This project includes comprehensive testing:

- **Primary Key Tests**: Ensure uniqueness of player-season records
- **Not Null Tests**: Validate critical fields like player_name, season
- **Referential Integrity**: Staging → Intermediate → Marts lineage
- **Custom Tests**: Business logic validation (coming soon)


## 📚 Resources

- [dbt Documentation](https://docs.getdbt.com/)
- [dbt Best Practices](https://docs.getdbt.com/guides/best-practices)
- [NBA Stats API Documentation](https://github.com/swar/nba_api)
- [Basketball Reference](https://www.basketball-reference.com/) (data source reference)

## 📄 License

This project is for educational and analytical purposes.

---

