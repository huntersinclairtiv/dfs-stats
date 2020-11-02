import sys
import logging
import json
from django.db import models
from django.utils import timezone
from datetime import datetime
from nfl_research.utilities import NFL_Utilities
from rest_framework import serializers

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
# logging.debug('A debug message!')
'''
class FlattenMixin(object):
    """Flatens the specified related objects in this representation"""
    def to_representation(self, obj):
        assert hasattr(self.Meta, 'flatten'), (
            'Class {serializer_class} missing "Meta.flatten" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        # Get the current object representation
        rep = super(FlattenMixin, self).to_representation(obj)
        # Iterate the specified related objects with their serializer
        for field, serializer_class in self.Meta.flatten:
            serializer = serializer_class(context = self.context)
            objrep = serializer.to_representation(getattr(obj, field))
            #Include their fields, prefixed, in the current   representation
            for key in objrep:
                rep[field + "__" + key] = objrep[key]
        return rep
        
class MembershipSerializer(FlattenMixin, serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Player_Game_Stats
        fields = ('id', 'url', 'group', 'date_joined', 'invite_reason')
        flatten = [ ('person', PersonSerializer) ]
'''
class PlayerStatManager(models.Manager):
  def create_with_json(self, jsonStatsText, jsonSnapsText, seasonType):
    jsonFull = {}
    try :
      #jsonFull = json.loads(jsonStatsText, object_hook=NFL_Utilities.parseMyJSONDates)
      jsonFull = json.loads(jsonStatsText, object_hook=NFL_Utilities.parseMyJSONDates)
    except:
      logging.debug('error parsing json stats text: ' + str(jsonStatsText))
      return
    
    data_array = jsonFull.get('Data', [])
    if (len(data_array) <= 0):
      return
    else :
      for j in data_array:
        if (j['IsGameOver'] == False or 
            j['Opponent'] is None or 
            j['Team'] is None or 
            j['PlayerID'] is None or 
            j['Season'] is None or 
            j['Week'] is None or 
            j['Played'] is None or 
            j['Name'] is None or 
            j['FirstName'] is None or 
            j['LastName'] is None or 
            j['FantasyPosition'] is None or 
            j['Position'] is None) :
          return
        else:
          #logging.debug('TEAM: ' + str(j['Team']))
          #logging.debug('PlayerID: ' + str(j.get('PlayerID',-1)) + ' Season: ' + str(j.get('Season',-1)) + ' Week: ' + str(j.get('Week',-1)))
          team_ref, team_created = Team.objects.update_or_create(
              initials=j['Team'].upper(),
              defaults={
                'all_names': j['Team'],
                'team_url_string': j['TeamUrlString'],
              }
          )
          if (team_ref.team_url_string == None):
            team_ref.team_url_string = j['TeamUrlString']
            team_ref.save()
    
          #all_names__icontains=j['Opponent'],
          opponent_ref, opponent_created = Team.objects.update_or_create(
              initials=j['Opponent'].upper(),
              defaults={
                'all_names': j['Opponent'],
              }
          )

          home_team_ref = team_ref
          away_team_ref = opponent_ref
          if (j['TeamIsHome'] == False):
            home_team_ref = opponent_ref
            away_team_ref = team_ref


          player_ref, player_created = Player.objects.get_or_create(
              id=j['PlayerID'],
              defaults={
                'name': j['Name'],
                'short_name': j['ShortName'],
                'first_name': j['FirstName'],
                'last_name': j['LastName'],
                'fantasy_position': j['FantasyPosition'],
                'position': j['Position'],
                'team': team_ref,
              }
          )

          overtime = False
          if (j['QuarterDisplay'] is not None):
            if ("OT" in str(j['QuarterDisplay']).lower()):
              overtime = True

          game_ref, game_created = Game.objects.get_or_create(
              home_team=home_team_ref,
              away_team=away_team_ref,
              season_type=seasonType,
              season_year=j['Season'],
              week=j['Week'],
              defaults={
                'game_date': NFL_Utilities.convertJSONDate(j['GameDate']),
                'home_score': j['HomeScore'],
                'away_score': j['AwayScore'],
                'game_ot': overtime,
              }
          )

          team_game_map_ref, team_game_map_created = Team_Game_Map.objects.get_or_create(
              team=team_ref,
              opponent=opponent_ref,
              game=game_ref,
              defaults={
                'team_is_home': j['TeamIsHome'],
                'score_summary': j['ScoreSummary'],
                'game_result': j['Result'],
              }
          )

          player_stats, player_stats_created = super(PlayerStatManager, self).get_or_create(
            player=player_ref,
            team_game=team_game_map_ref,
            defaults={
              'played': j.get('Played', False),
              'started': j.get('Started', False),
              'player_url_string': j.get('PlayerUrlString', ''),
              'passing_completions': j.get('PassingCompletions', 0) or 0,
              'passing_attempts': j.get('PassingAttempts', 0) or 0,
              'passing_completion_percentage': j.get('PassingCompletionPercentage', 0) or 0,
              'passing_yards': j.get('PassingYards', 0) or 0,
              'passing_yards_per_attempt': j.get('PassingYardsPerAttempt', 0) or 0,
              'passing_touchdowns': j.get('PassingTouchdowns', 0) or 0,
              'passing_interceptions': j.get('PassingInterceptions', 0) or 0,
              'passing_rating': j.get('PassingRating', 0) or 0,
              'rushing_attempts': j.get('RushingAttempts', 0) or 0,
              'rushing_yards': j.get('RushingYards', 0) or 0,
              'rushing_yards_per_attempt': j.get('RushingYardsPerAttempt', 0) or 0,
              'rushing_touchdowns': j.get('RushingTouchdowns', 0) or 0,
              'receptions': j.get('Receptions', 0) or 0,
              'receiving_targets': j.get('ReceivingTargets', 0) or 0,
              'receiving_yards': j.get('ReceivingYards', 0) or 0,
              'reception_percentage': j.get('ReceptionPercentage', 0) or 0,
              'receiving_touchdowns': j.get('ReceivingTouchdowns', 0) or 0,
              'receiving_long': j.get('ReceivingLong', 0) or 0,
              'receiving_yards_per_target': j.get('ReceivingYardsPerTarget', 0) or 0,
              'receiving_yards_per_reception': j.get('ReceivingYardsPerReception', 0) or 0,
              'fumbles': j.get('Fumbles', 0) or 0,
              'fumbles_lost': j.get('FumblesLost', 0) or 0,
              'field_goals_made': j.get('FieldGoalsMade', 0) or 0,
              'field_goals_attempted': j.get('FieldGoalsAttempted', 0) or 0,
              'field_goal_percentage': j.get('FieldGoalPercentage', 0) or 0,
              'field_goals_longest_made': j.get('FieldGoalsLongestMade', 0) or 0,
              'extra_points_made': j.get('ExtraPointsMade', 0) or 0,
              'extra_points_attempted': j.get('ExtraPointsAttempted', 0) or 0,
              'tackles_for_loss': j.get('TacklesForLoss', 0) or 0,
              'sacks': j.get('Sacks', 0) or 0,
              'quarterback_hits': j.get('QuarterbackHits', 0) or 0,
              'interceptions': j.get('Interceptions', 0) or 0,
              'fumbles_recovered': j.get('FumblesRecovered', 0) or 0,
              'safeties': j.get('Safeties', 0) or 0,
              'defensive_touchdowns': j.get('DefensiveTouchdowns', 0) or 0,
              'special_teams_touchdowns': j.get('SpecialTeamsTouchdowns', 0) or 0,
              'solo_tackles': j.get('SoloTackles', 0) or 0,
              'assisted_tackles': j.get('AssistedTackles', 0) or 0,
              'sack_yards': j.get('SackYards', 0) or 0,
              'passes_defended': j.get('PassesDefended', 0) or 0,
              'fumbles_forced': j.get('FumblesForced', 0) or 0,
              'points_allowed_by_defense_special_teams': j.get('PointsAllowedByDefenseSpecialTeams', 0) or 0,
              'total_tackles': j.get('TotalTackles', 0) or 0,
              'fantasy_points': j.get('FantasyPoints', 0) or 0,
              'fantasy_points_ppr': j.get('FantasyPointsPPR', 0) or 0,
              'fantasy_points_fan_duel': j.get('FantasyPointsFanDuel', 0) or 0,
              'fantasy_points_yahoo': j.get('FantasyPointsYahoo', 0) or 0,
              'fantasy_points_fantasy_draft': j.get('FantasyPointsFantasyDraft', 0) or 0,
              'fantasy_points_draft_kings': j.get('FantasyPointsDraftKings', 0) or 0,
              'fantasy_points_half_point_ppr': j.get('FantasyPointsHalfPointPpr', 0) or 0,
              'fantasy_points_six_point_pass_td': j.get('FantasyPointsSixPointPassTd', 0) or 0,
              'fantasy_points_per_game': j.get('FantasyPointsPerGame', 0) or 0,
              'fantasy_points_per_game_ppr': j.get('FantasyPointsPerGamePPR', 0) or 0,
              'fantasy_points_per_game_fan_duel': j.get('FantasyPointsPerGameFanDuel', 0) or 0,
              'fantasy_points_per_game_yahoo': j.get('FantasyPointsPerGameYahoo', 0) or 0,
              'fantasy_points_per_game_draft_kings': j.get('FantasyPointsPerGameDraftKings', 0) or 0,
              'fantasy_points_per_game_half_point_ppr': j.get('FantasyPointsPerGameHalfPointPPR', 0) or 0,
              'fantasy_points_per_game_six_point_pass_td': j.get('FantasyPointsPerGameSixPointPassTd', 0) or 0,
              'fantasy_points_per_game_fantasy_draft': j.get('FantasyPointsPerGameFantasyDraft', 0) or 0,
            }
          )
        #END ELSE - game is not over
      #END FOR LOOP OF PLAYERS
    #END ELSE data_array len

    jsonSnapsFull = {}
    try :
      jsonSnapsFull = json.loads(jsonSnapsText)
    except:
      logging.debug('error parsing json snaps text: ' + str(jsonSnapsText))

    snaps_array = jsonSnapsFull.get('Data', [])
    if (len(snaps_array) <= 0):
      return
    else :
      for js in snaps_array:
        #logging.debug('Opponent: ' + str(js.get('Opponent',-1)))
        #logging.debug('Team: ' + str(js.get('Team',-1)))
        #logging.debug('PlayerID: ' + str(js.get('PlayerID',-1)))
        #logging.debug('Season: ' + str(js.get('Season',-1)))
        #logging.debug('Week: ' + str(js.get('Week',-1)))
        #logging.debug('SnapsPerGame: ' + str(js.get('SnapsPerGame',-1)))
        if (js['Opponent'] is not None and js['Team'] is not None and js['PlayerID'] is not None and js['Season'] is not None and js['Week'] is not None and j['Position'] is not None and js.get('SnapsPerGame',-1) >= 0) :
          team_ref, team_created = Team.objects.update_or_create(
              initials=js['Team'].upper(),
              defaults={
                'all_names': js['Team'],
                'team_url_string': js['TeamUrlString'],
              }
          )

          opponent_ref, opponent_created = Team.objects.update_or_create(
              initials=js['Opponent'].upper(),
              defaults={
                'all_names': js['Opponent'],
              }
          )

          player_ref, player_created = Player.objects.get_or_create(
              id=js['PlayerID'],
              defaults={
                'name': js['Name'],
                'short_name': js['ShortName'],
                'first_name': js['FirstName'],
                'last_name': js['LastName'],
                'fantasy_position': js['FantasyPosition'],
                'position': js['Position'],
                'team': team_ref,
              }
          )

          game_ref = Game.objects.filter(
              home_team=team_ref,
              away_team=opponent_ref,
              season_type=seasonType,
              season_year=js['Season'],
              week=js['Week']
          )
          if (game_ref is None or len(game_ref) <= 0) :
            game_ref = Game.objects.filter(
                home_team=opponent_ref,
                away_team=team_ref,
                season_type=seasonType,
                season_year=js['Season'],
                week=js['Week']
            )

          if (game_ref is not None and len(game_ref) == 1) :

            team_game_map_ref = Team_Game_Map.objects.filter(
                team=team_ref,
                opponent=opponent_ref,
                game=game_ref[0]
            )
            #logging.debug('PlayerID: ' + str(js.get('PlayerID',-1)) + ' Season: ' + str(js.get('Season',-1)) + ' Week: ' + str(js.get('Week',-1)) + ' SnapPerc: ' + str(js.get('SnapsPlayedPercentage', 0)))

            if (team_game_map_ref is not None and len(team_game_map_ref) == 1) :
              player_stats, player_stats_created = super(PlayerStatManager, self).update_or_create(
                player=player_ref,
                team_game=team_game_map_ref[0],
                defaults={
                  'played': js.get('Played', False),
                  'started': js.get('Started', False),
                  'rush_snap_percentage': js.get('RushSnapPercentage', 0) or 0,
                  'target_snap_percentage': js.get('TargetSnapPercentage', 0) or 0,
                  'touch_snap_percentage': js.get('TouchSnapPercentage', 0) or 0,
                  'intended_touch_snap_percentage': js.get('IntendedTouchSnapPercentage', 0) or 0,
                  'tackle_snap_percentage': js.get('TackleSnapPercentage', 0) or 0,
                  'sack_snap_percentage': js.get('SackSnapPercentage', 0) or 0,
                  'quarterback_hit_snap_percentage': js.get('QuarterbackHitSnapPercentage', 0) or 0,
                  'fantasy_point_snap_percentage': js.get('FantasyPointSnapPercentage', 0) or 0,
                  'fantasy_point_snap_percentage_ppr': js.get('FantasyPointSnapPercentagePPR', 0) or 0,
                  'fantasy_point_snap_percentage_fan_duel': js.get('FantasyPointSnapPercentageFanDuel', 0) or 0,
                  'fantasy_point_snap_percentage_yahoo': js.get('FantasyPointSnapPercentageYahoo', 0) or 0,
                  'fantasy_point_snap_percentage_draft_kings': js.get('FantasyPointSnapPercentageDraftKings', 0) or 0,
                  'fantasy_point_snap_percentage_half_point_ppr': js.get('FantasyPointSnapPercentageHalfPointPPR', 0) or 0,
                  'fantasy_point_snap_percentage_six_point_pass_td': js.get('FantasyPointSnapPercentageSixPointPassTd', 0) or 0,
                  'fantasy_point_snap_percentage_fantasy_draft': js.get('FantasyPointSnapPercentageFantasyDraft', 0) or 0,
                  'snaps_per_game': js.get('SnapsPerGame', 0) or 0,
                  'snaps_played': js.get('SnapsPlayed', 0) or 0,
                  'snaps_played_percentage': js.get('SnapsPlayedPercentage', 0) or 0,
                }
              )
              if (player_stats_created == True) :
                logging.debug('Error - No record exists with stats for :  ' + str(js['Name']) + ' : ' + str(js['PlayerID']) + ' : season-' + str(js['Season']) + ' : week-' + str(js['Week']) + ' PlayerID created:' + str(player_stats.id) )
            #end if team_game_map_ref is not None
          #end if game_ref is not None
        #end if require values are not none
      #END FOR LOOP OF PLAYERS
    #END ELSE snaps_array len
    return player_stats
  #END create_with_json
#END PlayerStatManager
'''
    def with_counts(self):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.id, p.question, p.poll_date, COUNT(*)
                FROM polls_opinionpoll p, polls_response r
                WHERE p.id = r.poll_id
                GROUP BY p.id, p.question, p.poll_date
                ORDER BY p.poll_date DESC""")
            result_list = []
            for row in cursor.fetchall():
                p = self.model(id=row[0], question=row[1], poll_date=row[2])
                p.num_responses = row[3]
                result_list.append(p)
        return result_list
'''

class Team(models.Model):
  CONFERENCES = (
      ('AFC', 'American Football Conference'),
      ('NFC', 'National Football Conference'),
  )
  DIVISIONS = (
      ('AFC North', 'AFC North'),
      ('AFC East', 'AFC East'),
      ('AFC South', 'AFC South'),
      ('AFC West', 'AFC West'),
      ('NFC North', 'NFC North'),
      ('NFC East', 'NFC East'),
      ('NFC South', 'NFC South'),
      ('NFC West', 'NFC West'),
  )
  id = models.AutoField(primary_key=True)
  initials = models.CharField(max_length=3, unique=True)
  all_names = models.CharField(max_length=40, null=True) #'SD,LAC' etc.
  full_name = models.CharField(max_length=50, null=True)
  city_name = models.CharField(max_length=20, null=True)
  mascot_name = models.CharField(max_length=20, null=True)
  conference = models.CharField(max_length=3, choices=CONFERENCES, null=True)
  division = models.CharField(max_length=10, choices=DIVISIONS, null=True)
  team_url_string = models.CharField(max_length=50, null=True)
  created_date = models.DateTimeField(default=timezone.now)
  last_updated_date = models.DateTimeField(default=timezone.now)

  '''
  def publish(self):
    self.save()

  def __str__(self):
    return self.phrase
  '''
# Create your models here.
class Player(models.Model):
  id = models.IntegerField(primary_key=True)
  name = models.CharField(max_length=60)
  short_name = models.CharField(max_length=60, null=True)
  first_name = models.CharField(max_length=60)
  last_name = models.CharField(max_length=60)
  fantasy_position = models.CharField(max_length=3, null=True)
  position = models.CharField(max_length=3, null=True)
  created_date = models.DateTimeField(default=timezone.now)
  last_updated_date = models.DateTimeField(default=timezone.now)
  team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='player_team')
  #team = models.CharField(max_length=3)

class Game(models.Model):
  home_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='game_home_team')
  away_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='game_away_team')
  season_year = models.IntegerField()
  week = models.IntegerField()
  season_type = models.CharField(max_length=4, default="REG", null=True)
  location_name = models.CharField(max_length=30, null=True)
  game_date = models.DateTimeField(null=True)
  home_score = models.IntegerField(null=True)
  away_score = models.IntegerField(null=True)
  game_ot = models.BooleanField(default=False)

class Team_Game_Map(models.Model):
  GAME_RESULTS = (
      ('W', 'Win'),
      ('L', 'Loss'),
      ('T', 'Tie'),
  )
  team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='team_game_map_team')
  opponent = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='team_game_map_opponent')
  game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='team_game_map_game')
  team_is_home = models.BooleanField(default=False)
  score_summary = models.CharField(max_length=30, null=True)
  game_result = models.CharField(max_length=1, choices=GAME_RESULTS, null=True)


class Player_Game_Stats(models.Model):
  player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='player_game_stats_player')
  team_game = models.ForeignKey(Team_Game_Map, on_delete=models.CASCADE, related_name='player_game_stats_team_game_map')
  played = models.BooleanField(default=False)
  started = models.BooleanField(default=False)
  player_url_string = models.CharField(max_length=50, null=True)
  #PASSING
  passing_completions = models.IntegerField(default=0, null=True)
  passing_attempts = models.IntegerField(default=0, null=True)
  passing_completion_percentage = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  passing_yards = models.IntegerField(default=0, null=True)
  passing_yards_per_attempt = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  passing_touchdowns = models.IntegerField(default=0, null=True)
  passing_interceptions = models.IntegerField(default=0, null=True)
  passing_rating = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  #RUSHING
  rushing_attempts = models.IntegerField(default=0, null=True)
  rushing_yards = models.IntegerField(default=0, null=True)
  rushing_yards_per_attempt = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  rushing_touchdowns = models.IntegerField(default=0, null=True)
  #RECEIVING
  receptions = models.IntegerField(default=0, null=True)
  receiving_targets = models.IntegerField(default=0, null=True)
  receiving_yards = models.IntegerField(default=0, null=True)
  reception_percentage = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  receiving_touchdowns = models.IntegerField(default=0, null=True)
  receiving_long = models.IntegerField(default=0, null=True)
  receiving_yards_per_target = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  receiving_yards_per_reception = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  #FUMBLES
  fumbles = models.IntegerField(default=0, null=True)
  fumbles_lost = models.IntegerField(default=0, null=True)
  #KICKER
  field_goals_made = models.IntegerField(default=0, null=True)
  field_goals_attempted = models.IntegerField(default=0, null=True)
  field_goal_percentage = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  field_goals_longest_made = models.IntegerField(default=0, null=True)
  extra_points_made = models.IntegerField(default=0, null=True)
  extra_points_attempted = models.IntegerField(default=0, null=True)
  #DEFENSE
  tackles_for_loss = models.IntegerField(default=0, null=True)
  sacks = models.IntegerField(default=0, null=True)
  quarterback_hits = models.IntegerField(default=0, null=True)
  interceptions = models.IntegerField(default=0, null=True)
  fumbles_recovered = models.IntegerField(default=0, null=True)
  safeties = models.IntegerField(default=0, null=True)
  defensive_touchdowns = models.IntegerField(default=0, null=True)
  special_teams_touchdowns = models.IntegerField(default=0, null=True)
  solo_tackles = models.IntegerField(default=0, null=True)
  assisted_tackles = models.IntegerField(default=0, null=True)
  sack_yards = models.IntegerField(default=0, null=True)
  passes_defended = models.IntegerField(default=0, null=True)
  fumbles_forced = models.IntegerField(default=0, null=True)
  points_allowed_by_defense_special_teams = models.IntegerField(default=0, null=True)
  total_tackles = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  #FANTASY POINTS
  fantasy_points = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_ppr = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_fan_duel = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_yahoo = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_fantasy_draft = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_draft_kings = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_half_point_ppr = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_six_point_pass_td = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_per_game = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_per_game_ppr = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_per_game_fan_duel = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_per_game_yahoo = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_per_game_draft_kings = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_per_game_half_point_ppr = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_per_game_six_point_pass_td = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_points_per_game_fantasy_draft = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  #SNAPS
  rush_snap_percentage = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  target_snap_percentage = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  touch_snap_percentage = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  intended_touch_snap_percentage = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  tackle_snap_percentage = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  sack_snap_percentage = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  quarterback_hit_snap_percentage = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_point_snap_percentage = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_point_snap_percentage_ppr = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_point_snap_percentage_fan_duel = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_point_snap_percentage_yahoo = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_point_snap_percentage_draft_kings = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_point_snap_percentage_half_point_ppr = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_point_snap_percentage_six_point_pass_td = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  fantasy_point_snap_percentage_fantasy_draft = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  snaps_per_game = models.IntegerField(default=0, null=True)
  snaps_played = models.IntegerField(default=0, null=True)
  snaps_played_percentage = models.DecimalField(default=0, max_digits=6, decimal_places=1, null=True)
  #extend manager to include json parsing for object creation
  objects = PlayerStatManager()

'''
GREP INFO FOR CHANGING CAMELCASE TO SNAKE CASE:
find:
([A-Z])(?:([a-z0-9]*)([A-Z]))([a-z0-9]*)([a-zA-Z0-9]*)(\s=)
replace:
\l\1\2_\l\3\4_\5\6
Run the above over and over until no more match (watch out for all caps like PPR)

Then run this to capture the single words remaining:
find:
([A-Z])(?:([a-z0-9]*))(\s=)
replace:
\l\1\2_\3

Run with GREP on and case-sensitive on
'''

'''
example data:

{
  "Data": [
    {
      "PlayerID": 16765,
      "Season": 2018,
      "Played": 1,
      "Started": 1,
      "Week": 14,
      "Opponent": "PHI",
      "TeamHasPossession": false,
      "HomeOrAway": null,
      "TeamIsHome": true,
      "Result": "W",
      "HomeScore": 29,
      "AwayScore": 23,
      "Quarter": "F\/OT",
      "QuarterDisplay": "F\/OT",
      "IsGameOver": true,
      "GameDate": "\/Date(1544390700000)\/",
      "TimeRemaining": null,
      "ScoreSummary": "F\/OT (W) 29 - 23 vs. PHI",
      "PassingCompletions": 0,
      "PassingAttempts": 0,
      "PassingCompletionPercentage": 0,
      "PassingYards": 0,
      "PassingYardsPerAttempt": 0,
      "PassingTouchdowns": 0,
      "PassingInterceptions": 0,
      "PassingRating": 0,
      "RushingAttempts": 0,
      "RushingYards": 0,
      "RushingYardsPerAttempt": 0,
      "RushingTouchdowns": 0,
      "Receptions": 10,
      "ReceivingTargets": 13,
      "ReceivingYards": 217,
      "ReceptionPercentage": 76.9,
      "ReceivingTouchdowns": 3,
      "ReceivingLong": 75,
      "ReceivingYardsPerTarget": 16.7,
      "ReceivingYardsPerReception": 21.7,
      "Fumbles": 0,
      "FumblesLost": 0,
      "FieldGoalsMade": 0,
      "FieldGoalsAttempted": 0,
      "FieldGoalPercentage": 0,
      "FieldGoalsLongestMade": 0,
      "ExtraPointsMade": 0,
      "ExtraPointsAttempted": 0,
      "TacklesForLoss": 0,
      "Sacks": 0,
      "QuarterbackHits": 0,
      "Interceptions": 0,
      "FumblesRecovered": 0,
      "Safeties": 0,
      "DefensiveTouchdowns": 0,
      "SpecialTeamsTouchdowns": 0,
      "SoloTackles": 0,
      "AssistedTackles": 0,
      "SackYards": 0,
      "PassesDefended": 0,
      "FumblesForced": 0,
      "FantasyPoints": 39.7,
      "FantasyPointsPPR": 49.7,
      "FantasyPointsFanDuel": 44.7,
      "FantasyPointsYahoo": 44.7,
      "FantasyPointsFantasyDraft": 52.7,
      "FantasyPointsDraftKings": 52.7,
      "FantasyPointsHalfPointPpr": 44.7,
      "FantasyPointsSixPointPassTd": 39.7,
      "FantasyPointsPerGame": 39.7,
      "FantasyPointsPerGamePPR": 49.7,
      "FantasyPointsPerGameFanDuel": 44.7,
      "FantasyPointsPerGameYahoo": 44.7,
      "FantasyPointsPerGameDraftKings": 52.7,
      "FantasyPointsPerGameHalfPointPPR": 44.7,
      "FantasyPointsPerGameSixPointPassTd": 39.7,
      "FantasyPointsPerGameFantasyDraft": 52.7,
      "PlayerUrlString": "\/nfl\/amari-cooper-fantasy\/16765",
      "GameStatus": "",
      "GameStatusClass": "",
      "PointsAllowedByDefenseSpecialTeams": null,
      "TotalTackles": 0,
      "StatSummary": [
        {
          "Items": [
            {
              "StatValue": "13",
              "StatTitle": "TGT"
            },
            {
              "StatValue": "10",
              "StatTitle": "REC"
            },
            {
              "StatValue": "217",
              "StatTitle": "YDS"
            },
            {
              "StatValue": "3",
              "StatTitle": "TD"
            }
          ]
        }
      ],
      "Name": "Amari Cooper",
      "ShortName": "A. Cooper",
      "FirstName": "Amari",
      "LastName": "Cooper",
      "FantasyPosition": "WR",
      "Position": "WR",
      "TeamUrlString": "\/nfl\/team-details\/DAL",
      "Team": "DAL",
      "IsScrambled": false,
      "Rank": 1,
      "StaticRank": 0,
      "PositionRank": null,
      "IsFavorite": false
    }
  ],
  "Total": 2537,
  "AggregateResults": null,
  "Errors": null
}
'''

'''
SNAPS DATA 
      "RushSnapPercentage": 18.2,
      "TargetSnapPercentage": 0,
      "TouchSnapPercentage": 60.6,
      "IntendedTouchSnapPercentage": 60.6,
      "TackleSnapPercentage": 0,
      "SackSnapPercentage": 0,
      "QuarterbackHitSnapPercentage": 0,
      "FantasyPointSnapPercentage": 64.1,
      "FantasyPointSnapPercentagePPR": 64.1,
      "FantasyPointSnapPercentageFanDuel": 64.1,
      "FantasyPointSnapPercentageYahoo": 64.1,
      "FantasyPointSnapPercentageDraftKings": 68.6,
      "FantasyPointSnapPercentageHalfPointPPR": 64.1,
      "FantasyPointSnapPercentageSixPointPassTd": 76.2,
      "FantasyPointSnapPercentageFantasyDraft": 68.6,
      "SnapsPerGame": 66,
      "SnapsPlayed": 66,
      "SnapsPlayedPercentage": 100,

'''
