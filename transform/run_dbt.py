#!/usr/bin/env python3
"""
Databricks Job task wrapper: writes profiles.yml from env vars then runs dbt.
Env vars are injected by the cluster from the Databricks Secret Scope.
"""
import os
import subprocess
import pathlib
import textwrap
from dotenv import load_dotenv

load_dotenv(pathlib.Path.home() / ".claude" / ".env")

profiles_dir = pathlib.Path.home() / ".dbt"
profiles_dir.mkdir(exist_ok=True)
(profiles_dir / "profiles.yml").write_text(textwrap.dedent(f"""
    nba_dbt:
      target: prod
      outputs:
        prod:
          type: databricks
          host: {os.environ['DATABRICKS_SERVER_HOSTNAME']}
          http_path: {os.environ['DATABRICKS_HTTP_PATH']}
          token: {os.environ['DATABRICKS_TOKEN']}
          schema: nba
          threads: 2
"""))

project_dir = pathlib.Path(__file__).parent
subprocess.run(["dbt", "deps", "--project-dir", str(project_dir)], check=True)
subprocess.run(["dbt", "run",  "--project-dir", str(project_dir)], check=True)
subprocess.run(["dbt", "test", "--project-dir", str(project_dir)], check=True)


if __name__ == "__main__":
    pass
