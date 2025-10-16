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
│  - Player season totals from Basketball Reference scraper   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGING LAYER                                              │
│  ├─ stg_player_season_totals                               │
│  │  - Renames columns to clear, descriptive names          │
│  │  - Standardizes data types                              │
│  │  - Light cleaning (e.g., g → games_played)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  INTERMEDIATE LAYER                                         │
│  ├─ int_player_season_totals                               │
│  │  - Consolidates multi-team season records (2TM)         │
│  │  - One record per player per season                     │
│  │  - Handles traded players correctly                     │
│  │  - Filters players with 0 games played                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  MARTS LAYER                                                │
│  ├─ fct_player_season_stats                                │
│  │  - Analytics-ready fact table                           │
│  │  - Per-game averages calculated from totals             │
│  │  - Advanced metrics (TS%, PER-36, usage rate, etc.)     │
│  │  - Player categorizations and role classifications      │
│  │  - Season context (lockouts, COVID adjustments)         │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
nba-dbt/
├── models/
│   ├── staging/                    # Raw data cleaning layer
│   │   ├── sources.yml            # Source table definitions
│   │   ├── schema.yml             # Model documentation & tests
│   │   └── stg_player_season_totals.sql
│   │
│   ├── intermediate/               # Business logic layer
│   │   ├── schema.yml
│   │   └── int_player_season_totals.sql
│   │
│   └── marts/                      # Analytics-ready datasets
│       ├── schema.yml
│       └── fct_player_season_stats.sql
│
├── tests/                          # Custom data tests
│   ├── made_not_greater_than_attempted.sql
│   ├── field_goals_match_components.sql
│   ├── rebounds_match_components.sql
│   └── games_started_not_greater_than_played.sql
│
├── macros/                         # Reusable SQL functions
├── seeds/                          # Static reference data (CSV)
├── snapshots/                      # Slowly changing dimensions
├── analyses/                       # Ad-hoc analytical queries
│
├── dbt_project.yml                # Project configuration
├── packages.yml                    # dbt package dependencies
└── profiles.yml                    # Database connection config
```

## 📈 Data Models

### Staging Models

#### `stg_player_season_totals`
- **Materialization**: View
- **Purpose**: Standardizes raw player season totals with clear column names
- **Key Transformations**:
  - Renames cryptic abbreviations (e.g., `fg` → `total_field_goals_made`, `g` → `games_played`)
  - Adds `season_year` field extracted from season string
  - Maintains all original statistics for full traceability
  - No filtering or aggregation at this stage

### Intermediate Models

#### `int_player_season_totals`
- **Materialization**: Table
- **Purpose**: One clean record per player per season with proper multi-team handling
- **Key Logic**:
  - **Multi-Team Season Handling**: When players are traded mid-season, Basketball Reference shows:
    - Individual stats for each team
    - A combined "2TM" (two-team) record with season totals
  - This model selects the "2TM" aggregate for traded players
  - Ensures no double-counting in downstream analytics
  - Adds `is_two_team_season_flag` for easy identification
- **Filters**: Excludes players with 0 games played

### Marts Models

#### `fct_player_season_stats`
- **Materialization**: Table
- **Purpose**: Analytics-ready fact table with comprehensive player statistics and advanced metrics
- **Key Features**:
  - **Per-Game Averages**: Calculated from season totals (PPG, RPG, APG, etc.)
  - **Advanced Metrics**:
    - True Shooting Percentage (TS%)
    - Per-36 minute stats (points, rebounds, assists)
    - Assist-to-Turnover Ratio
    - Usage Rate per game
    - Offensive Rating approximation
  - **Historical Context**:
    - Season-specific game schedules (handles lockouts, COVID seasons)
    - Season participation percentage
  - **Player Categorizations**:
    - Playing time categories (Starter, Rotation, Bench, etc.)
    - Scoring categories (Elite, High, Above Average, etc.)
    - Player roles (Primary Playmaker, Scoring Guard, Rim Protector, etc.)
    - Efficiency tiers based on TS%
    - Three-point shooting categories
  - **Fantasy Points**: Standard fantasy basketball scoring formula

## 📚 Resources

- [dbt Documentation](https://docs.getdbt.com/)
- [dbt Best Practices](https://docs.getdbt.com/guides/best-practices)
- [Basketball Reference](https://www.basketball-reference.com/) (data source reference)

## 📄 License

This project is for educational and analytical purposes.

---

