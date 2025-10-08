{{
    config(
        materialized='view'
    )
}}

SELECT
    -- Primary key
    id AS player_season_id,

    -- Player information
    player AS player_name,
    age,
    pos AS position,

    -- Team information
    team AS team_abbreviation,
    season,
    CAST(LEFT(season, 4) AS INT) AS season_year,

    -- Game statistics
    g AS games_played,
    gs AS games_started,
    mp AS minutes_played,

    -- Shooting statistics
    fg AS field_goals_made,
    fga AS field_goals_attempted,
    fg_pct AS field_goal_percentage,

    three_p AS three_pointers_made,
    three_pa AS three_pointers_attempted,
    three_p_pct AS three_point_percentage,

    two_p AS two_pointers_made,
    two_pa AS two_pointers_attempted,
    two_p_pct AS two_point_percentage,

    efg_pct AS effective_field_goal_percentage,

    -- Free throw statistics
    ft AS free_throws_made,
    fta AS free_throws_attempted,
    ft_pct AS free_throw_percentage,

    -- Rebounds
    orb AS offensive_rebounds,
    drb AS defensive_rebounds,
    trb AS total_rebounds,

    -- Other statistics
    ast AS assists,
    stl AS steals,
    blk AS blocks,
    tov AS turnovers,
    pf AS personal_fouls,
    pts AS points,

    -- Additional information
    awards,
    created_at

FROM {{ source('nba', 'player_season_averages') }}
