{{
    config(
        materialized='table'
    )
}}

WITH base AS (

    SELECT * FROM {{ ref('int_player_season_totals') }}
),

calculated_metrics AS (

    SELECT 
        -- Identifiers
        player_season_id,
        player_id,
        player_name,
        age,
        position,
        team_abbreviation,
        season,
        season_year,
        is_two_team_season_flag,
        
        -- Game statistics
        games_played,
        82 as total_games,
        games_started,
        total_minutes_played,
        
        -- Season totals
        total_points,
        total_rebounds,
        total_offensive_rebounds,
        total_defensive_rebounds,
        total_assists,
        total_steals,
        total_blocks,
        total_turnovers,
        total_personal_fouls,
        total_field_goals_made,
        total_field_goals_attempted,
        total_three_pointers_made,
        total_three_pointers_attempted,
        total_two_pointers_made,
        total_two_pointers_attempted,
        total_free_throws_made,
        total_free_throws_attempted,
        triple_doubles,
        
        -- Shooting percentages
        field_goal_percentage,
        three_point_percentage,
        two_point_percentage,
        free_throw_percentage,
        effective_field_goal_percentage,
        
        -- Per game averages (calculated from totals)
        ROUND(CAST(total_points AS NUMERIC) / NULLIF(games_played, 0), 1) AS points_per_game,
        ROUND(CAST(total_rebounds AS NUMERIC) / NULLIF(games_played, 0), 1) AS rebounds_per_game,
        ROUND(CAST(total_assists AS NUMERIC) / NULLIF(games_played, 0), 1) AS assists_per_game,
        ROUND(CAST(total_steals AS NUMERIC) / NULLIF(games_played, 0), 1) AS steals_per_game,
        ROUND(CAST(total_blocks AS NUMERIC) / NULLIF(games_played, 0), 1) AS blocks_per_game,
        ROUND(CAST(total_turnovers AS NUMERIC) / NULLIF(games_played, 0), 1) AS turnovers_per_game,
        ROUND(CAST(total_minutes_played AS NUMERIC) / NULLIF(games_played, 0), 1) AS minutes_per_game,
        
        -- Advanced metrics
        -- True Shooting Percentage: TS% = PTS / (2 * TSA) where TSA = FGA + 0.44 * FTA
        CASE 
            WHEN (total_field_goals_attempted + 0.44 * total_free_throws_attempted) > 0
            THEN ROUND(
                CAST(total_points AS NUMERIC) / 
                (2 * (total_field_goals_attempted + 0.44 * total_free_throws_attempted)),
                3
            )
            ELSE NULL 
        END AS true_shooting_percentage,
        
        -- Assist to Turnover Ratio
        CASE 
            WHEN total_turnovers > 0 
            THEN ROUND(CAST(total_assists AS NUMERIC) / total_turnovers, 2)
            ELSE NULL 
        END AS assist_to_turnover_ratio,
        
        -- Usage Rate (simplified): (FGA + 0.44 * FTA + TOV) / GP
        ROUND(
            (total_field_goals_attempted + 0.44 * total_free_throws_attempted + COALESCE(total_turnovers, 0)) / 
            NULLIF(games_played, 0),
            1
        ) AS usage_rate_per_game,
        
        -- Rebound Rate per game
        ROUND(CAST(total_rebounds AS NUMERIC) / NULLIF(total_minutes_played, 0) * 36, 1) AS rebounds_per_36_minutes,
        
        -- Assist Rate per game  
        ROUND(CAST(total_assists AS NUMERIC) / NULLIF(total_minutes_played, 0) * 36, 1) AS assists_per_36_minutes,
        
        -- Points per 36 minutes
        ROUND(CAST(total_points AS NUMERIC) / NULLIF(total_minutes_played, 0) * 36, 1) AS points_per_36_minutes,
        
        -- Offensive rating approximation (points per 100 possessions)
        ROUND(
            CAST(total_points AS NUMERIC) / 
            NULLIF(total_field_goals_attempted + 0.44 * total_free_throws_attempted + total_turnovers, 0) * 100,
            1
        ) AS offensive_rating,
        
        -- Games started percentage
        ROUND(CAST(games_started AS NUMERIC) / NULLIF(games_played, 0) * 100, 1) AS games_started_percentage,
        
        -- Fantasy points (common formula: PTS + 1.2*REB + 1.5*AST + 3*STL + 3*BLK - TOV)
        ROUND(
            total_points + 
            1.2 * total_rebounds + 
            1.5 * total_assists + 
            3 * total_steals + 
            3 * total_blocks - 
            COALESCE(total_turnovers, 0),
            1
        ) AS total_fantasy_points,
        
        awards,
        created_at

    FROM base
),

categorized AS (

    SELECT 
        *,
        
        -- Playing time category
        CASE 
            WHEN minutes_per_game >= 30 THEN 'Starter - High Minutes'
            WHEN minutes_per_game >= 24 THEN 'Starter - Regular Minutes'
            WHEN minutes_per_game >= 15 THEN 'Rotation Player'
            WHEN minutes_per_game >= 10 THEN 'Bench Player'
            ELSE 'Deep Bench'
        END AS playing_time_category,
        
        -- Scoring category
        CASE 
            WHEN points_per_game >= 25 THEN 'Elite Scorer'
            WHEN points_per_game >= 20 THEN 'High Scorer'
            WHEN points_per_game >= 15 THEN 'Above Average Scorer'
            WHEN points_per_game >= 10 THEN 'Role Player Scorer'
            ELSE 'Low Volume Scorer'
        END AS scoring_category,
        
        -- Position role
        CASE 
            WHEN position IN ('PG', 'SG') AND assists_per_game >= 5 THEN 'Primary Playmaker'
            WHEN position IN ('PG', 'SG') AND points_per_game >= 15 THEN 'Scoring Guard'
            WHEN position IN ('SF', 'PF') AND rebounds_per_game >= 7 THEN 'Forward Rebounder'
            WHEN position IN ('C', 'PF') AND blocks_per_game >= 1.5 THEN 'Rim Protector'
            WHEN position IN ('C') THEN 'Traditional Center'
            WHEN position IN ('SF', 'PF') THEN 'Wing Player'
            ELSE 'Role Player'
        END AS player_role,
        
        -- Efficiency tier
        CASE 
            WHEN true_shooting_percentage >= 0.600 THEN 'Elite Efficiency'
            WHEN true_shooting_percentage >= 0.550 THEN 'Above Average Efficiency'
            WHEN true_shooting_percentage >= 0.500 THEN 'Average Efficiency'
            WHEN true_shooting_percentage >= 0.450 THEN 'Below Average Efficiency'
            ELSE 'Poor Efficiency'
        END AS efficiency_tier,
        
        -- Three-point shooting category
        CASE 
            WHEN total_three_pointers_attempted >= games_played * 3 THEN
                CASE 
                    WHEN three_point_percentage >= 0.400 THEN 'Elite 3PT Shooter'
                    WHEN three_point_percentage >= 0.360 THEN 'Good 3PT Shooter'
                    WHEN three_point_percentage >= 0.330 THEN 'Average 3PT Shooter'
                    ELSE 'Poor 3PT Shooter'
                END
            WHEN total_three_pointers_attempted >= games_played THEN 'Occasional 3PT Shooter'
            ELSE 'Non 3PT Shooter'
        END AS three_point_shooting_category

    FROM calculated_metrics
)

SELECT * FROM categorized
