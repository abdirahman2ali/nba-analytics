#!/usr/bin/env python3
"""
NBA Analytics Dashboard Generator
Queries Databricks and outputs a self-contained interactive HTML dashboard.
"""
import os
import json
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv
from databricks import sql as dbsql

load_dotenv(Path(__file__).resolve().parents[3] / ".claude" / ".env")


def to_serializable(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def rows_to_dicts(cursor) -> list[dict]:
    cols = [desc[0] for desc in cursor.description]
    return [
        {k: to_serializable(v) for k, v in zip(cols, row)}
        for row in cursor.fetchall()
    ]


def main():
    conn = dbsql.connect(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )
    cur = conn.cursor()

    # League trends — full history (76 rows)
    cur.execute("""
        select
            season_year,
            avg_ppg,
            avg_ts_pct,
            coalesce(avg_3pa_per_game, 0) as avg_3pa_per_game,
            player_count,
            max_ppg_in_season
        from nba_marts.fct_season_league_averages
        order by season_year
    """)
    league_trends = rows_to_dicts(cur)

    # Career leaders — top 10, 400+ games
    cur.execute("""
        select
            player_name,
            career_ppg,
            career_rpg,
            career_apg,
            coalesce(career_spg, 0) as career_spg,
            coalesce(career_bpg, 0) as career_bpg,
            career_games_played,
            seasons_played,
            round(career_true_shooting_pct * 100, 1) as career_ts_pct,
            first_season_year,
            last_season_year
        from nba_marts.dim_player_career_stats
        where career_games_played >= 400
        order by career_ppg desc
        limit 10
    """)
    career_leaders = rows_to_dicts(cur)

    # Career RPG leaders — top 10, 400+ games
    cur.execute("""
        select
            player_name,
            career_ppg,
            career_rpg,
            career_apg,
            career_games_played,
            seasons_played,
            round(career_true_shooting_pct * 100, 1) as career_ts_pct,
            first_season_year,
            last_season_year
        from nba_marts.dim_player_career_stats
        where career_games_played >= 400 and career_rpg is not null
        order by career_rpg desc
        limit 10
    """)
    career_rpg_leaders = rows_to_dicts(cur)

    # Career APG leaders — top 10, 400+ games
    cur.execute("""
        select
            player_name,
            career_ppg,
            career_rpg,
            career_apg,
            career_games_played,
            seasons_played,
            round(career_true_shooting_pct * 100, 1) as career_ts_pct,
            first_season_year,
            last_season_year
        from nba_marts.dim_player_career_stats
        where career_games_played >= 400 and career_apg is not null
        order by career_apg desc
        limit 10
    """)
    career_apg_leaders = rows_to_dicts(cur)

    # Multi-season stats for interactive filters (1990+, all qualifying players)
    cur.execute("""
        select
            player_name,
            team_abbreviation,
            coalesce(primary_position, 'N/A') as primary_position,
            season,
            season_year,
            games_played,
            points_per_game,
            rebounds_per_game,
            assists_per_game,
            coalesce(steals_per_game, 0)  as steals_per_game,
            coalesce(blocks_per_game, 0)  as blocks_per_game,
            round(true_shooting_percentage * 100, 1) as ts_pct,
            coalesce(usage_rate_per_game, 0) as usage_rate_per_game,
            efficiency_tier,
            player_role
        from nba_marts.fct_player_season_stats
        where season_year >= 1990
        order by season_year desc, points_per_game desc
    """)
    season_stats = rows_to_dicts(cur)

    # All-time single-season scoring record
    cur.execute("""
        select player_name, season, points_per_game
        from nba_marts.fct_player_season_stats
        order by points_per_game desc
        limit 1
    """)
    top_season = rows_to_dicts(cur)[0]

    # Total unique players
    cur.execute("select count(distinct player_id) as n from nba_marts.fct_player_season_stats")
    total_players = int(cur.fetchone()[0])

    cur.close()
    conn.close()

    # Era summary
    era_buckets = [
        ('Pre-3PT Era',          lambda yr: yr < 1980),
        ('Early 3PT (1980\u201394)', lambda yr: 1980 <= yr <= 1994),
        ('Mid Era (1995\u20132009)', lambda yr: 1995 <= yr <= 2009),
        ('Analytics Era (2010+)', lambda yr: yr >= 2010),
    ]
    era_summary = []
    for name, cond in era_buckets:
        rows = [r for r in league_trends if cond(r['season_year'])]
        if rows:
            era_summary.append({
                'era': name,
                'seasons': len(rows),
                'avg_ppg':   round(sum(r['avg_ppg'] for r in rows) / len(rows), 1),
                'avg_ts_pct': round(sum(r['avg_ts_pct'] for r in rows) / len(rows) * 100, 1),
                'avg_3pa':   round(sum(r['avg_3pa_per_game'] for r in rows) / len(rows), 1),
            })

    data = {
        'league_trends':      league_trends,
        'career_leaders':     career_leaders,
        'career_rpg_leaders': career_rpg_leaders,
        'career_apg_leaders': career_apg_leaders,
        'season_stats':       season_stats,
        'top_season':         top_season,
        'total_players':      total_players,
        'era_summary':        era_summary,
    }

    html = generate_html(data)

    output_path = Path(__file__).parent / 'index.html'
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Dashboard generated: {output_path}")
    print(f"Open: file://{output_path.absolute()}")


def generate_html(data):
    data_json = json.dumps(data)
    top = data['top_season']
    total_players = data['total_players']
    latest_ts = round(data['league_trends'][-1]['avg_ts_pct'] * 100, 1)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NBA Analytics Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --page-bg:   #EBEBEB;
  --card-bg:   #FFFFFF;
  --border:    #D4D4D4;
  --shadow:    0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.05);
  --header-bg: #17274A;
  --accent:    #E8651A;
  --t1: #1C1C1C;
  --t2: #3D3D3D;
  --t3: #767676;
  --t4: #AAAAAA;
  --tb-blue:   #4E79A7;
  --tb-orange: #F28E2B;
  --tb-red:    #E15759;
  --tb-teal:   #76B7B2;
  --tb-green:  #59A14F;
  --tb-yellow: #EDC948;
  --tb-purple: #B07AA1;
  --tb-gray:   #BAB0AC;
  --grid: #E8E8E8;
}}

html {{ scroll-behavior: smooth; }}
body {{
  font-family: 'Inter', -apple-system, sans-serif;
  background: var(--page-bg);
  color: var(--t1);
  font-size: 13px;
  line-height: 1.5;
}}

/* ── HEADER ───────────────────────────────────────────────────────── */
header {{
  background: var(--header-bg);
  padding: 0 28px;
}}
.header-inner {{
  max-width: 1480px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
}}
.header-left {{ display: flex; align-items: center; gap: 14px; }}
.header-logo {{
  width: 30px; height: 30px;
  background: var(--accent);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; flex-shrink: 0;
}}
.header-title  {{ font-size: 15px; font-weight: 700; color: #fff; letter-spacing: -0.2px; }}
.header-div    {{ width: 1px; height: 18px; background: rgba(255,255,255,0.2); }}
.header-sub    {{ font-size: 12px; color: rgba(255,255,255,0.5); }}
.header-meta   {{ font-size: 11px; color: rgba(255,255,255,0.35); }}
.accent-bar    {{ height: 3px; background: var(--accent); }}

/* ── DASHBOARD ────────────────────────────────────────────────────── */
.dashboard {{
  max-width: 1480px;
  margin: 0 auto;
  padding: 20px 24px 40px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}}

/* ── PANEL ────────────────────────────────────────────────────────── */
.panel {{
  background: var(--card-bg);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  border-radius: 2px;
  padding: 18px 20px 20px;
}}
.panel-title {{ font-size: 13px; font-weight: 600; color: var(--t2); margin-bottom: 2px; }}
.panel-caption {{ font-size: 11px; color: var(--t3); margin-bottom: 16px; line-height: 1.5; }}
.panel-title-row {{
  display: flex; align-items: flex-start;
  justify-content: space-between; gap: 12px; margin-bottom: 2px;
}}
.panel-tag {{
  font-size: 10px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.8px; padding: 2px 7px; border-radius: 2px;
  white-space: nowrap; flex-shrink: 0; margin-top: 1px;
}}
.tag-hist   {{ background: rgba(78,121,167,0.12);  color: #3a6391; }}
.tag-season {{ background: rgba(232,101,26,0.12);  color: #b84d10; }}

/* ── KPI ──────────────────────────────────────────────────────────── */
.kpi-row {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; }}
.kpi {{
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-top: 3px solid var(--kpi-color, var(--tb-blue));
  box-shadow: var(--shadow);
  border-radius: 2px;
  padding: 16px 18px 14px;
  transition: border-top-color 0.3s;
}}
.kpi-label {{
  font-size: 10px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 1px; color: var(--t3); margin-bottom: 8px;
}}
.kpi-value {{
  font-size: 34px; font-weight: 800; color: var(--t1);
  letter-spacing: -1.5px; line-height: 1; margin-bottom: 5px;
}}
.kpi-value .suffix {{ font-size: 15px; font-weight: 500; color: var(--t3); letter-spacing: 0; }}
.kpi-sub  {{ font-size: 11px; color: var(--t3); line-height: 1.4; }}
.kpi-sub strong {{ color: var(--kpi-color, var(--tb-blue)); font-weight: 600; }}

/* ── INSIGHT CARDS ────────────────────────────────────────────────── */
.insight-row {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}}
.insight-card {{
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-left: 3px solid var(--ic, var(--tb-blue));
  box-shadow: var(--shadow);
  border-radius: 2px;
  padding: 16px 18px;
}}
.insight-stat {{
  font-size: 22px;
  font-weight: 800;
  color: var(--ic, var(--tb-blue));
  letter-spacing: -0.5px;
  line-height: 1;
  margin-bottom: 6px;
}}
.insight-title {{
  font-size: 12px;
  font-weight: 700;
  color: var(--t1);
  margin-bottom: 6px;
}}
.insight-desc {{
  font-size: 11px;
  color: var(--t3);
  line-height: 1.6;
}}

/* ── FILTER BAR ───────────────────────────────────────────────────── */
.filter-bar {{
  background: var(--card-bg);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  border-radius: 2px;
  padding: 12px 16px;
  display: flex;
  align-items: flex-end;
  gap: 20px;
  flex-wrap: wrap;
}}
.filter-group {{ display: flex; flex-direction: column; gap: 5px; }}
.filter-label {{
  font-size: 10px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.8px; color: var(--t3);
}}
.filter-select {{
  height: 30px; padding: 0 8px;
  border: 1px solid var(--border);
  background: #FAFAFA;
  font-family: 'Inter', sans-serif;
  font-size: 12px; color: var(--t1);
  border-radius: 2px; cursor: pointer;
  min-width: 110px;
}}
.filter-select:focus {{ outline: none; border-color: var(--tb-blue); }}
.btn-group {{
  display: flex;
  border: 1px solid var(--border);
  border-radius: 2px;
  overflow: hidden;
}}
.btn-group button {{
  padding: 5px 10px;
  font-size: 11px; font-weight: 600;
  color: var(--t3);
  background: #FAFAFA;
  border: none;
  border-right: 1px solid var(--border);
  cursor: pointer;
  font-family: 'Inter', sans-serif;
  transition: background 0.12s, color 0.12s;
}}
.btn-group button:last-child {{ border-right: none; }}
.btn-group button.active {{
  background: var(--header-bg);
  color: #FFFFFF;
}}
.btn-group button:hover:not(.active) {{
  background: #EFEFEF;
  color: var(--t1);
}}
.range-group {{ display: flex; flex-direction: column; gap: 5px; }}
.range-row   {{ display: flex; align-items: center; gap: 8px; }}
.filter-range {{
  width: 110px;
  accent-color: var(--tb-blue);
  cursor: pointer;
  height: 4px;
}}
.range-val {{ font-size: 12px; font-weight: 700; color: var(--t1); min-width: 20px; }}
.search-input {{
  height: 30px; padding: 0 10px;
  border: 1px solid var(--border);
  background: #FAFAFA;
  font-family: 'Inter', sans-serif;
  font-size: 12px; color: var(--t1);
  border-radius: 2px; width: 170px;
}}
.search-input:focus {{ outline: none; border-color: var(--tb-blue); }}
.search-input::placeholder {{ color: var(--t4); }}
.filter-meta {{
  margin-left: auto;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}}
.filter-results {{ font-size: 11px; color: var(--t3); }}
.filter-results strong {{ color: var(--t1); font-weight: 600; }}
.clear-btn {{
  font-size: 11px; font-weight: 600;
  color: var(--tb-blue);
  background: none; border: none;
  cursor: pointer; padding: 3px 6px;
  border-radius: 2px;
  font-family: 'Inter', sans-serif;
}}
.clear-btn:hover {{ background: rgba(78,121,167,0.1); }}

/* ── GRID ─────────────────────────────────────────────────────────── */
.row-2col   {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
.row-3col   {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }}
.col-w-60   {{ grid-template-columns: 3fr 2fr !important; }}

/* ── CHART ────────────────────────────────────────────────────────── */
.chart-box canvas {{ display: block; }}
.h-300 canvas {{ max-height: 300px; }}
.h-360 canvas {{ max-height: 360px; }}
.h-200 canvas {{ max-height: 200px; }}
.h-480 {{ height: 480px; }}

/* ── SECTION LABEL ────────────────────────────────────────────────── */
.section-label {{
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--t2);
  padding: 10px 14px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-left: 3px solid var(--header-bg);
  box-shadow: var(--shadow);
  border-radius: 2px;
}}

/* ── ERA TABLE ────────────────────────────────────────────────────── */
.era-table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 4px; }}
.era-table thead th {{
  text-align: left; padding: 7px 10px;
  font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.7px;
  color: var(--t3); background: #F7F7F7; border-bottom: 1px solid var(--border);
}}
.era-table thead th:not(:first-child) {{ text-align: right; }}
.era-table tbody td {{
  padding: 9px 10px; border-bottom: 1px solid #F0F0F0;
  color: var(--t2); vertical-align: middle;
}}
.era-table tbody td:not(:first-child) {{ text-align: right; font-variant-numeric: tabular-nums; }}
.era-table tbody tr:last-child td {{ border-bottom: none; }}
.era-table tbody tr:hover td {{ background: #FAFAFA; }}
.era-name {{ display: flex; align-items: center; gap: 8px; font-weight: 500; color: var(--t1); }}
.era-pip  {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
.era-val  {{ font-weight: 700; color: var(--t1); }}

/* ── STATS TABLE ──────────────────────────────────────────────────── */
.stats-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
.stats-table thead th {{
  text-align: left; padding: 7px 10px;
  font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.7px;
  color: var(--t3); background: #F7F7F7; border-bottom: 1px solid var(--border);
  white-space: nowrap; cursor: pointer; user-select: none;
}}
.stats-table thead th:hover {{ background: #EFEFEF; color: var(--t1); }}
.stats-table thead th.sort-asc::after  {{ content: ' ↑'; }}
.stats-table thead th.sort-desc::after {{ content: ' ↓'; color: var(--accent); }}
.stats-table thead th:not(:first-child):not(:nth-child(2)) {{ text-align: right; }}
.stats-table tbody td {{
  padding: 8px 10px; border-bottom: 1px solid #F4F4F4;
  color: var(--t2); vertical-align: middle;
}}
.stats-table tbody td:not(:first-child):not(:nth-child(2)) {{
  text-align: right; font-variant-numeric: tabular-nums;
}}
.stats-table tbody tr:nth-child(even) td {{ background: #FAFAFA; }}
.stats-table tbody tr:hover td {{ background: #EFF5FD; cursor: pointer; }}
.stats-table tbody tr:last-child td {{ border-bottom: none; }}
.rank   {{ font-size: 11px; font-weight: 700; color: var(--t4); width: 24px; display: inline-block; }}
.rank.gold {{ color: var(--accent); }}
.pname  {{ font-weight: 600; color: var(--t1); }}
.pname mark {{ background: rgba(232,101,26,0.18); color: var(--t1); border-radius: 2px; padding: 0 1px; }}
.stat-hi {{ font-weight: 700; color: var(--t1); }}
.tier-pill {{
  font-size: 10px; font-weight: 600; padding: 2px 6px;
  border-radius: 2px; white-space: nowrap;
}}
.tier-elite {{ background: rgba(89,161,79,0.12);  color: #3d8a34; }}
.tier-above {{ background: rgba(78,121,167,0.12); color: #3a6391; }}
.tier-avg   {{ background: rgba(186,176,172,0.22); color: #6b6b6b; }}
.tier-below {{ background: rgba(237,201,72,0.2);  color: #9b7c00; }}
.tier-poor  {{ background: rgba(225,87,89,0.12);  color: #b33335; }}
.no-results {{
  padding: 32px; text-align: center; color: var(--t3);
  font-size: 13px; font-style: italic;
}}

/* ── LEGEND ───────────────────────────────────────────────────────── */
.legend {{
  display: flex; flex-wrap: wrap; gap: 14px;
  margin-top: 12px; padding-top: 12px; border-top: 1px solid #F0F0F0;
}}
.legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--t3); }}
.legend-dot  {{ width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }}

/* ── INFO BAR ─────────────────────────────────────────────────────── */
.info-bar {{
  background: #F4F4F4;
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 9px 16px;
  display: flex; align-items: center; gap: 24px; flex-wrap: wrap;
  font-size: 11px; color: var(--t3);
}}
.info-bar strong {{ color: var(--t2); font-weight: 600; }}
.info-sep {{ color: var(--border); }}

/* ── FOOTER ───────────────────────────────────────────────────────── */
footer {{
  background: var(--header-bg);
  padding: 16px 28px;
  font-size: 11px;
  color: rgba(255,255,255,0.38);
}}
.footer-inner {{
  max-width: 1480px; margin: 0 auto;
  display: flex; justify-content: space-between;
}}

@media (max-width: 1024px) {{
  .kpi-row {{ grid-template-columns: repeat(2,1fr); }}
  .row-2col, .col-w-60 {{ grid-template-columns: 1fr !important; }}
  .filter-bar {{ gap: 14px; }}
}}
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <div class="header-left">
      <div class="header-logo">🏀</div>
      <span class="header-title">NBA Analytics Dashboard</span>
      <div class="header-div"></div>
      <span class="header-sub">75 Years of Player Performance &nbsp;·&nbsp; 1949–2025</span>
    </div>
    <span class="header-meta">Basketball Reference &nbsp;·&nbsp; dbt + Databricks</span>
  </div>
</header>
<div class="accent-bar"></div>

<div class="dashboard">

  <!-- Info bar -->
  <div class="info-bar">
    <span><strong>76</strong> seasons</span>
    <span class="info-sep">|</span>
    <span><strong>{total_players:,}</strong> players</span>
    <span class="info-sep">|</span>
    <span><strong>24,561</strong> player-season records</span>
    <span class="info-sep">|</span>
    <span>All-time PPG record: <strong>{top['player_name']} &middot; {top['points_per_game']} PPG ({top['season']})</strong></span>
    <span class="info-sep">|</span>
    <span>2024–25 avg TS%: <strong>{latest_ts}%</strong> (up from 40.1% in 1949)</span>
  </div>

  <!-- Static KPI row -->
  <div class="kpi-row">
    <div class="kpi" style="--kpi-color:#4E79A7;">
      <p class="kpi-label">Seasons in Database</p>
      <p class="kpi-value">76</p>
      <p class="kpi-sub">1949–50 <strong>through</strong> 2024–25</p>
    </div>
    <div class="kpi" style="--kpi-color:#59A14F;">
      <p class="kpi-label">Unique Players</p>
      <p class="kpi-value">{total_players:,}</p>
      <p class="kpi-sub">400+ career games <strong>tracked in depth</strong></p>
    </div>
    <div class="kpi" style="--kpi-color:#E8651A;">
      <p class="kpi-label">All-Time Single Season</p>
      <p class="kpi-value">{top['points_per_game']}<span class="suffix"> PPG</span></p>
      <p class="kpi-sub"><strong>{top['player_name']}</strong> &nbsp;&middot;&nbsp; {top['season']}</p>
    </div>
    <div class="kpi" style="--kpi-color:#76B7B2;">
      <p class="kpi-label">2024–25 League Avg TS%</p>
      <p class="kpi-value">{latest_ts}<span class="suffix">%</span></p>
      <p class="kpi-sub">Efficiency has never been <strong>higher in NBA history</strong></p>
    </div>
  </div>

  <!-- ── HISTORICAL ─────────────────────────────────────────────── -->
  <div class="section-label">Historical Trends &nbsp;&middot;&nbsp; 1949–2025</div>

  <div class="row-2col col-w-60">
    <div class="panel">
      <div class="panel-title-row">
        <div>
          <p class="panel-title">League Average Scoring by Season</p>
          <p class="panel-caption">Points per game across 76 seasons. Era bands mark the Pre-3PT and Analytics eras. Hover for detail.</p>
        </div>
        <span class="panel-tag tag-hist">1949–2025</span>
      </div>
      <div class="chart-box h-360"><canvas id="scoringChart"></canvas></div>
    </div>
    <div class="panel" style="display:flex;flex-direction:column;gap:18px;">
      <div>
        <p class="panel-title">Era Comparison</p>
        <p class="panel-caption">Average scoring, efficiency, and 3-point volume by era.</p>
        <table class="era-table" id="eraTable"></table>
      </div>
      <div>
        <p class="panel-title">True Shooting % · 1949–2025</p>
        <p class="panel-caption">Shot quality and efficiency have improved dramatically since the 1950s.</p>
        <div class="chart-box h-200"><canvas id="tsChart"></canvas></div>
      </div>
    </div>
  </div>

  <div class="panel">
    <div class="panel-title-row">
      <div>
        <p class="panel-title">The Three-Point Revolution · Avg 3PA Per Player Per Game</p>
        <p class="panel-caption">Introduced in 1979, ignored for 30 years, then analytics changed everything. Hover any year to compare.</p>
      </div>
      <span class="panel-tag tag-hist">Rule Change: 1979</span>
    </div>
    <div class="chart-box h-300"><canvas id="threePtChart"></canvas></div>
  </div>

  <!-- ── HISTORICAL INSIGHTS ────────────────────────────────────── -->
  <div class="insight-row">
    <div class="insight-card" style="--ic:#4E79A7;">
      <p class="insight-stat">+16.6pp</p>
      <p class="insight-title">The Efficiency Revolution</p>
      <p class="insight-desc">True Shooting % climbed from 40.1% in 1949 to 56.7% in 2025. Better spacing, shot selection driven by analytics, and the three-point line all contributed to the biggest efficiency gain in the sport's history.</p>
    </div>
    <div class="insight-card" style="--ic:#F28E2B;">
      <p class="insight-stat">0 &rarr; 3.3</p>
      <p class="insight-title">The Three-Point Takeover</p>
      <p class="insight-desc">The three-point rule was introduced in 1979 but largely ignored for 30 years. The analytics era changed everything: average 3PA per player per game went from 0.3 in 2000 to 3.3 by 2025, reshaping every position on the floor.</p>
    </div>
    <div class="insight-card" style="--ic:#59A14F;">
      <p class="insight-stat">188 &rarr; 452</p>
      <p class="insight-title">League Growth</p>
      <p class="insight-desc">The NBA expanded from 11 to 30 teams between 1949 and 2025, nearly tripling the number of active players each season. Scoring averages dipped in expansion years as talent was diluted across more rosters.</p>
    </div>
    <div class="insight-card" style="--ic:#E8651A;">
      <p class="insight-stat">50.4 PPG</p>
      <p class="insight-title">The Wilt Era</p>
      <p class="insight-desc">Wilt Chamberlain's 1961-62 season (50.4 PPG) remains the all-time single-season scoring record 63 years later. He also averaged 48.5 minutes per game that season, a figure impossible in today's 48-minute game with modern load management.</p>
    </div>
  </div>

  <!-- ── ALL-TIME ────────────────────────────────────────────────── -->
  <div class="section-label">All-Time Career Leaders &nbsp;&middot;&nbsp; Minimum 400 Games</div>

  <div class="row-3col">
    <div class="panel">
      <div class="panel-title-row">
        <div>
          <p class="panel-title">Points Per Game · Top 10</p>
          <p class="panel-caption">Wilt Chamberlain and Michael Jordan tied at 30.1 PPG. Orange = active or retired after 2020.</p>
        </div>
        <span class="panel-tag tag-hist">All-Time</span>
      </div>
      <div class="chart-box" style="height:320px;"><canvas id="careerChart"></canvas></div>
    </div>
    <div class="panel">
      <div class="panel-title-row">
        <div>
          <p class="panel-title">Rebounds Per Game · Top 10</p>
          <p class="panel-caption">Wilt at 22.9 RPG is in a category of his own. Modern bigs rarely exceed 12 RPG for a career.</p>
        </div>
        <span class="panel-tag tag-hist">All-Time</span>
      </div>
      <div class="chart-box" style="height:320px;"><canvas id="careerRpgChart"></canvas></div>
    </div>
    <div class="panel">
      <div class="panel-title-row">
        <div>
          <p class="panel-title">Assists Per Game · Top 10</p>
          <p class="panel-caption">John Stockton leads all-time at 10.5 APG. The modern era blends scoring with playmaking.</p>
        </div>
        <span class="panel-tag tag-hist">All-Time</span>
      </div>
      <div class="chart-box" style="height:320px;"><canvas id="careerApgChart"></canvas></div>
    </div>
  </div>

  <!-- ── SEASON ANALYSIS (DYNAMIC) ──────────────────────────────── -->
  <div class="section-label">Season Analysis &nbsp;&middot;&nbsp; Interactive Filters</div>

  <!-- Filter bar -->
  <div class="filter-bar">
    <div class="filter-group">
      <span class="filter-label">Season</span>
      <select class="filter-select" id="seasonSelect"></select>
    </div>
    <div class="filter-group">
      <span class="filter-label">Stat</span>
      <div class="btn-group" id="statToggle">
        <button class="active" data-stat="points_per_game">PPG</button>
        <button data-stat="rebounds_per_game">RPG</button>
        <button data-stat="assists_per_game">APG</button>
        <button data-stat="steals_per_game">SPG</button>
        <button data-stat="blocks_per_game">BPG</button>
      </div>
    </div>
    <div class="filter-group">
      <span class="filter-label">Position</span>
      <div class="btn-group" id="posFilter">
        <button class="active" data-pos="ALL">All</button>
        <button data-pos="PG">PG</button>
        <button data-pos="SG">SG</button>
        <button data-pos="SF">SF</button>
        <button data-pos="PF">PF</button>
        <button data-pos="C">C</button>
      </div>
    </div>
    <div class="range-group">
      <span class="filter-label">Min Games: <span id="minGamesVal">20</span></span>
      <div class="range-row">
        <input type="range" class="filter-range" id="minGames" min="5" max="70" value="20">
      </div>
    </div>
    <div class="filter-group">
      <span class="filter-label">Search Player</span>
      <input type="text" class="search-input" id="playerSearch" placeholder="e.g. LeBron...">
    </div>
    <div class="filter-meta">
      <span class="filter-results" id="filterResults">&nbsp;</span>
      <button class="clear-btn" id="clearBtn">&#x21ba; Reset filters</button>
    </div>
  </div>

  <!-- Dynamic KPI row -->
  <div class="kpi-row" id="dynKpiRow">
    <div class="kpi" id="dynKpi1" style="--kpi-color:#E8651A;"></div>
    <div class="kpi" id="dynKpi2" style="--kpi-color:#4E79A7;"></div>
    <div class="kpi" id="dynKpi3" style="--kpi-color:#59A14F;"></div>
    <div class="kpi" id="dynKpi4" style="--kpi-color:#76B7B2;"></div>
  </div>

  <!-- Leaderboard + Scatter -->
  <div class="row-2col">
    <div class="panel">
      <div class="panel-title-row">
        <div>
          <p class="panel-title" id="leadersTitle">Top 15 Scorers · Points Per Game</p>
          <p class="panel-caption">Bars colored by shooting efficiency tier. Updates with all filters.</p>
        </div>
        <span class="panel-tag tag-season" id="leadersTag">2024–25</span>
      </div>
      <div class="chart-box h-360"><canvas id="scorersChart"></canvas></div>
    </div>
    <div class="panel">
      <div class="panel-title-row">
        <div>
          <p class="panel-title">Efficiency vs. Volume · TS% and Usage Rate</p>
          <p class="panel-caption">Bubble size = PPG. Color = efficiency tier. Top players labeled.</p>
        </div>
        <span class="panel-tag tag-season" id="scatterTag">2024–25</span>
      </div>
      <div class="chart-box h-360"><canvas id="scatterChart"></canvas></div>
      <div class="legend" id="scatterLegend"></div>
    </div>
  </div>

  <!-- Full stats table -->
  <div class="panel">
    <div class="panel-title-row">
      <div>
        <p class="panel-title" id="tableTitle">Season Stats · Full Table</p>
        <p class="panel-caption">Click any column header to sort. Updates with all active filters.</p>
      </div>
      <span class="panel-tag tag-season" id="tableTag">2024–25</span>
    </div>
    <div id="tableWrap"></div>
  </div>

</div>
<footer>
  <div class="footer-inner">
    <span>Data: Basketball Reference &nbsp;&middot;&nbsp; Pipeline: Python + Databricks + dbt &nbsp;&middot;&nbsp; Dashboard: HTML + Chart.js</span>
    <span>Abdirahman Ali &nbsp;&middot;&nbsp; 2025</span>
  </div>
</footer>

<script>
const DATA = {data_json};

// ── DEFAULTS ───────────────────────────────────────────────────────────────
Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";
Chart.defaults.font.size   = 11;
Chart.defaults.color       = '#767676';

const TB = {{
  blue: '#4E79A7', orange: '#F28E2B', red: '#E15759',
  teal: '#76B7B2', green: '#59A14F', yellow: '#EDC948',
  purple: '#B07AA1', gray: '#BAB0AC',
}};

const TIER_COLOR = {{
  'Elite Efficiency':         TB.green,
  'Above Average Efficiency': TB.blue,
  'Average Efficiency':       TB.gray,
  'Below Average Efficiency': TB.yellow,
  'Poor Efficiency':          TB.red,
}};
const TIER_ORDER = ['Elite Efficiency','Above Average Efficiency','Average Efficiency','Below Average Efficiency','Poor Efficiency'];
const TIER_SHORT = {{'Elite Efficiency':'Elite','Above Average Efficiency':'Above Avg','Average Efficiency':'Average','Below Average Efficiency':'Below Avg','Poor Efficiency':'Poor'}};
const TIER_CLASS = {{'Elite Efficiency':'tier-elite','Above Average Efficiency':'tier-above','Average Efficiency':'tier-avg','Below Average Efficiency':'tier-below','Poor Efficiency':'tier-poor'}};

const STAT_LABEL = {{
  points_per_game: 'PPG', rebounds_per_game: 'RPG', assists_per_game: 'APG',
  steals_per_game: 'SPG', blocks_per_game: 'BPG',
}};
const STAT_LONG = {{
  points_per_game: 'Points Per Game', rebounds_per_game: 'Rebounds Per Game',
  assists_per_game: 'Assists Per Game', steals_per_game: 'Steals Per Game',
  blocks_per_game: 'Blocks Per Game',
}};
const LEADER_LABEL = {{
  points_per_game: 'Scoring Leader', rebounds_per_game: 'Rebounding Leader',
  assists_per_game: 'Assists Leader', steals_per_game: 'Steals Leader',
  blocks_per_game: 'Blocks Leader',
}};

function rgba(hex, a) {{
  const r=parseInt(hex.slice(1,3),16), g=parseInt(hex.slice(3,5),16), b=parseInt(hex.slice(5,7),16);
  return `rgba(${{r}},${{g}},${{b}},${{a}})`;
}}
function areaGrad(ctx, hex, h) {{
  const g = ctx.createLinearGradient(0,0,0,h);
  g.addColorStop(0,  rgba(hex, 0.18));
  g.addColorStop(0.6,rgba(hex, 0.06));
  g.addColorStop(1,  rgba(hex, 0));
  return g;
}}

const TT = {{
  backgroundColor:'#FFFFFF', borderColor:'#D4D4D4', borderWidth:1,
  padding:10, titleColor:'#1C1C1C', bodyColor:'#767676',
  titleFont:{{size:12,weight:'600'}}, bodyFont:{{size:11}},
  cornerRadius:2,
}};

const xAx = (title='') => ({{
  grid:{{color:'#E8E8E8',drawBorder:false}},
  border:{{color:'#CCCCCC',display:true}},
  ticks:{{color:'#767676',font:{{size:11}}}},
  title:{{display:!!title,text:title,color:'#767676',font:{{size:11}}}},
}});
const yAx = (title='') => ({{
  grid:{{color:'#E8E8E8',drawBorder:false}},
  border:{{display:false}},
  ticks:{{color:'#767676',font:{{size:11}}}},
  title:{{display:!!title,text:title,color:'#767676',font:{{size:11}}}},
}});

// ── STATE ──────────────────────────────────────────────────────────────────
let activeStat = 'points_per_game';
let activePos  = 'ALL';
let sortCol    = 'points_per_game';
let sortDir    = 'desc';

// Chart instances (dynamic)
let scorersChart = null;
let scatterChart = null;

// ── SEASON DROPDOWN ────────────────────────────────────────────────────────
(function initSeasons() {{
  const seasons = [...new Set(DATA.season_stats.map(p => p.season))].sort((a,b)=>b.localeCompare(a));
  const sel = document.getElementById('seasonSelect');
  seasons.forEach(s => {{
    const o = document.createElement('option');
    o.value = s; o.textContent = s;
    sel.appendChild(o);
  }});
  sel.value = seasons[0];
}})();

// ── FILTER HELPERS ─────────────────────────────────────────────────────────
function getFilters() {{
  return {{
    season:   document.getElementById('seasonSelect').value,
    minGames: +document.getElementById('minGames').value,
    pos:      activePos,
    stat:     activeStat,
    search:   document.getElementById('playerSearch').value.toLowerCase().trim(),
  }};
}}

function applyFilters(f) {{
  return DATA.season_stats
    .filter(p => p.season === f.season)
    .filter(p => p.games_played >= f.minGames)
    .filter(p => f.pos === 'ALL' || p.primary_position === f.pos)
    .filter(p => !f.search || p.player_name.toLowerCase().includes(f.search));
}}

function sortData(rows, col, dir) {{
  return [...rows].sort((a,b) => {{
    const av = a[col] ?? -Infinity, bv = b[col] ?? -Infinity;
    return dir === 'desc' ? bv - av : av - bv;
  }});
}}

// ── DYNAMIC KPIs ───────────────────────────────────────────────────────────
function updateKPIs(sorted, f) {{
  const stat  = f.stat;
  const label = STAT_LABEL[stat];
  const leader = sorted[0];
  const n = sorted.length;

  const avg = n ? (sorted.reduce((s,p)=>(s+(p[stat]||0)),0)/n).toFixed(1) : '—';
  const effSorted = [...sorted].sort((a,b)=>(b.ts_pct||0)-(a.ts_pct||0));
  const effLeader = effSorted[0];
  const eliteCount = sorted.filter(p=>p.efficiency_tier==='Elite Efficiency').length;

  document.getElementById('dynKpi1').innerHTML = `
    <p class="kpi-label">${{LEADER_LABEL[stat]}} &middot; ${{f.season}}</p>
    <p class="kpi-value">${{leader ? leader[stat] : '—'}}<span class="suffix"> ${{label}}</span></p>
    <p class="kpi-sub"><strong>${{leader ? leader.player_name : '—'}}</strong> &middot; ${{leader ? leader.team_abbreviation : ''}}</p>`;

  document.getElementById('dynKpi2').innerHTML = `
    <p class="kpi-label">Season Avg ${{label}}</p>
    <p class="kpi-value">${{avg}}<span class="suffix"> ${{label}}</span></p>
    <p class="kpi-sub">Across <strong>${{n}}</strong> qualifying players</p>`;

  document.getElementById('dynKpi3').innerHTML = `
    <p class="kpi-label">Efficiency Leader · TS%</p>
    <p class="kpi-value">${{effLeader ? effLeader.ts_pct : '—'}}<span class="suffix">%</span></p>
    <p class="kpi-sub"><strong>${{effLeader ? effLeader.player_name : '—'}}</strong> &middot; ${{effLeader ? effLeader.team_abbreviation : ''}}</p>`;

  document.getElementById('dynKpi4').innerHTML = `
    <p class="kpi-label">Elite Efficiency Players</p>
    <p class="kpi-value">${{eliteCount}}</p>
    <p class="kpi-sub"><strong>${{n ? Math.round(eliteCount/n*100) : 0}}%</strong> of qualifying players</p>`;
}}

// ── SCORERS CHART ──────────────────────────────────────────────────────────
function initScorersChart(top15, stat) {{
  const ctx = document.getElementById('scorersChart').getContext('2d');
  const labels  = top15.map(p => p.player_name.split(' ').slice(-1)[0] + ' (' + p.team_abbreviation + ')');
  const vals    = top15.map(p => p[stat] || 0);
  const bgColors = top15.map(p => rgba(TIER_COLOR[p.efficiency_tier]||TB.gray, 0.82));
  const bdColors = top15.map(p => TIER_COLOR[p.efficiency_tier]||TB.gray);

  scorersChart = new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels,
      datasets: [{{ label: STAT_LABEL[stat], data: vals,
        backgroundColor: bgColors, borderColor: bdColors,
        borderWidth: 1, borderRadius: 2, borderSkipped: false }}]
    }},
    options: {{
      indexAxis: 'y', responsive: true, maintainAspectRatio: true,
      animation: {{ duration: 400 }},
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          ...TT,
          callbacks: {{
            title: i => top15[i[0].dataIndex].player_name,
            label: i => {{
              const p = top15[i[0].dataIndex];
              return [
                ` ${{STAT_LABEL[stat]}}: ${{p[stat]}}`,
                ` TS%: ${{p.ts_pct}}%`,
                ` GP: ${{p.games_played}}`,
                ` ${{p.efficiency_tier||''}}`,
              ];
            }}
          }}
        }}
      }},
      scales: {{
        x: {{ ...xAx(STAT_LONG[stat]), min: getBarMin(vals), ticks:{{color:'#767676',font:{{size:10}}}} }},
        y: {{ ...yAx(), ticks:{{color:'#3D3D3D',font:{{size:11}}}} }},
      }}
    }}
  }});
}}

function getBarMin(vals) {{
  if (!vals.length) return 0;
  return Math.max(0, Math.floor(Math.min(...vals) * 0.88));
}}

function updateScorersChart(top15, stat) {{
  if (!scorersChart) return;
  scorersChart.data.labels = top15.map(p => p.player_name.split(' ').slice(-1)[0] + ' (' + p.team_abbreviation + ')');
  scorersChart.data.datasets[0].data       = top15.map(p => p[stat]||0);
  scorersChart.data.datasets[0].label      = STAT_LABEL[stat];
  scorersChart.data.datasets[0].backgroundColor = top15.map(p => rgba(TIER_COLOR[p.efficiency_tier]||TB.gray, 0.82));
  scorersChart.data.datasets[0].borderColor     = top15.map(p => TIER_COLOR[p.efficiency_tier]||TB.gray);
  scorersChart.options.scales.x.min   = getBarMin(top15.map(p=>p[stat]||0));
  scorersChart.options.scales.x.title.text = STAT_LONG[stat];
  scorersChart.update('active');
}}

// ── SCATTER CHART ──────────────────────────────────────────────────────────
const scatterLabelPlugin = {{
  id: 'scatterLabels',
  afterDatasetsDraw(chart) {{
    const ctx = chart.ctx;
    ctx.save();
    ctx.font = '700 11px Inter';
    ctx.textBaseline = 'middle';
    chart.data.datasets.forEach((ds, di) => {{
      chart.getDatasetMeta(di).data.forEach((pt, pi) => {{
        const d = ds.data[pi];
        if (d && d.ppg >= 20) {{
          const name = d.name.split(' ').slice(-1)[0];
          const x = pt.x + d.r + 4;
          const y = pt.y;
          ctx.lineWidth = 3;
          ctx.strokeStyle = 'rgba(255,255,255,0.9)';
          ctx.lineJoin = 'round';
          ctx.strokeText(name, x, y);
          ctx.fillStyle = '#1C1C1C';
          ctx.fillText(name, x, y);
        }}
      }});
    }});
    ctx.restore();
  }}
}};

function buildScatterDatasets(filtered) {{
  const grouped = {{}};
  filtered.forEach(p => {{
    if (!grouped[p.efficiency_tier]) grouped[p.efficiency_tier] = [];
    grouped[p.efficiency_tier].push(p);
  }});
  return TIER_ORDER.filter(t => grouped[t]).map(tier => ({{
    label: tier.replace(' Efficiency',''),
    data: grouped[tier].map(p => ({{
      x: p.usage_rate_per_game, y: p.ts_pct,
      r: Math.max(4, p.points_per_game * 0.52),
      name: p.player_name, ppg: p.points_per_game,
    }})),
    backgroundColor: rgba(TIER_COLOR[tier], 0.65),
    borderColor: rgba(TIER_COLOR[tier], 0.9),
    borderWidth: 1,
  }}));
}}

function initScatterChart(filtered) {{
  const ctx = document.getElementById('scatterChart').getContext('2d');
  scatterChart = new Chart(ctx, {{
    type: 'bubble',
    data: {{ datasets: buildScatterDatasets(filtered) }},
    plugins: [scatterLabelPlugin],
    options: {{
      responsive: true, maintainAspectRatio: true,
      animation: {{ duration: 400 }},
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          ...TT,
          callbacks: {{
            title: i => i[0].raw.name,
            label: i => [
              ` PPG: ${{i.raw.ppg}}`,
              ` TS%: ${{i.raw.y}}%`,
              ` Usage: ${{i.raw.x}}/g`,
            ]
          }}
        }}
      }},
      scales: {{
        x: {{ ...xAx('Usage Rate Per Game'), min:5, max:38, ticks:{{color:'#767676',font:{{size:10}}}} }},
        y: {{ ...yAx('True Shooting %'), min:38, max:80,
              ticks:{{ callback: v => v+'%', color:'#767676', font:{{size:10}} }} }},
      }}
    }}
  }});

  const el = document.getElementById('scatterLegend');
  el.innerHTML = '';
  TIER_ORDER.forEach(t => {{
    el.innerHTML += `<div class="legend-item">
      <div class="legend-dot" style="background:${{TIER_COLOR[t]}}"></div>
      ${{t.replace(' Efficiency','')}}
    </div>`;
  }});
}}

function updateScatterChart(filtered) {{
  if (!scatterChart) return;
  scatterChart.data.datasets = buildScatterDatasets(filtered);
  scatterChart.update('active');
}}

// ── STATS TABLE ────────────────────────────────────────────────────────────
function highlight(text, search) {{
  if (!search) return text;
  const re = new RegExp(`(${{search.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&')}})`, 'gi');
  return text.replace(re, '<mark>$1</mark>');
}}

const TABLE_COLS = [
  {{ key: '#',                    label: '#',    sortKey: null }},
  {{ key: 'player_name',          label: 'Player', sortKey: 'player_name' }},
  {{ key: 'team_abbreviation',    label: 'Team', sortKey: null }},
  {{ key: 'primary_position',     label: 'Pos',  sortKey: null }},
  {{ key: 'games_played',         label: 'GP',   sortKey: 'games_played' }},
  {{ key: 'points_per_game',      label: 'PPG',  sortKey: 'points_per_game' }},
  {{ key: 'rebounds_per_game',    label: 'RPG',  sortKey: 'rebounds_per_game' }},
  {{ key: 'assists_per_game',     label: 'APG',  sortKey: 'assists_per_game' }},
  {{ key: 'steals_per_game',      label: 'SPG',  sortKey: 'steals_per_game' }},
  {{ key: 'blocks_per_game',      label: 'BPG',  sortKey: 'blocks_per_game' }},
  {{ key: 'ts_pct',               label: 'TS%',  sortKey: 'ts_pct' }},
  {{ key: 'efficiency_tier',      label: 'Tier', sortKey: null }},
]

function renderTable(sorted, search) {{
  const wrap = document.getElementById('tableWrap');
  if (!sorted.length) {{
    wrap.innerHTML = '<div class="no-results">No players match the current filters.</div>';
    return;
  }}

  const headCells = TABLE_COLS.map(c => {{
    let cls = '';
    if (c.sortKey === sortCol) cls = sortDir === 'desc' ? 'sort-desc' : 'sort-asc';
    const ptr = c.sortKey ? 'style="cursor:pointer"' : '';
    return `<th class="${{cls}}" data-key="${{c.sortKey||''}}" ${{ptr}}>${{c.label}}</th>`;
  }}).join('');

  const bodyRows = sorted.map((p, i) => {{
    const rankCls = i < 3 ? 'rank gold' : 'rank';
    const tierCls = TIER_CLASS[p.efficiency_tier] || 'tier-avg';
    const tierShort = TIER_SHORT[p.efficiency_tier] || p.efficiency_tier;
    const name = highlight(p.player_name, search);
    const statVal = p[activeStat] ?? '—';
    return `<tr>
      <td><span class="${{rankCls}}">${{i+1}}</span></td>
      <td><span class="pname">${{name}}</span></td>
      <td>${{p.team_abbreviation}}</td>
      <td>${{p.primary_position||'—'}}</td>
      <td>${{p.games_played}}</td>
      <td><span class="${{sortCol==='points_per_game'?'stat-hi':''}}">${{p.points_per_game}}</span></td>
      <td><span class="${{sortCol==='rebounds_per_game'?'stat-hi':''}}">${{p.rebounds_per_game}}</span></td>
      <td><span class="${{sortCol==='assists_per_game'?'stat-hi':''}}">${{p.assists_per_game}}</span></td>
      <td><span class="${{sortCol==='steals_per_game'?'stat-hi':''}}">${{p.steals_per_game}}</span></td>
      <td><span class="${{sortCol==='blocks_per_game'?'stat-hi':''}}">${{p.blocks_per_game}}</span></td>
      <td>${{p.ts_pct}}%</td>
      <td><span class="tier-pill ${{tierCls}}">${{tierShort}}</span></td>
    </tr>`;
  }}).join('');

  wrap.innerHTML = `<table class="stats-table">
    <thead><tr>${{headCells}}</tr></thead>
    <tbody>${{bodyRows}}</tbody>
  </table>`;

  // Column sort listeners
  wrap.querySelectorAll('th[data-key]').forEach(th => {{
    if (!th.dataset.key) return;
    th.addEventListener('click', () => {{
      const key = th.dataset.key;
      if (sortCol === key) sortDir = sortDir === 'desc' ? 'asc' : 'desc';
      else {{ sortCol = key; sortDir = 'desc'; }}
      updateAll();
    }});
  }});
}}

// ── MAIN UPDATE ────────────────────────────────────────────────────────────
function updateAll() {{
  const f       = getFilters();
  const filtered = applyFilters(f);
  const sorted   = sortData(filtered, sortCol, sortDir);
  const byStat   = sortData(filtered, f.stat, 'desc');
  const top15    = byStat.slice(0, 15);

  // Labels
  const season = f.season;
  document.getElementById('leadersTitle').textContent =
    `Top 15 by ${{STAT_LONG[f.stat]}}`;
  ['leadersTag','scatterTag','tableTag'].forEach(id =>
    document.getElementById(id).textContent = season);
  document.getElementById('tableTitle').textContent =
    `${{season}} Season Stats \u00b7 Top 20 of ${{filtered.length}} Players`;

  // Filter count
  document.getElementById('filterResults').innerHTML =
    `<strong>${{filtered.length}}</strong> players shown`;

  updateKPIs(byStat, f);
  updateScorersChart(top15, f.stat);
  updateScatterChart(filtered);
  renderTable(sorted.slice(0, 20), f.search);
}}

// ── EVENT LISTENERS ────────────────────────────────────────────────────────
document.getElementById('seasonSelect').addEventListener('change', updateAll);
document.getElementById('playerSearch').addEventListener('input',  updateAll);

document.getElementById('minGames').addEventListener('input', function() {{
  document.getElementById('minGamesVal').textContent = this.value;
  updateAll();
}});

document.getElementById('statToggle').addEventListener('click', e => {{
  const btn = e.target.closest('button');
  if (!btn) return;
  activeStat = btn.dataset.stat;
  sortCol    = activeStat;
  sortDir    = 'desc';
  document.querySelectorAll('#statToggle button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  updateAll();
}});

document.getElementById('posFilter').addEventListener('click', e => {{
  const btn = e.target.closest('button');
  if (!btn) return;
  activePos = btn.dataset.pos;
  document.querySelectorAll('#posFilter button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  updateAll();
}});

document.getElementById('clearBtn').addEventListener('click', () => {{
  document.getElementById('seasonSelect').value = document.getElementById('seasonSelect').options[0].value;
  document.getElementById('minGames').value = 20;
  document.getElementById('minGamesVal').textContent = '20';
  document.getElementById('playerSearch').value = '';
  activeStat = 'points_per_game';
  activePos  = 'ALL';
  sortCol    = 'points_per_game';
  sortDir    = 'desc';
  document.querySelectorAll('#statToggle button').forEach((b,i) => b.classList.toggle('active', i===0));
  document.querySelectorAll('#posFilter button').forEach((b,i) => b.classList.toggle('active', i===0));
  updateAll();
}});

// ── STATIC CHARTS ──────────────────────────────────────────────────────────

// Scoring evolution
(function() {{
  const ctx = document.getElementById('scoringChart').getContext('2d');
  const years = DATA.league_trends.map(d => d.season_year);
  const ppg   = DATA.league_trends.map(d => d.avg_ppg);
  new Chart(ctx, {{
    type: 'line',
    data: {{ labels: years, datasets: [{{
      label:'League Avg PPG', data: ppg,
      borderColor: TB.blue, borderWidth: 2,
      backgroundColor: areaGrad(ctx, TB.blue, 360),
      fill: true, tension: 0.3, pointRadius: 0,
      pointHoverRadius: 4, pointHoverBackgroundColor: TB.blue,
      pointHoverBorderColor:'#fff', pointHoverBorderWidth:2,
    }}]}},
    options: {{
      responsive:true, maintainAspectRatio:true, animation:{{duration:900}},
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        legend:{{display:false}},
        tooltip:{{ ...TT, callbacks:{{
          title: i=>`${{i[0].label}}\u2013${{(+i[0].label+1).toString().slice(-2)}} Season`,
          label: i=>` Avg PPG: ${{i.raw}}`,
        }}}},
        annotation:{{ annotations:{{
          preBand:{{ type:'box', xMin:1949, xMax:1979,
            backgroundColor:rgba(TB.blue,0.04), borderWidth:0,
            label:{{content:'Pre-3PT Era',display:true,position:{{x:'start',y:'start'}},
              xAdjust:6,yAdjust:6,color:rgba(TB.blue,0.5),font:{{size:10,weight:'600'}},padding:0}} }},
          anaBand:{{ type:'box', xMin:2010, xMax:2025,
            backgroundColor:rgba('#E8651A',0.05), borderWidth:0,
            label:{{content:'Analytics Era',display:true,position:{{x:'start',y:'start'}},
              xAdjust:6,yAdjust:6,color:rgba('#E8651A',0.6),font:{{size:10,weight:'600'}},padding:0}} }},
          rule79:{{ type:'line', xMin:1979, xMax:1979,
            borderColor:rgba(TB.teal,0.6), borderWidth:1.5, borderDash:[5,4],
            label:{{content:'3PT Rule (1979)',display:true,position:'start',yAdjust:-14,
              color:rgba(TB.teal,0.85),font:{{size:10,weight:'600'}},backgroundColor:'transparent',padding:0}} }},
        }}}}
      }},
      scales:{{
        x:{{ ...xAx(), ticks:{{maxTicksLimit:10,color:'#767676',font:{{size:10}}}} }},
        y:{{ ...yAx('Avg PPG'), suggestedMin:5, suggestedMax:13 }},
      }}
    }}
  }});
}})();

// TS% trend
(function() {{
  const ctx = document.getElementById('tsChart').getContext('2d');
  const years = DATA.league_trends.map(d => d.season_year);
  const ts    = DATA.league_trends.map(d => Math.round(d.avg_ts_pct*1000)/10);
  new Chart(ctx, {{
    type:'line',
    data:{{ labels:years, datasets:[{{
      label:'Avg TS%', data:ts,
      borderColor:TB.green, borderWidth:2,
      backgroundColor:areaGrad(ctx,TB.green,200),
      fill:true, tension:0.3, pointRadius:0, pointHoverRadius:4,
    }}]}},
    options:{{
      responsive:true, maintainAspectRatio:true, animation:{{duration:900}},
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        legend:{{display:false}},
        tooltip:{{ ...TT, callbacks:{{
          title:i=>`${{i[0].label}} Season`,
          label:i=>` TS%: ${{i.raw}}%`,
        }}}},
      }},
      scales:{{
        x:{{ ...xAx(), ticks:{{maxTicksLimit:6,color:'#767676',font:{{size:10}}}} }},
        y:{{ ...yAx('TS%'), suggestedMin:38, suggestedMax:60,
          ticks:{{callback:v=>v+'%',color:'#767676',font:{{size:10}}}} }},
      }}
    }}
  }});
}})();

// Era table
(function() {{
  const ERA_COLORS = [TB.gray, TB.teal, TB.blue, '#E8651A'];
  const tbl = document.getElementById('eraTable');
  tbl.innerHTML = `
    <thead><tr><th>Era</th><th>Seasons</th><th>Avg PPG</th><th>Avg TS%</th><th>Avg 3PA/G</th></tr></thead>
    <tbody>${{DATA.era_summary.map((e,i)=>`
      <tr>
        <td><div class="era-name"><div class="era-pip" style="background:${{ERA_COLORS[i]}}"></div>${{e.era}}</div></td>
        <td>${{e.seasons}}</td>
        <td><span class="era-val">${{e.avg_ppg}}</span></td>
        <td><span class="era-val">${{e.avg_ts_pct}}%</span></td>
        <td><span class="era-val">${{e.avg_3pa}}</span></td>
      </tr>`).join('')}}
    </tbody>`;
}})();

// 3-point revolution
(function() {{
  const ctx = document.getElementById('threePtChart').getContext('2d');
  const years = DATA.league_trends.map(d => d.season_year);
  const pa3   = DATA.league_trends.map(d => d.avg_3pa_per_game);
  new Chart(ctx, {{
    type:'line',
    data:{{ labels:years, datasets:[{{
      label:'Avg 3PA/G', data:pa3,
      borderColor:TB.orange, borderWidth:2,
      backgroundColor:areaGrad(ctx,TB.orange,300),
      fill:true, tension:0.25, pointRadius:0,
      pointHoverRadius:4, pointHoverBackgroundColor:TB.orange,
      pointHoverBorderColor:'#fff', pointHoverBorderWidth:2,
    }}]}},
    options:{{
      responsive:true, maintainAspectRatio:true, animation:{{duration:900}},
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        legend:{{display:false}},
        tooltip:{{ ...TT, callbacks:{{
          title:i=>`${{i[0].label}} Season`,
          label:i=>` Avg 3PA/G: ${{i.raw}}`,
        }}}},
        annotation:{{ annotations:{{
          rule79:{{ type:'line', xMin:1979, xMax:1979,
            borderColor:rgba(TB.teal,0.7), borderWidth:1.5, borderDash:[5,4],
            label:{{content:'3-Point Rule (1979)',display:true,position:'start',yAdjust:-14,
              color:rgba(TB.teal,0.85),font:{{size:10,weight:'600'}},backgroundColor:'transparent',padding:0}} }},
          curry:{{ type:'line', xMin:2015, xMax:2015,
            borderColor:rgba(TB.purple,0.6), borderWidth:1.5, borderDash:[5,4],
            label:{{content:'Curry: 402 3s (2015)',display:true,position:'start',yAdjust:-14,
              color:rgba(TB.purple,0.8),font:{{size:10,weight:'600'}},backgroundColor:'transparent',padding:0}} }},
        }}}}
      }},
      scales:{{
        x:{{ ...xAx(), ticks:{{maxTicksLimit:10,color:'#767676',font:{{size:10}}}} }},
        y:{{ ...yAx('3PA Per Player Per Game'), min:0 }},
      }}
    }}
  }});
}})();

// Career leaders helper
function buildCareerChart(canvasId, players, statKey, statLabel, histColor) {{
  const ctx = document.getElementById(canvasId).getContext('2d');
  new Chart(ctx, {{
    type:'bar',
    data:{{ labels: players.map(p=>p.player_name),
      datasets:[{{
        label: statLabel,
        data: players.map(p=>p[statKey]),
        backgroundColor: players.map(p=>rgba(p.last_season_year>=2020?TB.orange:histColor,0.8)),
        borderColor:      players.map(p=>p.last_season_year>=2020?TB.orange:histColor),
        borderWidth:1, borderRadius:2, borderSkipped:false,
      }}]
    }},
    options:{{
      indexAxis:'y', responsive:true, maintainAspectRatio:false, animation:{{duration:900}},
      plugins:{{
        legend:{{display:false}},
        tooltip:{{ ...TT, callbacks:{{
          title: i=>players[i[0].dataIndex].player_name,
          label: i=>{{
            const p=players[i[0].dataIndex];
            return [
              ` ${{statLabel}}: ${{p[statKey]}}`,
              ` PPG: ${{p.career_ppg}}  RPG: ${{p.career_rpg}}  APG: ${{p.career_apg}}`,
              ` GP: ${{p.career_games_played}}  Seasons: ${{p.seasons_played}}`,
              ` TS%: ${{p.career_ts_pct}}%`,
              ` ${{p.first_season_year}}\u2013${{p.last_season_year}}`,
            ];
          }}
        }}}},
      }},
      scales:{{
        x:{{ ...xAx(statLabel), ticks:{{color:'#767676',font:{{size:10}}}} }},
        y:{{ ...yAx(), ticks:{{color:'#3D3D3D',font:{{size:11}}}} }},
      }}
    }}
  }});
}}

// Career PPG
buildCareerChart('careerChart',    DATA.career_leaders,     'career_ppg', 'Career PPG', TB.blue);
// Career RPG
buildCareerChart('careerRpgChart', DATA.career_rpg_leaders, 'career_rpg', 'Career RPG', TB.teal);
// Career APG
buildCareerChart('careerApgChart', DATA.career_apg_leaders, 'career_apg', 'Career APG', TB.green);

// ── INIT DYNAMIC SECTION ───────────────────────────────────────────────────
(function init() {{
  const f        = getFilters();
  const filtered  = applyFilters(f);
  const byStat   = sortData(filtered, f.stat, 'desc');
  const top15    = byStat.slice(0,15);

  initScorersChart(top15, f.stat);
  initScatterChart(filtered);

  const sorted = sortData(filtered, sortCol, sortDir);
  updateKPIs(byStat, f);
  renderTable(sorted.slice(0, 20), f.search);

  document.getElementById('filterResults').innerHTML =
    `<strong>${{filtered.length}}</strong> players shown`;
  ['leadersTag','scatterTag','tableTag'].forEach(id =>
    document.getElementById(id).textContent = f.season);
  document.getElementById('tableTitle').textContent =
    `${{f.season}} Season Stats \u2014 Top 20 of ${{filtered.length}} Players`;
}})();
</script>
</body>
</html>"""


if __name__ == '__main__':
    main()
