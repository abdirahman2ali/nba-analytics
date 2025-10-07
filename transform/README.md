# NBA dbt Project

This dbt project contains transformations for NBA data analytics.

## Project Structure

- **models/**: SQL transformation models organized by layer
  - **staging/**: Raw data cleaning and standardization
  - **intermediate/**: Business logic transformations
  - **marts/**: Final analytics-ready tables
- **tests/**: Custom data tests
- **macros/**: Reusable SQL functions
- **seeds/**: Static CSV data files
- **snapshots/**: Slowly changing dimension tracking
- **analyses/**: Ad-hoc analytical queries

## Getting Started

### Prerequisites

1. Install dbt:
   ```bash
   pip install dbt-core dbt-<your-adapter>
   # For example: dbt-postgres, dbt-snowflake, dbt-bigquery, etc.
   ```

2. Configure your profile in `~/.dbt/profiles.yml`:
   ```yaml
   nba_dbt:
     target: dev
     outputs:
       dev:
         type: <your-database-type>
         # Add your database connection details here
   ```

### Running the Project

```bash
# Install dependencies
dbt deps

# Run all models
dbt run

# Run tests
dbt test

# Build everything (run + test)
dbt build

# Generate and serve documentation
dbt docs generate
dbt docs serve
```

## Development Workflow

1. Create new models in the appropriate folder under `models/`
2. Add tests in schema.yml files
3. Run `dbt run --select <model_name>` to test your model
4. Run `dbt test --select <model_name>` to validate
5. Document your changes in the README or schema files

## Resources

- Learn more about dbt [in the docs](https://docs.getdbt.com/docs/introduction)
- Check out [Discourse](https://discourse.getdbt.com/) for commonly asked questions
- Join the [chat](https://community.getdbt.com/) on Slack for live discussions

