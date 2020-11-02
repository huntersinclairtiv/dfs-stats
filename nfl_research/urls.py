from django.conf.urls import url

from . import views
from nfl_research.views import Home
from nfl_research.views import NFL_Stats
from nfl_research.views import Showdown
from nfl_research.views import Data_Loader
from nfl_research.views import Get_Current_Week
from nfl_research.views import Get_Current_Season
from nfl_research.views import Get_Current_Week_Games
from nfl_research.views import Get_Team_Season_Stats
from nfl_research.views import Get_Team_Projections
from nfl_research.views import Load_Week_Data
from nfl_research.views import Load_Season_Data
from nfl_research.views import Update_Stats_Data
from nfl_research.views import Reload_Slates_Salary_Data
from nfl_research.views import Get_Slates
from nfl_research.views import Get_Slate_Games
from nfl_research.views import Get_Slate_Players
from nfl_research.views import Update_Week_Data_For_Team
from nfl_research.views import Save_File
from nfl_research.views import Load_Stats_Data

urlpatterns = [
    url(r'^nfl-stats/', NFL_Stats.as_view()),
    url(r'^showdown/', Showdown.as_view()),
    url(r'^data-loader/', Data_Loader.as_view()),
    #url(r'^nfl-stats/', views.nfl_stats, name='nfl_stats'),
    url(r'^get_current_week/', Get_Current_Week.as_view()),
    url(r'^get_current_season/', Get_Current_Season.as_view()),
    url(r'^get_current_week_games/', Get_Current_Week_Games.as_view()),
    url(r'^get_team_season_stats/', Get_Team_Season_Stats.as_view()),
    url(r'^get_team_projections/', Get_Team_Projections.as_view()),
    url(r'^load_week/', Load_Week_Data.as_view()),
    url(r'^load_season/', Load_Season_Data.as_view()),
    url(r'^update_stats_data/', Update_Stats_Data.as_view()),
    url(r'^load_stats_data/', Load_Stats_Data.as_view()),
    #url(r'^load_week/', views.load_week, name='load_week'),
    url(r'^load_salary/', Reload_Slates_Salary_Data.as_view()),
    #url(r'^load_salary/', views.load_salary, name='load_salary'),
    url(r'^get_slates/', Get_Slates.as_view()),
    url(r'^get_slate_games/', Get_Slate_Games.as_view()),
    url(r'^get_slate_players/', Get_Slate_Players.as_view()),
    #url(r'^get_slates/', views.get_slates, name='get_slates'),
    url(r'^update_weekdata_for_team_request/', Update_Week_Data_For_Team.as_view()),
    #url(r'^update_weekdata_for_team_request/', views.update_weekdata_for_team_request, name='update_weekdata_for_team_request'),
    #url(r'^keyword/', views.keyword, name='keyword'),
    #url(r'^project/', views.projectSpecific, name='projectSpecific'),
    #url(r'^projects/', views.projects, name='projects'),
    #url(r'^create_project/', views.create_project, name='create_project'),
    url(r'^savefile/', Save_File.as_view()),
    #url(r'^savefile/', views.saveFile, name='saveFile'),
    #url(r'^start_explore/', views.start_explore, name='start_explore'),
    #url(r'^explore_collect/', views.explore_collect, name='explore_collect'),
    #url(r'^explore_collect_keyword/', views.explore_collect_keyword, name='explore_collect_keyword'),
    url(r'^$', Home.as_view()),
    #url(r'^$', views.index, name='index'),
]