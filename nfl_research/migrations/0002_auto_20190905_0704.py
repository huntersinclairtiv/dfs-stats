# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2019-09-05 07:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('nfl_research', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('season_year', models.IntegerField()),
                ('week', models.IntegerField()),
                ('location_name', models.CharField(max_length=30, null=True)),
                ('game_date', models.DateTimeField(null=True)),
                ('home_score', models.IntegerField(default=0)),
                ('away_score', models.IntegerField(default=0)),
                ('game_ot', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=60)),
                ('short_name', models.CharField(max_length=60)),
                ('first_name', models.CharField(max_length=60)),
                ('last_name', models.CharField(max_length=60)),
                ('fantasy_position', models.CharField(max_length=3)),
                ('position', models.CharField(max_length=3)),
                ('created_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_updated_date', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='Player_Game_Stats',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('played', models.BooleanField(default=False)),
                ('started', models.BooleanField(default=False)),
                ('player_url_string', models.CharField(max_length=50, null=True)),
                ('passing_completions', models.IntegerField(default=0)),
                ('passing_attempts', models.IntegerField(default=0)),
                ('passing_completion_percentage', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('passing_yards', models.IntegerField(default=0)),
                ('passing_yards_per_attempt', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('passing_touchdowns', models.IntegerField(default=0)),
                ('passing_interceptions', models.IntegerField(default=0)),
                ('passing_rating', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('rushing_attempts', models.IntegerField(default=0)),
                ('rushing_yards', models.IntegerField(default=0)),
                ('rushing_yards_per_attempt', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('rushing_touchdowns', models.IntegerField(default=0)),
                ('receptions', models.IntegerField(default=0)),
                ('receiving_targets', models.IntegerField(default=0)),
                ('receiving_yards', models.IntegerField(default=0)),
                ('reception_percentage', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('receiving_touchdowns', models.IntegerField(default=0)),
                ('receiving_long', models.IntegerField(default=0)),
                ('receiving_yards_per_target', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('receiving_yards_per_reception', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fumbles', models.IntegerField(default=0)),
                ('fumbles_lost', models.IntegerField(default=0)),
                ('field_goals_made', models.IntegerField(default=0)),
                ('field_goals_attempted', models.IntegerField(default=0)),
                ('field_goal_percentage', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('field_goals_longest_made', models.IntegerField(default=0)),
                ('extra_points_made', models.IntegerField(default=0)),
                ('extra_points_attempted', models.IntegerField(default=0)),
                ('tackles_for_loss', models.IntegerField(default=0)),
                ('sacks', models.IntegerField(default=0)),
                ('quarterback_hits', models.IntegerField(default=0)),
                ('interceptions', models.IntegerField(default=0)),
                ('fumbles_recovered', models.IntegerField(default=0)),
                ('safeties', models.IntegerField(default=0)),
                ('defensive_touchdowns', models.IntegerField(default=0)),
                ('special_teams_touchdowns', models.IntegerField(default=0)),
                ('solo_tackles', models.IntegerField(default=0)),
                ('assisted_tackles', models.IntegerField(default=0)),
                ('sack_yards', models.IntegerField(default=0)),
                ('passes_defended', models.IntegerField(default=0)),
                ('fumbles_forced', models.IntegerField(default=0)),
                ('points_allowed_by_defense_special_teams', models.IntegerField(default=0)),
                ('total_tackles', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_ppr', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_fan_duel', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_yahoo', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_fantasy_draft', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_draft_kings', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_half_point_ppr', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_six_point_pass_td', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_per_game', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_per_game_ppr', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_per_game_fan_duel', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_per_game_yahoo', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_per_game_draft_kings', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_per_game_half_point_ppr', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_per_game_six_point_pass_td', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_points_per_game_fantasy_draft', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('rush_snap_percentage', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('target_snap_percentage', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('touch_snap_percentage', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('intended_touch_snap_percentage', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('tackle_snap_percentage', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('sack_snap_percentage', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('quarterback_hit_snap_percentage', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_point_snap_percentage', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_point_snap_percentage_ppr', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_point_snap_percentage_fan_duel', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_point_snap_percentage_yahoo', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_point_snap_percentage_draft_kings', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_point_snap_percentage_half_point_ppr', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_point_snap_percentage_six_point_pass_td', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('fantasy_point_snap_percentage_fantasy_draft', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('snaps_per_game', models.IntegerField(default=0)),
                ('snaps_played', models.IntegerField(default=0)),
                ('snaps_played_percentage', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='player_game_stats_player', to='nfl_research.Player')),
            ],
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('initials', models.CharField(max_length=3, unique=True)),
                ('all_names', models.CharField(max_length=40)),
                ('full_name', models.CharField(max_length=50, null=True)),
                ('city_name', models.CharField(max_length=20, null=True)),
                ('mascot_name', models.CharField(max_length=20, null=True)),
                ('conference', models.CharField(choices=[('AFC', 'American Football Conference'), ('NFC', 'National Football Conference')], max_length=3, null=True)),
                ('division', models.CharField(choices=[('AFC North', 'AFC North'), ('AFC East', 'AFC East'), ('AFC South', 'AFC South'), ('AFC West', 'AFC West'), ('NFC North', 'NFC North'), ('NFC East', 'NFC East'), ('NFC South', 'NFC South'), ('NFC West', 'NFC West')], max_length=10, null=True)),
                ('team_url_string', models.CharField(max_length=50, null=True)),
                ('created_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_updated_date', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='Team_Game_Map',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('team_is_home', models.BooleanField(default=False)),
                ('score_summary', models.CharField(max_length=30, null=True)),
                ('game_result', models.CharField(choices=[('W', 'Win'), ('L', 'Loss'), ('T', 'Tie')], max_length=1, null=True)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_game_map_game', to='nfl_research.Game')),
                ('opponent', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='team_game_map_opponent', to='nfl_research.Team')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='team_game_map_team', to='nfl_research.Team')),
            ],
        ),
        migrations.DeleteModel(
            name='Keyphrase',
        ),
        migrations.AddField(
            model_name='player_game_stats',
            name='team_game',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='player_game_stats_team_game_map', to='nfl_research.Team_Game_Map'),
        ),
        migrations.AddField(
            model_name='player',
            name='team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='player_team', to='nfl_research.Team'),
        ),
        migrations.AddField(
            model_name='game',
            name='away_team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='game_away_team', to='nfl_research.Team'),
        ),
        migrations.AddField(
            model_name='game',
            name='home_team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='game_home_team', to='nfl_research.Team'),
        ),
    ]