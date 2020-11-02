import sys
import logging
import time
import os
import re
import csv
import collections
from django.views import View
from django.views.generic import TemplateView

from nfl_research.constants import teamNames
from nfl_research.utilities import NFL_Utilities
from nfl_research.models import Player_Game_Stats

from django.http import HttpResponse
from django.shortcuts import render, redirect
from bs4 import BeautifulSoup, Comment
import urllib.request
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
import requests
import nltk
import nltk.corpus  
from nltk.text import Text, FreqDist, ContextIndex
from nltk.util import tokenwrap, LazyConcatenation, skipgrams
from nltk.metrics import f_measure, BigramAssocMeasures, TrigramAssocMeasures
from nltk.collocations import BigramCollocationFinder
from os import walk
import os.path
import zipfile
from django.http import JsonResponse
from nltk.tokenize import RegexpTokenizer
from stop_words import get_stop_words
from nltk.stem.porter import PorterStemmer
from gensim import corpora, models
import gensim
from nltk.corpus import stopwords
import json

try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
STATIC_PROJECTS = '/static/projects/'
STATIC_DATA = '/static/data/'
API_KEY='5f8fb37357c749b0a91651561af92cbe'
PROJ_API_KEY='1122438f4e6d46afa9404a8c51cdc194'
API_VERSION_URL='https://api.sportsdata.io/v3/'
DOM_API_URL='https://domination.dfsarmy.com/api/v1/'

requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL'
try:
    requests.packages.urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST = 'ALL'
except AttributeError:
    # no pyopenssl support used / needed / available
    pass

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
# logging.debug('A debug message!')
# logging.info('We processed %d records', len(processed_records))

# Generic View Handling
class Data_Manager:
  #define class properties here

  '''
  *****************************************************************************************
  LOAD STATS DATA FOR ALL TEAMS
  *****************************************************************************************
  '''
  def update_stats_data_request(theYear, theWeek, theSeason, reload):
    data = {"errorMsg":"","success":"","logResults":[]}

    thisYear = int((datetime.today() - timedelta(days=60)).year) # subtracting 60 days since some games played into new year - 4digit current year.
    teams = ['ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC','LAC','LAR','MIA','MIN','NE','NO','NYG','NYJ','OAK','PHI','PIT','SEA','SF','TB','TEN','WAS']
    positions = {2:'QB',3:'RB',4:'WR',5:'TE',6:'K',7:'DST',9:'DL',10:'LB',11:'DB'}
    seasonTypes = {1:'REG',2:'PRE',3:'POST'}
    seasonTypeWeeks = {1:[1,17],2:[1,4],3:[1,4]}

    #if seasontype passed in then remove others
    if (theSeason == "Post") :
      seasonTypes = {3:'POST'}
    elif (theSeason == "Pre") :
      seasonTypes = {2:'PRE'}
    elif (theSeason == "Week") :
      seasonTypes = {1:'REG'}

    forceReload = False
    if (reload == "true") :
      forceReload = True
    #team = 1 #1 to 32 as in array above. Using 0 index count

    path = SITE_ROOT + STATIC_PROJECTS + 'downloaded_stats' + '/'
    NFL_Utilities.makeDirIfDoesNotExist(path)
    
    #OLD queryurl = 'https://fantasydata.com/nfl-stats/nfl-fantasy-football-stats.aspx?fs=' + str(fsNum) + '&stype=' + str(seasonType) + '&sn=' + str(nflYear) + '&scope=1&w=' + str(weekNumStart) + '&ew=' + str(weekNumStop) + '&s=&t=' + str(team) + '&p=' + str(position) + '&st=' + str(scoringType) + '&d=1&ls=&live=false&pid=false&minsnaps=4'
    #queryurl = 'https://fantasydata.com/FantasyStatsNFL/FantasyStats_Read?sort=FantasyPointsDraftKings-desc&pageSize=2500&group=&filter=&filters.position=4&filters.team=&filters.teamkey=&filters.season=2018&filters.seasontype=1&filters.scope=2&filters.subscope=1&filters.redzonescope=&filters.scoringsystem=4&filters.leaguetype=&filters.searchtext=&filters.week=&filters.startweek=1&filters.endweek=17&filters.minimumsnaps=&filters.teamaspect=&filters.stattype=&filters.exportType=&filters.desktop=&filters.dfsoperator=&filters.dfsslateid=&filters.dfsslategameid=&filters.dfsrosterslot=&filters.page=&filters.showfavs=&filters.posgroup=&filters.oddsstate=&filters.aggregatescope=1&filters.rangescope=&filters.range=1'

    # RESPONSE: {"Data":[{"PlayerID":16765,"Season":2018,"Played":1,"Started":1,"Week":14,"Opponent":"PHI","TeamHasPossession":false,"HomeOrAway":null,"TeamIsHome":true,"Result":"W","HomeScore":29,"AwayScore":23,"Quarter":"F/OT","QuarterDisplay":"F/OT","IsGameOver":true,"GameDate":"\/Date(1544390700000)\/","TimeRemaining":null,"ScoreSummary":"F/OT (W) 29 - 23 vs. PHI","PassingCompletions":0,"PassingAttempts":0,"PassingCompletionPercentage":0,"PassingYards":0,"PassingYardsPerAttempt":0,"PassingTouchdowns":0.00,"PassingInterceptions":0.00,"PassingRating":0,"RushingAttempts":0.00,"RushingYards":0.00,"RushingYardsPerAttempt":0,"RushingTouchdowns":0.00,"Receptions":10.00,"ReceivingTargets":13.00,"ReceivingYards":217.00,"ReceptionPercentage":76.9,"ReceivingTouchdowns":3.00,"ReceivingLong":75.00,"ReceivingYardsPerTarget":16.7,"ReceivingYardsPerReception":21.7,"Fumbles":0.00,"FumblesLost":0.00,"FieldGoalsMade":0.00,"FieldGoalsAttempted":0.00,"FieldGoalPercentage":0,"FieldGoalsLongestMade":0.00,"ExtraPointsMade":0.00,"ExtraPointsAttempted":0.00,"TacklesForLoss":0.00,"Sacks":0.00,"QuarterbackHits":0.00,"Interceptions":0.00,"FumblesRecovered":0.00,"Safeties":0.00,"DefensiveTouchdowns":0,"SpecialTeamsTouchdowns":0,"SoloTackles":0.00,"AssistedTackles":0.00,"SackYards":0.00,"PassesDefended":0.00,"FumblesForced":0.00,"FantasyPoints":39.70,"FantasyPointsPPR":49.70,"FantasyPointsFanDuel":44.70,"FantasyPointsYahoo":44.70,"FantasyPointsFantasyDraft":52.70,"FantasyPointsDraftKings":52.70,"FantasyPointsHalfPointPpr":44.70,"FantasyPointsSixPointPassTd":39.70,"FantasyPointsPerGame":39.7,"FantasyPointsPerGamePPR":49.7,"FantasyPointsPerGameFanDuel":44.7,"FantasyPointsPerGameYahoo":44.7,"FantasyPointsPerGameDraftKings":52.7,"FantasyPointsPerGameHalfPointPPR":44.7,"FantasyPointsPerGameSixPointPassTd":39.7,"FantasyPointsPerGameFantasyDraft":52.7,"PlayerUrlString":"/nfl/amari-cooper-fantasy/16765","GameStatus":"","GameStatusClass":"","PointsAllowedByDefenseSpecialTeams":null,"TotalTackles":0.00,"StatSummary":[{"Items":[{"StatValue":"13","StatTitle":"TGT"},{"StatValue":"10","StatTitle":"REC"},{"StatValue":"217","StatTitle":"YDS"},{"StatValue":"3","StatTitle":"TD"}]}],"Name":"Amari Cooper","ShortName":"A. Cooper","FirstName":"Amari","LastName":"Cooper","FantasyPosition":"WR","Position":"WR","TeamUrlString":"/nfl/team-details/DAL","Team":"DAL","IsScrambled":false,"Rank":1,"StaticRank":0,"PositionRank":null,"IsFavorite":false}],"Total":2537,"AggregateResults":null,"Errors":null}
    #Year	Season	Rk	Player	Pos	Week	Team
    #return filtered array
    #filter(lambda x:x[1]=='test',list)

    lowYear = 2010
    highYear = thisYear + 1
    if (theYear > 0) : #if year passed in we only need to do 1 loop for this one year
      lowYear = theYear
      highYear = theYear + 1
      
    logResultsArr=[]
    
    for yearNum in range(lowYear, highYear):
      for seasonTypeNum in seasonTypes:
        #first set the low and high week numbers which go with the seasonType (1-4 for pre and post, and 1-17 for reg)
        lowWeek = seasonTypeWeeks[seasonTypeNum][0]
        highWeek = seasonTypeWeeks[seasonTypeNum][1] + 1
        if (theWeek > 0): #this means we just want a single week
          lowWeek = theWeek
          highWeek = theWeek + 1
        #for position in positions: #removing position since we can get all positions in one shot.
        for weekNum in range(lowWeek, highWeek):

          file_path = path + "fantasydata_" + str(yearNum) + "_" + seasonTypes[seasonTypeNum] + "_" + str(weekNum) + ".csv"
          statsJsonText = Data_Manager.load_data_for_query(file_path, 'FantasyStats_Read', yearNum, seasonTypeNum, weekNum, forceReload, logResultsArr)

          file_path2 = path + "fantasysnaps_" + str(yearNum) + "_" + seasonTypes[seasonTypeNum] + "_" + str(weekNum) + ".json"
          snapsJsonText = Data_Manager.load_data_for_query(file_path2, 'SnapCounts_Read', yearNum, seasonTypeNum, weekNum, forceReload, logResultsArr)
          
          '''
          THIS IS WHERE WE WILL STORE JSON IN DJANGO MODELS DB
          '''
          Player_Game_Stats.objects.create_with_json(jsonStatsText=statsJsonText, jsonSnapsText=snapsJsonText, seasonType=seasonTypes[seasonTypeNum])
          '''
          END STORE JSON IN DJANGO MODELS DB
          '''
          
          data["success"] = "true"
        #END OF WEEK LOOP
      #END OF SEASON TYPE LOOP
    #END OF YEAR LOOP

    data["logResults"] = '\n'.join(logResultsArr)
    return data


  '''
  *****************************************************************************************
  EITHER LOADS JSON TEXT FROM DISK OR DOWNLOADS FROM URL AND STORES TO DISK.
  - file_path : (str) path to the json file to save or load
  - yearNum : (int) 4 digit numeric year 
  - seasonTypeNum (int) : 1 digit numeric season type number
  - weekNum : (int) 1 digit numeric week number
  - forceReload : (bool) True/False - True will force us to redownload from the URL and 
      overwrite file on disk
  - logResultsArr : Note: this should be passed in as an array already created - so we can 
      append to it - we are not allowed to reassign value of array inside this function as
      it will not reference back to the original array and won't be passed back to caller.
  *****************************************************************************************
  '''
  def load_data_for_query(file_path, api_path, yearNum, seasonTypeNum, weekNum, forceReload, logResultsArr):
    jsonResponse = ''
    '''
    CHECK EXISTING FIRST
    '''
    if (os.path.exists(file_path) and forceReload == False):
      #if the file exists and we are not forcing a reload then just continue
      logResultsArr.append('Skipping Existing Stats: ' + file_path)
      with open(file_path, 'r') as content_file:
        jsonResponse = content_file.read()
    else:
      #else either the file does not exist OR we are forcing a refresh
      cookie = '_ga=GA1.2.2044379692.1564279303; _hjid=d506a6ac-e368-4ca1-87a7-f2ee23ae0ccb; _fbp=fb.1.1564279303585.1593872001; __adroll_fpc=c2463efb57dfa2bcaa765ab9d63a30c4-s2-1564279305950; .AspNet.Cookies=dT1h5gbpdknDaHQ7xNx5DkcAN4xvPG9WrbvyKoJR_ABYRmdtcYt6PjkUuy7Lz4eNzehJTdVFHdeYZZsKAbSVOBs4OyBl2p8hZgy83ixo4e837P7xzQWcPxl1y8hO4A86E0eMQdesQI5gcbJOEJdcDbpXgPg10_MHcphjF-K8Z_SWFSePSke3mk6CP2pPhROqQcLSwehCQ3xit1dotlWG9ZKkFTqBJlsIEqGzMtKkQ_W62eABUQUA9Gnz4K7YHMa7l8TWK9wHOS2ResL_IiK4OSJH5aIXDpIW67vwPYaNhc5qCbyxY1cx75AUv7w-P35GiiCtNYA8mRXR1ZehF3i2V2wQ64UFpBUrZaDHoOe-TQQD4rpCTSTNeFlO3oswmOeSuIWWldLq2rQBk3yGiUxKWnBqQM2qS4l3c8IBYJDE9b8nKbquQX8EasSVBrvzYkBYidNVvp61pQEzEFNnbeNglLL19eB85rUFvysWhh3LQClgaCvY1g0OyB1aCWS3OZmUbyax1lpFtRQMQwer4R5lTX1EtIU_yc4f7kDkl7l6pfuJPb1-T5PR0XxrQKvWJrGLkPr-XpQnbz33mWJEvZPpK12hvCCIyCps34wjyXdYBkKNWroD-Ud98kPSuOBuCYWELiqKxloGWoedppoMo2wOteotrjARGlRCKX45abzdsLujA--Jrsczi7by5ELcQSda8__D1bM5D1yPJyIseLO6V0XxynuyeUs2K62_49rSoVO7wfaNdO-rAW3-9nDgAEmP_nBHQcUwEi9Ry0xlcOQ_MA-EoEjvwzgNVUQ3uybDPGrIE1JV3bDeVQKVfhy46Zsv-E57T4haCXlfkGHfJ2EHt-uOARS6SkhQvj1eyMvFeoPjWYDS5VaPRuZ0kYLtIedd5lsnsPm9sC2oWZ4HawEk8QYK1-liLDYGckW9nuwq44RJ8FxRy3OmtKg6WMjnF8NsI7wmbMPZ8rZJLE1raE04n2m6TJa_Fyd1vNJZTegbHaUQmm9ouW5EAjdGYSapRUyNvLBEQdw4aMCcvr1iVB4JM3WsZ5YoW4EmpMXMDrXCl3wA4d_IvtR_9bSy3Gjm-cSvjxdr8OC3OBNycyGIp_8E8BJyOcoqAQIFSLy6zy4Or-5B6jKnbQ3zAXKor-SZBtL_GoWC4dMJghDosrZ4Olf7nZdp3HkkmRtnryZ4VL6RiuGkhZ77k7DJPm1J_OE6OE7SSPFG1OY3A50doq_9DWEBZ9vzTe8L9VlsM3Z2bYotrvgG_XyDx73Bn6ar33utKpFVmzJdgAPXD6O0j38WEaoBiY4m9Fi67eFp0Q3pPgA-AFmJvJ_nN7hwdtuOJCk-JxDIWnMg6bWa81Eiw4YseUXfsN-Zcauxz5Kt0z1agV53kzgdtZPN3tmtgyj7FlicaDpKmbWThxJ0BK6ltJdcbz-WvbD299fn1l8mqgxkRGPnUq_aTm1z1c0ly9xi1umZ-A5zLGTjYC3mafE1uoUejFt1I1Ib4AmBuuzpofiQqIODMfNwMS4ZOQTDFjWxbDjgKGxtiYDISIzLmIXgp2_gxn0Qkn2-q2qSh6J2YgJwjinUhfHmKDp0Q3trWL9E2Axo6e3pSf_zfT5ISPM6XdnAOHsL5SC0luk2WKTYJ2sjJ61dFHw; FantasyData_CookiesAccepted=1; ASP.NET_SessionId=vewzdij1whsfoiv55krsxylk; _hjIncludedInSample=1; kw_fwABAVsn_rIazwBQ=11; _gid=GA1.2.36845873.1567822060; _gat=1; _cioid=43511; _hjShownFeedbackMessage=true; _cio=d6e8119c-19ac-556e-56ab-a647cbeeb196; __ar_v4=2YUP7TATPFC7XD6D2GIARW%3A20190826%3A18%7CZUS4OCBXGBDWLCGQSOCSQN%3A20190826%3A18%7CNHFCO3TELVGCHHJD5FHXVD%3A20190826%3A18%7CMWS3UCEQVRCGPNAMIADWHZ%3A20190812%3A2'
      
      position = '' #note: we are setting this to empty since we want all positions
      queryurl = 'https://fantasydata.com/FantasyStatsNFL/' + api_path + '?test=&sort=&pageSize=2500&group=&filter=&filters.position=' + str(position) + '&filters.team=&filters.teamkey=&filters.season=' + str(yearNum) + '&filters.seasontype=' + str(seasonTypeNum) + '&filters.scope=2&filters.subscope=1&filters.redzonescope=&filters.scoringsystem=4&filters.leaguetype=&filters.searchtext=&filters.week=&filters.startweek=' + str(weekNum) + '&filters.endweek=' + str(weekNum) + '&filters.minimumsnaps=0&filters.teamaspect=&filters.stattype=&filters.exportType=&filters.desktop=&filters.dfsoperator=&filters.dfsslateid=&filters.dfsslategameid=&filters.dfsrosterslot=&filters.page=&filters.showfavs=&filters.posgroup=&filters.oddsstate=&filters.aggregatescope=1&filters.rangescope=&filters.range=1'
      #queryurl = 'https://fantasydata.com/FantasyStatsNFL/FantasyStats_Read?sort=FantasyPointsDraftKings-desc&pageSize=2500&group=&filter=&filters.position=' + str(position) + '&filters.team=&filters.teamkey=&filters.season=' + str(yearNum) + '&filters.seasontype=' + str(seasonTypeNum) + '&filters.scope=2&filters.subscope=1&filters.redzonescope=&filters.scoringsystem=4&filters.leaguetype=&filters.searchtext=&filters.week=&filters.startweek=' + str(weekNum) + '&filters.endweek=' + str(weekNum) + '&filters.minimumsnaps=&filters.teamaspect=&filters.stattype=&filters.exportType=&filters.desktop=&filters.dfsoperator=&filters.dfsslateid=&filters.dfsslategameid=&filters.dfsrosterslot=&filters.page=&filters.showfavs=&filters.posgroup=&filters.oddsstate=&filters.aggregatescope=1&filters.rangescope=&filters.range=1'
      #snapsqueryurl = 'https://fantasydata.com/FantasyStatsNFL/SnapCounts_Read?sort=FantasyPointSnapPercentage-desc&pageSize=2500&group=&filter=&filters.position=' + str(position) + '&filters.team=&filters.teamkey=&filters.season=' + str(yearNum) + '&filters.seasontype=' + str(seasonTypeNum) + '&filters.scope=2&filters.subscope=&filters.redzonescope=&filters.scoringsystem=&filters.leaguetype=&filters.searchtext=&filters.week=&filters.startweek=' + str(weekNum) + '&filters.endweek=' + str(weekNum) + '&filters.minimumsnaps=&filters.teamaspect=&filters.stattype=&filters.exportType=&filters.desktop=&filters.dfsoperator=&filters.dfsslateid=&filters.dfsslategameid=&filters.dfsrosterslot=&filters.page=&filters.showfavs=&filters.posgroup=&filters.oddsstate=&filters.aggregatescope=&filters.rangescope=&filters.range='
      if (api_path == "Slates_Read"):
        queryurl = 'https://fantasydata.com/FantasyStatsNFL/' + api_path + '?sort=OperatorSalary-desc~FantasyPointsDraftKings-desc&pageSize=5000&group=&filter=&filters.position=' + str(position) + '&filters.team=&filters.teamkey=&filters.season=' + str(yearNum) + '&filters.seasontype=' + str(seasonTypeNum) + '&filters.scope=2&filters.subscope=&filters.redzonescope=&filters.scoringsystem=&filters.leaguetype=&filters.searchtext=&filters.week=&filters.startweek=' + str(weekNum) + '&filters.endweek=' + str(weekNum) + '&filters.minimumsnaps=&filters.teamaspect=&filters.stattype=&filters.exportType=&filters.desktop=&filters.dfsoperator=4&filters.dfsslateid=' + str(slateid) + '&filters.dfsslategameid=&filters.dfsrosterslot=&filters.page=&filters.showfavs=&filters.posgroup=&filters.oddsstate=&filters.aggregatescope=&filters.rangescope=&filters.range='

      jsonResponse = Data_Manager.get_text_from_url(queryurl)
      if (jsonResponse == ""): 
        logResultsArr.append('File not written: ' + file_path)
        logResultsArr.append('Error Calling URL: ' + queryurl)
        return

      #NOTE: find a better way to check for no results back - like parse JSON and check data array
      if (not jsonResponse or jsonResponse == '{"Data":[],"Total":0,"AggregateResults":null,"Errors":null}'):
        logging.debug('Response was empty for: ' + file_path)
        logResultsArr.append('Response was empty for: ' + file_path)
        return
      else :
        #append_write = 'ab' # append if already exists
        append_write = 'wb' # make a new file if not
        file = open(file_path, append_write) 
        file.write(str(jsonResponse).encode('utf-8')) 
        file.close()
        logResultsArr.append('File SUCCESSFULLY written: ' + file_path)
    #END OF ELSE FOR FILE EXISTS
    return jsonResponse


  '''
  *****************************************************************************************
  GETS the current NFL week number - this changes after the last game finished for week
  *****************************************************************************************
  '''
  def getCurrentWeek():
    #https://api.sportsdata.io/v3/nfl/scores/json/UpcomingWeek
    queryurl = API_VERSION_URL + 'nfl/scores/json/UpcomingWeek' + '?key=' + API_KEY

    jsonResponse = Data_Manager.get_text_from_url_nocookie(queryurl)

    return jsonResponse


  '''
  *****************************************************************************************
  GETS the current NFL season year - this changes after the last game finished for season
  *****************************************************************************************
  '''
  def getCurrentSeason():
    #https://api.sportsdata.io/v3/nfl/scores/json/UpcomingSeason
    queryurl = API_VERSION_URL + 'nfl/scores/json/UpcomingSeason' + '?key=' + API_KEY

    jsonResponse = Data_Manager.get_text_from_url_nocookie(queryurl)

    return jsonResponse



  '''
  *****************************************************************************************
  EITHER LOADS JSON TEXT FROM DISK OR DOWNLOADS FROM URL AND STORES TO DISK.
  - file_path : (str) path to the json file to save or load
  - api_path : (str) path to the API URL to call
  - forceReload : (bool) True/False - True will force us to redownload from the URL and 
      overwrite file on disk
  - logResultsArr : Note: this should be passed in as an array already created - so we can 
      append to it - we are not allowed to reassign value of array inside this function as
      it will not reference back to the original array and won't be passed back to caller.
  *****************************************************************************************
  '''
  def load_data_or_reload(file_path, api_path, forceReload, logResultsArr, apiCallMethod = 1):
    jsonResponse = ''
    '''
    CHECK EXISTING FIRST
    '''
    if (os.path.exists(file_path) and forceReload == False):
      #if the file exists and we are not forcing a reload then just continue
      logResultsArr.append('Skipping Existing Stats: ' + file_path)
      with open(file_path, 'r') as content_file:
        jsonResponse = content_file.read()
    else:
      #else either the file does not exist OR we are forcing a refresh
      queryurl = api_path

      if (apiCallMethod == 1):
        jsonResponse = Data_Manager.get_text_from_url_nocookie(queryurl)
      else:
        jsonResponse = Data_Manager.get_text_from_url_nocookie(queryurl, False)
        #with urllib.request.urlopen(queryurl) as url:
            #jsonResponse = url.read().decode()
            #jsonResponse = json.loads(url.read().decode())
      if (jsonResponse == ""): 
        logResultsArr.append('File not written: ' + file_path)
        logResultsArr.append('Error Calling URL: ' + queryurl)
        return

      #NOTE: find a better way to check for no results back - like parse JSON and check data array
      if (not jsonResponse or jsonResponse == '[]'):
        logging.debug('Response was empty for: ' + file_path)
        logResultsArr.append('Response was empty for: ' + file_path)
        return
      else :
        #append_write = 'ab' # append if already exists
        append_write = 'wb' # make a new file if not
        file = open(file_path, append_write) 
        file.write(str(jsonResponse).encode('utf-8')) 
        file.close()
        logResultsArr.append('File SUCCESSFULLY written: ' + file_path)
    #END OF ELSE FOR FILE EXISTS
    return jsonResponse
    

  '''
  *****************************************************************************************
  EITHER LOADS JSON TEXT FROM DISK OR DOWNLOADS FROM URL AND STORES TO DISK.
  - yearNum : (int) 4 digit numeric year 
  - seasonTypeNum (int) : 1 digit numeric season type number
  - forceReload : (bool) True/False - True will force us to redownload from the URL and 
      overwrite file on disk
  *****************************************************************************************
  '''

  def getSeasonDataIfExists(yearNum, seasonType, forceReload):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["logResults"] = ""
    data["playerData"] = []

    logResultsArr=[]
    file_path = SITE_ROOT + STATIC_DATA + 'sportsdata' + '/' + str(yearNum) + '/'
    if (not os.path.exists(file_path)):
        os.makedirs(file_path);
    raw_file = file_path + str(yearNum) + str(seasonType) + ".json"
    api_path = API_VERSION_URL + 'nfl/stats/json/PlayerSeasonStats/' + str(yearNum) + str(seasonType) + '?key=' + API_KEY
    results_data = Data_Manager.load_data_or_reload(raw_file, api_path, forceReload, logResultsArr)
    data["logResults"] = '\n'.join(logResultsArr)
    if (len(results_data) > 0) :
        try :
            parsed_data = json.loads(results_data)
            data["success"] = "true"
            data["playerData"] = parsed_data
        except :
            logResultsArr.append('Cant parse json for : ' + str(yearNum) + ' season: ' + str(seasonType))
            data["logResults"] = '\n'.join(logResultsArr)
            data["errorMsg"] = 'Cant parse json for : ' + str(yearNum) + ' season: ' + str(seasonType)
            return data
    else :
        data["errorMsg"] = "Error - Error loading player data from file or URL"

    return data

  '''
  *****************************************************************************************
  EITHER LOADS JSON TEXT FROM DISK OR DOWNLOADS FROM URL AND STORES TO DISK.
  - yearNum : (int) 4 digit numeric year 
  - seasonTypeNum (int) : 1 digit numeric season type number
  - forceReload : (bool) True/False - True will force us to redownload from the URL and 
      overwrite file on disk
  *****************************************************************************************
  '''

  def getCurrentWeekGames(yearNum, weekNum, forceReload):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["logResults"] = ""
    data["weekGameData"] = []

    logResultsArr=[]
    file_path = SITE_ROOT + STATIC_DATA + 'sportsdata' + '/' + str(yearNum) + '/'
    if (not os.path.exists(file_path)):
        os.makedirs(file_path);
    raw_file = file_path + str(yearNum)  + '_week' + str(weekNum) + ".json"
    #https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/2020/8?key=5f8fb37357c749b0a91651561af92cbe
    api_path = API_VERSION_URL + 'nfl/scores/json/ScoresByWeek/' + str(yearNum) + '/' + str(weekNum) + '?key=' + API_KEY
    results_data = Data_Manager.load_data_or_reload(raw_file, api_path, forceReload, logResultsArr)
    data["logResults"] = '\n'.join(logResultsArr)
    if (len(results_data) > 0) :
        try :
            parsed_data = json.loads(results_data)
            data["success"] = "true"
            data["weekGameData"] = parsed_data
        except :
            logResultsArr.append('Cant parse json for : ' + str(yearNum) + ' week: ' + str(weekNum))
            data["logResults"] = '\n'.join(logResultsArr)
            data["errorMsg"] = 'Cant parse json for : ' + str(yearNum) + ' week: ' + str(weekNum)
            return data
    else :
        data["errorMsg"] = "Error - Error loading player data from file or URL"

    return data

  '''
  *****************************************************************************************
  EITHER LOADS JSON TEXT FROM DISK OR DOWNLOADS FROM URL AND STORES TO DISK.
  - yearNum : (int) 4 digit numeric year 
  - seasonTypeNum (int) : 1 digit numeric season type number
  - forceReload : (bool) True/False - True will force us to redownload from the URL and 
      overwrite file on disk
  *****************************************************************************************
  '''
  def getTeamSeasonStats(yearNum, seasonType, forceReload):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["logResults"] = ""
    data["teamSeasonData"] = []

    logResultsArr=[]
    file_path = SITE_ROOT + STATIC_DATA + 'sportsdata' + '/' + str(yearNum) + '/'
    if (not os.path.exists(file_path)):
        os.makedirs(file_path);
    raw_file = file_path + 'TEAM_SEASON_' + str(yearNum) + str(seasonType) + ".json"
    #https://api.sportsdata.io/v3/nfl/scores/json/TeamSeasonStats/2020REG?key=5f8fb37357c749b0a91651561af92cbe
    api_path = API_VERSION_URL + 'nfl/scores/json/TeamSeasonStats/' + str(yearNum) + str(seasonType) + '?key=' + API_KEY
    results_data = Data_Manager.load_data_or_reload(raw_file, api_path, forceReload, logResultsArr)
    data["logResults"] = '\n'.join(logResultsArr)
    if (len(results_data) > 0) :
        try :
            parsed_data = json.loads(results_data)
            data["success"] = "true"
            data["teamSeasonData"] = parsed_data
        except :
            logResultsArr.append('Cant parse json for : ' + str(yearNum) + ' seasonType: ' + str(seasonType))
            data["logResults"] = '\n'.join(logResultsArr)
            data["errorMsg"] = 'Cant parse json for : ' + str(yearNum) + ' seasonType: ' + str(seasonType)
            return data
    else :
        data["errorMsg"] = "Error - Error loading player data from file or URL"

    return data


  '''
  *****************************************************************************************
  EITHER LOADS JSON TEXT FROM DISK OR DOWNLOADS FROM URL AND STORES TO DISK.
  - site : (str) iether 'draftkings' or 'fanduel'
  - yearNum : (int) 4 digit numeric year 
  - weekNum (int) : week number for slates requested for the season (1-21)
  - currentWeek (int) : week of the current week for current season.
  - forceReload : (bool) True/False - True will force us to redownload from the URL and 
      overwrite file on disk
  *****************************************************************************************
  '''
  def getWeekSlates(site, yearNum, weekNum, currentWeek, forceReload):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["logResults"] = ""
    data["slates"] = []

    logResultsArr=[]
    file_path = SITE_ROOT + STATIC_DATA + 'domdata' + '/' + str(yearNum) + '/'
    if (not os.path.exists(file_path)):
        os.makedirs(file_path)
    file_path = file_path + str(site) + '/'
    if (not os.path.exists(file_path)):
        os.makedirs(file_path)
        
    gameType = 'showdown';
    if (site == 'draftkings'):
        gameType = 'showdown'
    elif (site == 'fanduel'):
        gameType = 'single-game'
    
    slotsPath = 'slots';
    if (weekNum != currentWeek):
        slotsPath = 'archived-slots'

    raw_file = file_path + 'SLATES_' + str(yearNum) + '_week_' + str(weekNum) + ".json"
    # https://domination.dfsarmy.com/api/v1/lineup-tool/slots?sport=nfl&site=draftkings&gameType=showdown
    # https://domination.dfsarmy.com/api/v1/lineup-tool/slots?sport=nfl&site=fanduel&gameType=single-game
    # https://domination.dfsarmy.com/api/v1/lineup-tool/archived-slots?sport=nfl&site=draftkings&gameType=showdown
    # https://domination.dfsarmy.com/api/v1/lineup-tool/archived-slots?sport=nfl&site=fanduel&gameType=single-game
    api_path = DOM_API_URL + 'lineup-tool/' + str(slotsPath) + '?sport=nfl&site=' + str(site) + '&gameType=' + str(gameType)
    results_data = Data_Manager.load_data_or_reload(raw_file, api_path, forceReload, logResultsArr, 2) #pass 2 for different api method
    data["logResults"] = '\n'.join(logResultsArr)
    if (len(results_data) > 0) :
        try :
            parsed_data = json.loads(results_data)
            data["success"] = "true"
            data["slates"] = parsed_data
        except :
            logResultsArr.append('Cant parse json for : ' + str(yearNum) + ' week: ' + str(weekNum))
            data["logResults"] = '\n'.join(logResultsArr)
            data["errorMsg"] = 'Cant parse json for : ' + str(yearNum) + ' week: ' + str(weekNum)
            return data
    else :
        data["errorMsg"] = "Error - Error loading player data from file or URL"

    return data
    

  '''
  *****************************************************************************************
  EITHER LOADS JSON TEXT FROM DISK OR DOWNLOADS FROM URL AND STORES TO DISK.
  - site : (str) iether 'draftkings' or 'fanduel'
  - yearNum : (int) 4 digit numeric year 
  - weekNum (int) : week number for slates requested for the season (1-21)
  - slateId (str) :id for the slate.
  - forceReload : (bool) True/False - True will force us to redownload from the URL and 
      overwrite file on disk
  *****************************************************************************************
  '''
  def getSlateGames(site, yearNum, weekNum, slateId, forceReload):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["logResults"] = ""
    data["games"] = []

    logResultsArr=[]
    file_path = SITE_ROOT + STATIC_DATA + 'domdata' + '/' + str(yearNum) + '/'
    if (not os.path.exists(file_path)):
        os.makedirs(file_path)
    file_path = file_path + str(site) + '/'
    if (not os.path.exists(file_path)):
        os.makedirs(file_path)
        
    raw_file = file_path + 'SLATES_GAMES_' + str(yearNum) + '_week_' + str(weekNum) + '_slate_' + str(slateId) + ".json"
    # 'https://domination.dfsarmy.com/api/v1/lineup-tool/games?slot=' + slateId,
    api_path = DOM_API_URL + 'lineup-tool/games?slot=' + str(slateId)
    results_data = Data_Manager.load_data_or_reload(raw_file, api_path, forceReload, logResultsArr, 2) #pass 2 for different api method
    data["logResults"] = '\n'.join(logResultsArr)
    if (len(results_data) > 0) :
        try :
            parsed_data = json.loads(results_data)
            data["success"] = "true"
            data["games"] = parsed_data
        except :
            logResultsArr.append('Cant parse json for : ' + str(yearNum) + ' week: ' + str(weekNum))
            data["logResults"] = '\n'.join(logResultsArr)
            data["errorMsg"] = 'Cant parse json for : ' + str(yearNum) + ' week: ' + str(weekNum)
            return data
    else :
        data["errorMsg"] = "Error - Error loading player data from file or URL"

    return data


  '''
  *****************************************************************************************
  EITHER LOADS JSON TEXT FROM DISK OR DOWNLOADS FROM URL AND STORES TO DISK.
  - site : (str) iether 'draftkings' or 'fanduel'
  - yearNum : (int) 4 digit numeric year 
  - weekNum (int) : week number for slates requested for the season (1-21)
  - slateId (str) :id for the slate.
  - forceReload : (bool) True/False - True will force us to redownload from the URL and 
      overwrite file on disk
  *****************************************************************************************
  '''
  def getSlatePlayers(site, yearNum, weekNum, slateId, forceReload):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["logResults"] = ""
    data["players"] = []

    logResultsArr=[]
    file_path = SITE_ROOT + STATIC_DATA + 'domdata' + '/' + str(yearNum) + '/'
    if (not os.path.exists(file_path)):
        os.makedirs(file_path)
    file_path = file_path + str(site) + '/'
    if (not os.path.exists(file_path)):
        os.makedirs(file_path)
        
    raw_file = file_path + 'SLATES_PLAYERS_' + str(yearNum) + '_week_' + str(weekNum) + '_slate_' + str(slateId) + ".json"
    #https://domination.dfsarmy.com/api/v1/lineup-tool/players?slot=18882
    api_path = DOM_API_URL + 'lineup-tool/players?slot=' + str(slateId)
    results_data = Data_Manager.load_data_or_reload(raw_file, api_path, forceReload, logResultsArr, 2) #pass 2 for different api method
    data["logResults"] = '\n'.join(logResultsArr)
    if (len(results_data) > 0) :
        try :
            parsed_data = json.loads(results_data)
            data["success"] = "true"
            data["players"] = parsed_data
        except :
            logResultsArr.append('Cant parse json for : ' + str(yearNum) + ' week: ' + str(weekNum))
            data["logResults"] = '\n'.join(logResultsArr)
            data["errorMsg"] = 'Cant parse json for : ' + str(yearNum) + ' week: ' + str(weekNum)
            return data
    else :
        data["errorMsg"] = "Error - Error loading player data from file or URL"

    return data

  '''
  *****************************************************************************************
  EITHER LOADS JSON TEXT FROM DISK OR DOWNLOADS FROM URL AND STORES TO DISK.
  - yearNum : (int) 4 digit numeric year 
  - seasonType (str) : REG, POST, PRE.
  - weekNum (int) : week number for slates requested for the season (1-21)
  - teamName (str) :Initials for team.
  - forceReload : (bool) True/False - True will force us to redownload from the URL and 
      overwrite file on disk
  *****************************************************************************************
  '''
  def getTeamProjections(yearNum, seasonType, weekNum, teamName, forceReload):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["logResults"] = ""
    data["projData"] = []

    logResultsArr=[]
    file_path = SITE_ROOT + STATIC_DATA + 'sportsdata' + '/' + str(yearNum) + '/'
    if (not os.path.exists(file_path)):
        os.makedirs(file_path);
    raw_file = file_path + 'TEAM_PROJ_' + str(yearNum) + str(seasonType) + '_week_' + str(weekNum) + '_' + str(teamName) + '.json'
    #https://api.sportsdata.io/v3/nfl/projections/json/PlayerGameProjectionStatsByTeam/2020REG/8/PHI?key=1122438f4e6d46afa9404a8c51cdc194
    api_path = API_VERSION_URL + 'nfl/projections/json/PlayerGameProjectionStatsByTeam/' + str(yearNum) + str(seasonType) + '/' + str(weekNum) + '/' + str(teamName) + '?key=' + PROJ_API_KEY
    results_data = Data_Manager.load_data_or_reload(raw_file, api_path, forceReload, logResultsArr)
    data["logResults"] = '\n'.join(logResultsArr)
    if (len(results_data) > 0) :
        try :
            parsed_data = json.loads(results_data)
            data["success"] = "true"
            data["projData"] = parsed_data
        except :
            logResultsArr.append('Cant parse json for : ' + str(yearNum) + ' seasonType: ' + str(seasonType))
            data["logResults"] = '\n'.join(logResultsArr)
            data["errorMsg"] = 'Cant parse json for : ' + str(yearNum) + ' seasonType: ' + str(seasonType)
            return data
    else :
        data["errorMsg"] = "Error - Error loading player data from file or URL"

    return data


  '''
  EXAMPLE SQL
  ﻿select * from 
   nfl_research_player_game_stats pgs
   left join nfl_research_player p on p.id = pgs.player_id
   left join nfl_research_team_game_map tgm on tgm.id = pgs.team_game_id
   left join nfl_research_game g on g.id = tgm.game_id
   left join nfl_research_team tm on tgm.team_id = tm.id
   left join nfl_research_team opp on tgm.team_id = opp.id
 '''
 
 
  def get_text_from_url(queryurl):
    cookie = '_ga=GA1.2.2044379692.1564279303; _hjid=d506a6ac-e368-4ca1-87a7-f2ee23ae0ccb; _fbp=fb.1.1564279303585.1593872001; __adroll_fpc=c2463efb57dfa2bcaa765ab9d63a30c4-s2-1564279305950; .AspNet.Cookies=dT1h5gbpdknDaHQ7xNx5DkcAN4xvPG9WrbvyKoJR_ABYRmdtcYt6PjkUuy7Lz4eNzehJTdVFHdeYZZsKAbSVOBs4OyBl2p8hZgy83ixo4e837P7xzQWcPxl1y8hO4A86E0eMQdesQI5gcbJOEJdcDbpXgPg10_MHcphjF-K8Z_SWFSePSke3mk6CP2pPhROqQcLSwehCQ3xit1dotlWG9ZKkFTqBJlsIEqGzMtKkQ_W62eABUQUA9Gnz4K7YHMa7l8TWK9wHOS2ResL_IiK4OSJH5aIXDpIW67vwPYaNhc5qCbyxY1cx75AUv7w-P35GiiCtNYA8mRXR1ZehF3i2V2wQ64UFpBUrZaDHoOe-TQQD4rpCTSTNeFlO3oswmOeSuIWWldLq2rQBk3yGiUxKWnBqQM2qS4l3c8IBYJDE9b8nKbquQX8EasSVBrvzYkBYidNVvp61pQEzEFNnbeNglLL19eB85rUFvysWhh3LQClgaCvY1g0OyB1aCWS3OZmUbyax1lpFtRQMQwer4R5lTX1EtIU_yc4f7kDkl7l6pfuJPb1-T5PR0XxrQKvWJrGLkPr-XpQnbz33mWJEvZPpK12hvCCIyCps34wjyXdYBkKNWroD-Ud98kPSuOBuCYWELiqKxloGWoedppoMo2wOteotrjARGlRCKX45abzdsLujA--Jrsczi7by5ELcQSda8__D1bM5D1yPJyIseLO6V0XxynuyeUs2K62_49rSoVO7wfaNdO-rAW3-9nDgAEmP_nBHQcUwEi9Ry0xlcOQ_MA-EoEjvwzgNVUQ3uybDPGrIE1JV3bDeVQKVfhy46Zsv-E57T4haCXlfkGHfJ2EHt-uOARS6SkhQvj1eyMvFeoPjWYDS5VaPRuZ0kYLtIedd5lsnsPm9sC2oWZ4HawEk8QYK1-liLDYGckW9nuwq44RJ8FxRy3OmtKg6WMjnF8NsI7wmbMPZ8rZJLE1raE04n2m6TJa_Fyd1vNJZTegbHaUQmm9ouW5EAjdGYSapRUyNvLBEQdw4aMCcvr1iVB4JM3WsZ5YoW4EmpMXMDrXCl3wA4d_IvtR_9bSy3Gjm-cSvjxdr8OC3OBNycyGIp_8E8BJyOcoqAQIFSLy6zy4Or-5B6jKnbQ3zAXKor-SZBtL_GoWC4dMJghDosrZ4Olf7nZdp3HkkmRtnryZ4VL6RiuGkhZ77k7DJPm1J_OE6OE7SSPFG1OY3A50doq_9DWEBZ9vzTe8L9VlsM3Z2bYotrvgG_XyDx73Bn6ar33utKpFVmzJdgAPXD6O0j38WEaoBiY4m9Fi67eFp0Q3pPgA-AFmJvJ_nN7hwdtuOJCk-JxDIWnMg6bWa81Eiw4YseUXfsN-Zcauxz5Kt0z1agV53kzgdtZPN3tmtgyj7FlicaDpKmbWThxJ0BK6ltJdcbz-WvbD299fn1l8mqgxkRGPnUq_aTm1z1c0ly9xi1umZ-A5zLGTjYC3mafE1uoUejFt1I1Ib4AmBuuzpofiQqIODMfNwMS4ZOQTDFjWxbDjgKGxtiYDISIzLmIXgp2_gxn0Qkn2-q2qSh6J2YgJwjinUhfHmKDp0Q3trWL9E2Axo6e3pSf_zfT5ISPM6XdnAOHsL5SC0luk2WKTYJ2sjJ61dFHw; FantasyData_CookiesAccepted=1; ASP.NET_SessionId=vewzdij1whsfoiv55krsxylk; _hjIncludedInSample=1; kw_fwABAVsn_rIazwBQ=11; _gid=GA1.2.1834860186.1569033572; _cioid=43511; _hjShownFeedbackMessage=true; _cio=55ae7fa9-85da-e43c-7fc1-29be335869a7; __ar_v4=2YUP7TATPFC7XD6D2GIARW%3A20190826%3A90%7CZUS4OCBXGBDWLCGQSOCSQN%3A20190826%3A90%7CNHFCO3TELVGCHHJD5FHXVD%3A20190826%3A90'

    try:
      r = requests.get(queryurl, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36', 'cookie': cookie}, timeout=100)
    except requests.exceptions.RequestException as e:  # This is the correct syntax
      try:
        r = requests.get(queryurl, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36', 'cookie': cookie}, timeout=100)
      except requests.exceptions.RequestException as e:  # This is the correct syntax
        try:
          r = requests.get(queryurl, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36', 'cookie': cookie}, timeout=100)
        except requests.exceptions.RequestException as e:  # This is the correct syntax
          logging.debug(e)
          #r.close()
          return ""
          #sys.exit(1)
    #END OF TRY BLOCK
    this_text = r.text
    r.close()
    return this_text
  #END OF get_text_from_url

  def get_text_from_url_nocookie(queryurl, verifyOverride = True):
    #cookie = '_ga=GA1.2.2044379692.1564279303; _hjid=d506a6ac-e368-4ca1-87a7-f2ee23ae0ccb; _fbp=fb.1.1564279303585.1593872001; __adroll_fpc=c2463efb57dfa2bcaa765ab9d63a30c4-s2-1564279305950; .AspNet.Cookies=dT1h5gbpdknDaHQ7xNx5DkcAN4xvPG9WrbvyKoJR_ABYRmdtcYt6PjkUuy7Lz4eNzehJTdVFHdeYZZsKAbSVOBs4OyBl2p8hZgy83ixo4e837P7xzQWcPxl1y8hO4A86E0eMQdesQI5gcbJOEJdcDbpXgPg10_MHcphjF-K8Z_SWFSePSke3mk6CP2pPhROqQcLSwehCQ3xit1dotlWG9ZKkFTqBJlsIEqGzMtKkQ_W62eABUQUA9Gnz4K7YHMa7l8TWK9wHOS2ResL_IiK4OSJH5aIXDpIW67vwPYaNhc5qCbyxY1cx75AUv7w-P35GiiCtNYA8mRXR1ZehF3i2V2wQ64UFpBUrZaDHoOe-TQQD4rpCTSTNeFlO3oswmOeSuIWWldLq2rQBk3yGiUxKWnBqQM2qS4l3c8IBYJDE9b8nKbquQX8EasSVBrvzYkBYidNVvp61pQEzEFNnbeNglLL19eB85rUFvysWhh3LQClgaCvY1g0OyB1aCWS3OZmUbyax1lpFtRQMQwer4R5lTX1EtIU_yc4f7kDkl7l6pfuJPb1-T5PR0XxrQKvWJrGLkPr-XpQnbz33mWJEvZPpK12hvCCIyCps34wjyXdYBkKNWroD-Ud98kPSuOBuCYWELiqKxloGWoedppoMo2wOteotrjARGlRCKX45abzdsLujA--Jrsczi7by5ELcQSda8__D1bM5D1yPJyIseLO6V0XxynuyeUs2K62_49rSoVO7wfaNdO-rAW3-9nDgAEmP_nBHQcUwEi9Ry0xlcOQ_MA-EoEjvwzgNVUQ3uybDPGrIE1JV3bDeVQKVfhy46Zsv-E57T4haCXlfkGHfJ2EHt-uOARS6SkhQvj1eyMvFeoPjWYDS5VaPRuZ0kYLtIedd5lsnsPm9sC2oWZ4HawEk8QYK1-liLDYGckW9nuwq44RJ8FxRy3OmtKg6WMjnF8NsI7wmbMPZ8rZJLE1raE04n2m6TJa_Fyd1vNJZTegbHaUQmm9ouW5EAjdGYSapRUyNvLBEQdw4aMCcvr1iVB4JM3WsZ5YoW4EmpMXMDrXCl3wA4d_IvtR_9bSy3Gjm-cSvjxdr8OC3OBNycyGIp_8E8BJyOcoqAQIFSLy6zy4Or-5B6jKnbQ3zAXKor-SZBtL_GoWC4dMJghDosrZ4Olf7nZdp3HkkmRtnryZ4VL6RiuGkhZ77k7DJPm1J_OE6OE7SSPFG1OY3A50doq_9DWEBZ9vzTe8L9VlsM3Z2bYotrvgG_XyDx73Bn6ar33utKpFVmzJdgAPXD6O0j38WEaoBiY4m9Fi67eFp0Q3pPgA-AFmJvJ_nN7hwdtuOJCk-JxDIWnMg6bWa81Eiw4YseUXfsN-Zcauxz5Kt0z1agV53kzgdtZPN3tmtgyj7FlicaDpKmbWThxJ0BK6ltJdcbz-WvbD299fn1l8mqgxkRGPnUq_aTm1z1c0ly9xi1umZ-A5zLGTjYC3mafE1uoUejFt1I1Ib4AmBuuzpofiQqIODMfNwMS4ZOQTDFjWxbDjgKGxtiYDISIzLmIXgp2_gxn0Qkn2-q2qSh6J2YgJwjinUhfHmKDp0Q3trWL9E2Axo6e3pSf_zfT5ISPM6XdnAOHsL5SC0luk2WKTYJ2sjJ61dFHw; FantasyData_CookiesAccepted=1; ASP.NET_SessionId=vewzdij1whsfoiv55krsxylk; _hjIncludedInSample=1; kw_fwABAVsn_rIazwBQ=11; _gid=GA1.2.1834860186.1569033572; _cioid=43511; _hjShownFeedbackMessage=true; _cio=55ae7fa9-85da-e43c-7fc1-29be335869a7; __ar_v4=2YUP7TATPFC7XD6D2GIARW%3A20190826%3A90%7CZUS4OCBXGBDWLCGQSOCSQN%3A20190826%3A90%7CNHFCO3TELVGCHHJD5FHXVD%3A20190826%3A90'

    try:
      r = requests.get(queryurl, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36'}, timeout=100, verify=verifyOverride)
    except requests.exceptions.RequestException as e:  # This is the correct syntax
      try:
        r = requests.get(queryurl, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36'}, timeout=100, verify=False)
      except requests.exceptions.RequestException as e:  # This is the correct syntax
        try:
          r = requests.get(queryurl, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36'}, timeout=100, verify=False)
        except requests.exceptions.RequestException as e:  # This is the correct syntax
          logging.debug(e)
          #r.close()
          return ""
          #sys.exit(1)
    #END OF TRY BLOCK
    this_text = r.text
    r.close()
    return this_text
  #END OF get_text_from_url
  
  '''
  *****************************************************************************************
  THIS GETS SALARIES FOR SPECIFIC SLATE
  EITHER LOADS JSON TEXT FROM DISK OR DOWNLOADS FROM URL AND STORES TO DISK.
  - file_path : (str) path to the json file to save or load
  - yearNum : (int) 4 digit numeric year 
  - seasonTypeNum (int) : 1 digit numeric season type number
  - weekNum : (int) 1 digit numeric week number
  - slateid : (int) number identifying slate for week
  - forceReload : (bool) True/False - True will force us to redownload from the URL and 
      overwrite file on disk
  - logResultsArr : Note: this should be passed in as an array already created - so we can 
      append to it - we are not allowed to reassign value of array inside this function as
      it will not reference back to the original array and won't be passed back to caller.
  *****************************************************************************************
  '''
  def load_data_for_slate(file_path, api_path, yearNum, seasonTypeNum, weekNum, forceReload, logResultsArr):
    jsonResponse = ''
    '''
    CHECK EXISTING FIRST
    '''
    if (os.path.exists(file_path) and forceReload == False):
      #if the file exists and we are not forcing a reload then just continue
      logResultsArr.append('Skipping Existing Stats for Slate: ' + file_path)
      with open(file_path, 'r') as content_file:
        jsonResponse = content_file.read()
    else:
      #else either the file does not exist OR we are forcing a refresh
      
      position = '' #note: we are setting this to empty since we want all positions
      slatesurl = 'https://fantasydata.com/FantasyStatsNFL/AvailableSlates_Read?sort=OperatorSalary-desc~FantasyPointsDraftKings-desc&pageSize=5000&group=&filter=&filters.position=' + str(position) + '&filters.team=&filters.teamkey=&filters.season=' + str(yearNum) + '&filters.seasontype=' + str(seasonTypeNum) + '&filters.scope=2&filters.subscope=&filters.redzonescope=&filters.scoringsystem=&filters.leaguetype=&filters.searchtext=&filters.week=&filters.startweek=' + str(weekNum) + '&filters.endweek=' + str(weekNum) + '&filters.minimumsnaps=&filters.teamaspect=&filters.stattype=&filters.exportType=&filters.desktop=&filters.dfsoperator=4&filters.dfsslateid=&filters.dfsslategameid=&filters.dfsrosterslot=&filters.page=&filters.showfavs=&filters.posgroup=&filters.oddsstate=&filters.aggregatescope=&filters.rangescope=&filters.range='

      slateid = ''
      jsonResponse = Data_Manager.get_text_from_url(slatesurl)
      if (jsonResponse == ""): 
        logResultsArr.append('Error Calling URL: ' + slatesurl)
        return
      else :
        try :
          slate_data = json.loads(jsonResponse)
          slateid = next((x.get('SlateID','') for x in slate_data if x.get('OperatorName','') == "Main"), '')
        except :
          logResultsArr.append('Cant find main slate id: ' + slatesurl)
      
      if slateid == '' :
        logResultsArr.append('Cant find main slate id for : ' + slatesurl)

      #NOW call for salaries
      queryurl = 'https://fantasydata.com/FantasyStatsNFL/' + api_path + '?sort=OperatorSalary-desc~FantasyPointsDraftKings-desc&pageSize=5000&group=&filter=&filters.position=' + str(position) + '&filters.team=&filters.teamkey=&filters.season=' + str(yearNum) + '&filters.seasontype=' + str(seasonTypeNum) + '&filters.scope=2&filters.subscope=&filters.redzonescope=&filters.scoringsystem=&filters.leaguetype=&filters.searchtext=&filters.week=&filters.startweek=' + str(weekNum) + '&filters.endweek=' + str(weekNum) + '&filters.minimumsnaps=&filters.teamaspect=&filters.stattype=&filters.exportType=&filters.desktop=&filters.dfsoperator=4&filters.dfsslateid=' + str(slateid) + '&filters.dfsslategameid=&filters.dfsrosterslot=&filters.page=&filters.showfavs=&filters.posgroup=&filters.oddsstate=&filters.aggregatescope=&filters.rangescope=&filters.range='

      jsonResponse = Data_Manager.get_text_from_url(queryurl)
      if (jsonResponse == ""): 
        logResultsArr.append('File not written: ' + file_path)
        logResultsArr.append('Error Calling URL: ' + queryurl)
        return


      #NOTE: find a better way to check for no results back - like parse JSON and check data array
      if (not jsonResponse or jsonResponse == '{"Data":[],"Total":0,"AggregateResults":null,"Errors":null}'):
        logging.debug('Response was empty for: ' + file_path)
        logResultsArr.append('Response was empty for: ' + file_path)
        return
      else :
        #append_write = 'ab' # append if already exists
        append_write = 'wb' # make a new file if not
        file = open(file_path, append_write) 
        file.write(str(jsonResponse).encode('utf-8')) 
        file.close()
        logResultsArr.append('File SUCCESSFULLY written: ' + file_path)
    #END OF ELSE FOR FILE EXISTS
    return jsonResponse


  '''
  *****************************************************************************************
  COMBINE FILES INTO 1 JSON
  *****************************************************************************************
  '''
  def combine_files_to_one_json(theYear, theWeek, theSeason, reload):
    data = {"errorMsg":"","success":"","logResults":[]}

    thisYear = int((datetime.today() - timedelta(days=60)).year) # subtracting 60 days since some games played into new year - 4digit current year.
    teams = ['ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC','LAC','LAR','MIA','MIN','NE','NO','NYG','NYJ','OAK','PHI','PIT','SEA','SF','TB','TEN','WAS']
    positions = {2:'QB',3:'RB',4:'WR',5:'TE',6:'K',7:'DST',9:'DL',10:'LB',11:'DB'}
    seasonTypes = {1:'REG',2:'PRE',3:'POST'}
    seasonTypeWeeks = {1:[1,17],2:[1,4],3:[1,4]}

    #if seasontype passed in then remove others
    if (theSeason == "Post") :
      seasonTypes = {3:'POST'}
    elif (theSeason == "Pre") :
      seasonTypes = {2:'PRE'}
    elif (theSeason == "Week") :
      seasonTypes = {1:'REG'}

    forceReload = False
    if (reload == "true") :
      forceReload = True
    #team = 1 #1 to 32 as in array above. Using 0 index count

    path = SITE_ROOT + STATIC_PROJECTS + 'downloaded_stats' + '/'
    NFL_Utilities.makeDirIfDoesNotExist(path)
    
    #OLD queryurl = 'https://fantasydata.com/nfl-stats/nfl-fantasy-football-stats.aspx?fs=' + str(fsNum) + '&stype=' + str(seasonType) + '&sn=' + str(nflYear) + '&scope=1&w=' + str(weekNumStart) + '&ew=' + str(weekNumStop) + '&s=&t=' + str(team) + '&p=' + str(position) + '&st=' + str(scoringType) + '&d=1&ls=&live=false&pid=false&minsnaps=4'
    #queryurl = 'https://fantasydata.com/FantasyStatsNFL/FantasyStats_Read?sort=FantasyPointsDraftKings-desc&pageSize=2500&group=&filter=&filters.position=4&filters.team=&filters.teamkey=&filters.season=2018&filters.seasontype=1&filters.scope=2&filters.subscope=1&filters.redzonescope=&filters.scoringsystem=4&filters.leaguetype=&filters.searchtext=&filters.week=&filters.startweek=1&filters.endweek=17&filters.minimumsnaps=&filters.teamaspect=&filters.stattype=&filters.exportType=&filters.desktop=&filters.dfsoperator=&filters.dfsslateid=&filters.dfsslategameid=&filters.dfsrosterslot=&filters.page=&filters.showfavs=&filters.posgroup=&filters.oddsstate=&filters.aggregatescope=1&filters.rangescope=&filters.range=1'

    # RESPONSE: {"Data":[{"PlayerID":16765,"Season":2018,"Played":1,"Started":1,"Week":14,"Opponent":"PHI","TeamHasPossession":false,"HomeOrAway":null,"TeamIsHome":true,"Result":"W","HomeScore":29,"AwayScore":23,"Quarter":"F/OT","QuarterDisplay":"F/OT","IsGameOver":true,"GameDate":"\/Date(1544390700000)\/","TimeRemaining":null,"ScoreSummary":"F/OT (W) 29 - 23 vs. PHI","PassingCompletions":0,"PassingAttempts":0,"PassingCompletionPercentage":0,"PassingYards":0,"PassingYardsPerAttempt":0,"PassingTouchdowns":0.00,"PassingInterceptions":0.00,"PassingRating":0,"RushingAttempts":0.00,"RushingYards":0.00,"RushingYardsPerAttempt":0,"RushingTouchdowns":0.00,"Receptions":10.00,"ReceivingTargets":13.00,"ReceivingYards":217.00,"ReceptionPercentage":76.9,"ReceivingTouchdowns":3.00,"ReceivingLong":75.00,"ReceivingYardsPerTarget":16.7,"ReceivingYardsPerReception":21.7,"Fumbles":0.00,"FumblesLost":0.00,"FieldGoalsMade":0.00,"FieldGoalsAttempted":0.00,"FieldGoalPercentage":0,"FieldGoalsLongestMade":0.00,"ExtraPointsMade":0.00,"ExtraPointsAttempted":0.00,"TacklesForLoss":0.00,"Sacks":0.00,"QuarterbackHits":0.00,"Interceptions":0.00,"FumblesRecovered":0.00,"Safeties":0.00,"DefensiveTouchdowns":0,"SpecialTeamsTouchdowns":0,"SoloTackles":0.00,"AssistedTackles":0.00,"SackYards":0.00,"PassesDefended":0.00,"FumblesForced":0.00,"FantasyPoints":39.70,"FantasyPointsPPR":49.70,"FantasyPointsFanDuel":44.70,"FantasyPointsYahoo":44.70,"FantasyPointsFantasyDraft":52.70,"FantasyPointsDraftKings":52.70,"FantasyPointsHalfPointPpr":44.70,"FantasyPointsSixPointPassTd":39.70,"FantasyPointsPerGame":39.7,"FantasyPointsPerGamePPR":49.7,"FantasyPointsPerGameFanDuel":44.7,"FantasyPointsPerGameYahoo":44.7,"FantasyPointsPerGameDraftKings":52.7,"FantasyPointsPerGameHalfPointPPR":44.7,"FantasyPointsPerGameSixPointPassTd":39.7,"FantasyPointsPerGameFantasyDraft":52.7,"PlayerUrlString":"/nfl/amari-cooper-fantasy/16765","GameStatus":"","GameStatusClass":"","PointsAllowedByDefenseSpecialTeams":null,"TotalTackles":0.00,"StatSummary":[{"Items":[{"StatValue":"13","StatTitle":"TGT"},{"StatValue":"10","StatTitle":"REC"},{"StatValue":"217","StatTitle":"YDS"},{"StatValue":"3","StatTitle":"TD"}]}],"Name":"Amari Cooper","ShortName":"A. Cooper","FirstName":"Amari","LastName":"Cooper","FantasyPosition":"WR","Position":"WR","TeamUrlString":"/nfl/team-details/DAL","Team":"DAL","IsScrambled":false,"Rank":1,"StaticRank":0,"PositionRank":null,"IsFavorite":false}],"Total":2537,"AggregateResults":null,"Errors":null}
    #Year	Season	Rk	Player	Pos	Week	Team
    #return filtered array
    #filter(lambda x:x[1]=='test',list)

    lowYear = 2010
    highYear = thisYear + 1
    if (theYear > 0) : #if year passed in we only need to do 1 loop for this one year
      lowYear = theYear
      highYear = theYear + 1
      
    logResultsArr=[]
    
    for yearNum in range(lowYear, highYear):
      for seasonTypeNum in seasonTypes:
        #first set the low and high week numbers which go with the seasonType (1-4 for pre and post, and 1-17 for reg)
        lowWeek = seasonTypeWeeks[seasonTypeNum][0]
        highWeek = seasonTypeWeeks[seasonTypeNum][1] + 1
        if (theWeek > 0): #this means we just want a single week
          lowWeek = theWeek
          highWeek = theWeek + 1
        #for position in positions: #removing position since we can get all positions in one shot.
        for weekNum in range(lowWeek, highWeek):

          file_path = path + "fantasydata_" + str(yearNum) + "_" + seasonTypes[seasonTypeNum] + "_" + str(weekNum) + ".csv"
          statsJsonText = Data_Manager.load_data_for_query(file_path, 'FantasyStats_Read', yearNum, seasonTypeNum, weekNum, forceReload, logResultsArr)

          file_path2 = path + "fantasysnaps_" + str(yearNum) + "_" + seasonTypes[seasonTypeNum] + "_" + str(weekNum) + ".json"
          snapsJsonText = Data_Manager.load_data_for_query(file_path2, 'SnapCounts_Read', yearNum, seasonTypeNum, weekNum, forceReload, logResultsArr)
          
          file_path3 = path + "fantasysalary_" + str(yearNum) + "_" + seasonTypes[seasonTypeNum] + "_" + str(weekNum) + "_MAIN.json"
          slateJsonText = Data_Manager.load_data_for_slate(file_path3, 'Slates_Read', yearNum, seasonTypeNum, weekNum, forceReload, logResultsArr)
          
          Data_Manager.combine_on_player_id(statsJsonText, snapsJsonText, slateJsonText, yearNum, seasonTypes[seasonTypeNum], weekNum)
          
          '''
          THIS IS WHERE WE WILL STORE JSON IN DJANGO MODELS DB
          '''
          #Player_Game_Stats.objects.create_with_json(jsonStatsText=statsJsonText, jsonSnapsText=snapsJsonText, seasonType=seasonTypes[seasonTypeNum])
          '''
          END STORE JSON IN DJANGO MODELS DB
          '''
          
          data["success"] = "true"
        #END OF WEEK LOOP
      #END OF SEASON TYPE LOOP
    #END OF YEAR LOOP

    data["logResults"] = '\n'.join(logResultsArr)
    return data

  '''
  *****************************************************************************************
  COMBINE JSON files into a single one by playerID
  Note: this only works with json passed in that is alreay filtered by year, week and seasontype
  *****************************************************************************************
  '''
  def combine_on_player_id(statsJsonText, snapsJsonText, slateJsonText, yearNum, seasonType, weekNum):
    path = SITE_ROOT + STATIC_PROJECTS + 'downloaded_stats' + '/'
    main_list = []
    l2 = []
    l3 = []
    try :
      main_list = json.loads(statsJsonText).get('Data',[])
      l2 = json.loads(snapsJsonText).get('Data',[])
      l3 = json.loads(slateJsonText).get('Data',[])
    except :
      logResultsArr.append('Cant parse json for : ' + str(yearNum) + ' week: ' + str(weekNum))

    for indx, line in enumerate(main_list):
      if ('PlayerID' in line.keys()):
        for l in (l2, l3):
          for elem in l:
            if (elem.get('PlayerID', '') == line.get('PlayerID', '')):
              line.update(elem)
      
    string_json = json.dumps(main_list)
    file_path = path + "fantasyall_" + str(yearNum) + "_" + seasonType + "_" + str(weekNum) + ".json"
    append_write = 'wb' # make a new file if not
    file = open(file_path, append_write) 
    file.write(str(string_json).encode('utf-8')) 
    file.close()
    
    return string_json      
    #combined_values = d.values()

  # end of combine_on_player_id
  '''
  *****************************************************************************************
  LOAD THE PRIOR WEEKS DATA FOR A TEAM
  *****************************************************************************************
  '''
  def update_weekdata_for_team(analysisYear, analysisWeek, thisSeason, site, teamInitial, reload):
    data = {"errorMsg":"","success":"","playerData":[]}

    season = thisSeason
    thisWeek = analysisWeek
    thisYear = int((datetime.today() - timedelta(days=60)).year) # subtracting 60 days since some games played into new year
    teams = ['ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC','LAC','LAR','MIA','MIN','NE','NO','NYG','NYJ','OAK','PHI','PIT','SEA','SF','TB','TEN','WAS']
    positions = {2:'QB',3:'RB',4:'WR',5:'TE',11:'DST',10:'K'}
    seasonTypes = {0:'REG',1:'PRE',2:'POST'}
    #weeksArr = [{'weekStart':0, 'weekStop':4, 'season':0},{'weekStart':5, 'weekStop':9, 'season':0},{'weekStart':10, 'weekStop':14, 'season':0},{'weekStart':15, 'weekStop':16, 'season':0},{'weekStart':1, 'weekStop':4, 'season':1},{'weekStart':0, 'weekStop':3, 'season':2}]

    seasonType = 0 #0 reg, 1 pre, 2 post
    if (season == "Post") :
      seasonType = 2
    elif (season == "Pre") :
      seasonType = 1

    if (thisWeek == 1 and seasonType == 0) :
      #Reg season week 1 so set to week 4 of preseaons
      seasonType = 1
      season = "Pre"
      thisWeek = 4
      weekNumStart = 4 
      weekNumStop = 4
    elif (thisWeek == 1 and seasonType == 1)  :
      #nothing before this - so lets just try to load same week
      weekNumStart = 1
      weekNumStop = 1
    elif (seasonType == 1)  :
      #preseason is 1 based weeks - so lets subtract 1 for last week
      weekNumStart = thisWeek - 1
      weekNumStop = thisWeek - 1
    elif (thisWeek == 1 and seasonType == 2)  :
      #post season  week 1 so set to reg season week 17
      seasonType = 0
      season = "Week"
      thisWeek = 17
      weekNumStart = 17
      weekNumStop = 17
    else  :
      #all other reg season and post season is negative 2 since they are zero based
      thisWeek = thisWeek - 1 #this is the friendly view of last weeks number
      weekNumStart = thisWeek - 1 #now take away another 1 for zero base
      weekNumStop = thisWeek - 1 #now take away another 1 for zero base

    #team = 1 #1 to 32 as in array above.
    #position = 4 #2-QB, 3-RB, 4-WR, 5-TE, 11-DST
    scoringType = 'FantasyPointsDraftKings' 
    fsNum = 3 #3 = DK  2 = FD
    if (site == "Fanduel"):
      fsNum = 2 #2 = Fanduel
      scoringType = 'FantasyPointsFanDuel'
    #nflYear = analysisYear #this will get subtracted from current year to get integer for sn value
    #nflYear = int(datetime.now().year)-nflYear
    year = analysisYear
    nflYear = thisYear - year
    txtYear = str(thisYear - nflYear)
    path = SITE_ROOT + STATIC_PROJECTS + 'historical' + '/'
    #queryurl = 'https://fantasydata.com/nfl-stats/nfl-fantasy-football-stats.aspx?fs=' + str(fsNum) + '&stype=' + str(seasonType) + '&sn=' + str(nflYear) + '&scope=1&w=' + str(weekNumStart) + '&ew=' + str(weekNumStop) + '&s=&t=' + str(team) + '&p=' + str(position) + '&st=' + str(scoringType) + '&d=1&ls=&live=false&pid=false&minsnaps=4'

    #Year	Season	Rk	Player	Pos	Week	Team
    #return filtered array
    #filter(lambda x:x[1]=='test',list)


    for pos in positions:
      if (not (site == "DK" and positions[pos] == "K")):
        position = pos
        headerRow = ''
        fantasydataRows = []
  
        '''
        CHECK EXISTING FIRST
        '''
        file_path = path + "fantasydata_" + site + "_" + positions[pos] + ".csv"

        with open(file_path, 'r') as content_file:
          player_content = content_file.read()

        forceReload = False
        if (reload == "true") :
          forceReload = True
        foundMatch = False

        newPlayerArray = []
        newPlayerTxtArray = []
        for playerline in player_content.splitlines():
          if playerline.strip():
            playerVals = playerline.strip().split(',')
            if (len(playerVals) > 6 and str(playerVals[0]) == txtYear and str(playerVals[1]) == seasonTypes[seasonType] and str(playerVals[5]) == str(thisWeek) and  str(playerVals[6]) ==  teamInitial):
              if (not forceReload) : #only add matching rows if we are not force reloading
                newPlayerArray.append(playerVals)
                newPlayerTxtArray.append(playerline.strip())
              foundMatch = True
            else: #no match
              newPlayerArray.append(playerVals)
              newPlayerTxtArray.append(playerline.strip())

        if (not foundMatch and not forceReload) :
          forceReload = True #if we didn't find a match and we are not forcing a reload then we need to reload anyhow
        '''
        END CHECK EXISTING FIRST
        '''
        if (forceReload) :
          if (foundMatch) : #only need to rewrite data to file if we found a match since that means we are removing rows so we can reload them below
            playerText = "\n".join(newPlayerTxtArray) + '\n'
            file = open(file_path, 'wb') 
            file.write(str(playerText).encode('utf-8')) 
            file.close()

          #for teamIndex in range(len(teams)):
          try:
            teamIndex = teams.index(teamInitial)
            team = teamIndex + 1
            teamTxt = teams[teamIndex]
            queryurl = 'https://fantasydata.com/nfl-stats/nfl-fantasy-football-stats.aspx?fs=' + str(fsNum) + '&stype=' + str(seasonType) + '&sn=' + str(nflYear) + '&scope=1&w=' + str(weekNumStart) + '&ew=' + str(weekNumStop) + '&s=&t=' + str(team) + '&p=' + str(position) + '&st=' + str(scoringType) + '&d=1&ls=&live=false&pid=false&minsnaps=4'

            #filename = 'fantasydata_' + teamTxt + '_' + positions[position] + '_'  + txtYear + '_'  + seasonTypes[seasonType] + '_'  + str(weekNumStart + 1) + '_'  + str(weekNumStop + 1) + ''

            try:
                r = requests.get(queryurl, headers={'User-Agent': 'Mozilla/5.0'})
            except requests.exceptions.RequestException as e:  # This is the correct syntax
              try:
                  r = requests.get(queryurl, headers={'User-Agent': 'Mozilla/5.0'})
              except requests.exceptions.RequestException as e:  # This is the correct syntax
                try:
                    r = requests.get(queryurl, headers={'User-Agent': 'Mozilla/5.0'})
                except requests.exceptions.RequestException as e:  # This is the correct syntax
                    logging.debug(e)
                    sys.exit(1)
    

            # r = requests.get(thisUrl, headers={'User-Agent': 'Googlebot'}) #this is not working for some sites
            html = r.text
            # logging.debug('Debug for : ' + str(html))
            # logging.debug('Debug for : ' + str(r.status_code))
            # logging.debug('Debug for : ' + str(r.raise_for_status()))

            soup = BeautifulSoup(html, 'html.parser', from_encoding="utf-8")

            fantasydata = soup.find(id="StatsGrid")
            if (fantasydata is not None):
              datatext = fantasydata.get_text(separator=u' ')
              datatextlines = list(line.strip() for line in datatext.splitlines() if not line.isspace() and line.strip())
              newdatalines = []
              if (teamIndex == 0 and len(datatextlines) > 1) :
                headerRow = 'Year,Season,' + datatextlines[0].replace('Fantasy Points','FantasyPts').replace('QB Rating','QBRating').replace('QB Hits','QBHits').replace('Fum Rec','FumRec').replace('Def TD','DefTD').replace('Return TD','ReturnTD').replace('Pts Allowed','PtsAllowed').replace('FG Made','FGMade').replace('FG Att','FGAtt').replace('XP Made','XPMade').replace('XP Att','XPAtt').replace('/','Per').replace(' ',',')
              for thisline in datatextlines[1:]:
                logging.debug('Debug : ' + str(thisline))
                newline = thisline.replace(' ', ',', 1)
                newparts = newline.split(' ' + positions[position] + ' ')
                if (len(newparts) != 2 and positions[position] == 'RB'):
                  newparts = newline.split(' FB ')
                if (len(newparts) != 2 and positions[position] == 'RB'):
                  newparts = newline.split(' HB ')
                if (len(newparts) != 2 and positions[position] == 'RB'):
                  newparts = newline.split(' TB ')
                if (len(newparts) != 2 and positions[position] == 'RB'):
                  newparts = newline.split(' SB ')
                if (len(newparts) == 2):
                  newline = newparts[0] + ',' + positions[position] + ',' + newparts[1].replace(' ', ',')

                thisTxtLine = txtYear + ',' + seasonTypes[seasonType] + ',' + newline
                newdatalines.append(thisTxtLine)
                newPlayerArray.append(thisTxtLine.split(","))

              fantasydataRows.extend(newdatalines)

            #Write file out per position type and year
            if (len(fantasydataRows) > 0):
              datatext = "\n".join(fantasydataRows) + '\n'
              #urlfiledata[1] = path + "fantasydata_" + filename + ".txt"
              #file = open(path + "fantasydata_" + filename + ".txt",'wb') 
              if os.path.exists(file_path):
                append_write = 'ab' # append if already exists
              else:
                append_write = 'wb' # make a new file if not
                datatext = headerRow + '\n' + datatext
              file = open(file_path, append_write) 
              file.write(str(datatext).encode('utf-8')) 
              file.close()
    
            data["success"] = "true"
            data["playerData"] = newPlayerArray
          except ValueError:
            data["errorMsg"] = "Error - Team Initials do not exist"
        else: #not forceReload
          data["success"] = "true"
          data["playerData"] = newPlayerArray
      # END of IF NOT Kicker and DK
    # END OF FOR LOOP (pos in positions)
  
    return data

  '''
  *****************************************************************************************
  Just check if the historical data is loaded for the last week - otherwise return error
  TODO - replace above with call to this function
  *****************************************************************************************
  '''
  def getLastWeekDataIfExists(analysisYear, analysisWeek, thisSeason, site, teamInitial, reload, position):
    data = {"errorMsg":"","success":"","forceReload":False,"foundMatch":False,"thisYearsPlayerArray":[],"thisYearsPlayerTxtArray":[],"lastWeeksPlayerArray":[],"lastWeeksPlayerTxtArray":[]}

    season = thisSeason
    thisWeek = analysisWeek
    thisYear = int((datetime.today() - timedelta(days=60)).year) # subtracting 60 days since some games played into new year
    teams = ['ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC','LAC','LAR','MIA','MIN','NE','NO','NYG','NYJ','OAK','PHI','PIT','SEA','SF','TB','TEN','WAS']
    positions = {2:'QB',3:'RB',4:'WR',5:'TE',11:'DST',10:'K'}
    seasonTypes = {0:'REG',1:'PRE',2:'POST'}
  
    seasonType = 0 #0 reg, 1 pre, 2 post
    if (season == "Post") :
      seasonType = 2
    elif (season == "Pre") :
      seasonType = 1

    if (thisWeek == 1 and seasonType == 0) :
      #Reg season week 1 so set to week 4 of preseaons
      seasonType = 1
      season = "Pre"
      thisWeek = 4
      weekNumStart = 4 
      weekNumStop = 4
    elif (thisWeek == 1 and seasonType == 1)  :
      #nothing before this - so lets just try to load same week
      weekNumStart = 1
      weekNumStop = 1
    elif (seasonType == 1)  :
      #preseason is 1 based weeks - so lets subtract 1 for last week
      weekNumStart = thisWeek - 1
      weekNumStop = thisWeek - 1
    elif (thisWeek == 1 and seasonType == 2)  :
      #post season  week 1 so set to reg season week 17
      seasonType = 0
      season = "Week"
      thisWeek = 17
      weekNumStart = 17
      weekNumStop = 17
    else  :
      #all other reg season and post season is negative 2 since they are zero based
      thisWeek = thisWeek - 1 #this is the friendly view of last weeks number
      weekNumStart = thisWeek - 1 #now take away another 1 for zero base
      weekNumStop = thisWeek - 1 #now take away another 1 for zero base

    scoringType = 'FantasyPointsDraftKings' 
    fsNum = 3 #3 = DK  2 = FD
    if (site == "Fanduel"):
      fsNum = 2 #2 = Fanduel
      scoringType = 'FantasyPointsFanDuel'
    year = analysisYear
    nflYear = thisYear - year
    txtYear = str(thisYear - nflYear)
    path = SITE_ROOT + STATIC_PROJECTS + 'historical' + '/'
    teamInit = teamInitial

    headerRow = ''
    fantasydataRows = []

    if (not (position == 'K' and site == 'DK')) :
      '''
      CHECK EXISTING FIRST
      '''
      file_path = path + "fantasydata_" + site + "_" + position + ".csv"
      if (os.path.exists(file_path)):
        with open(file_path, 'r') as content_file:
          player_content = content_file.read()

        forceReload = False
        if (reload == "true") :
          forceReload = True
        foundMatch = False

        lastWeeksPlayerDict = {}
        lastWeeksPlayerArray = []
        lastWeeksPlayerTxtArray = []
        newPlayerArray = []
        newPlayerTxtArray = []
        for playerline in player_content.splitlines():
          if playerline.strip():
            playerVals = playerline.strip().split(',')
            if (teamInitial == '') : 
              teamInit = str(playerVals[6]) #if passed an empty string for team then don't check for Team in results - just check for week, season, year.
            if (len(playerVals) > 6 and str(playerVals[0]) == txtYear and str(playerVals[1]) == seasonTypes[seasonType] and str(playerVals[5]) == str(thisWeek) and  str(playerVals[6]) ==  teamInit):
              if (not forceReload) : #only add matching rows if we are not force reloading
                newPlayerArray.append(playerVals)
                newPlayerTxtArray.append(playerline.strip())
              foundMatch = True
              dictKeyName = playerVals[3] + "_" + playerVals[4] + "_" + playerVals[6]
              lastWeeksPlayerDict[dictKeyName] = playerVals
              lastWeeksPlayerArray.append(playerVals)
              lastWeeksPlayerTxtArray.append(playerline.strip())
            else: #no match
              newPlayerArray.append(playerVals)
              newPlayerTxtArray.append(playerline.strip())

        if (not foundMatch and not forceReload) :
          forceReload = True #if we didn't find a match and we are not forcing a reload then we need to reload anyhow
        data["thisYearsPlayerArray"] = newPlayerArray
        data["thisYearsPlayerTxtArray"] = newPlayerTxtArray
        data["lastWeeksPlayerDict"] = lastWeeksPlayerDict
        data["lastWeeksPlayerArray"] = lastWeeksPlayerArray
        data["lastWeeksPlayerTxtArray"] = lastWeeksPlayerTxtArray
        data["forceReload"] = forceReload
        data["foundMatch"] = foundMatch
        data["success"] = 'true'
      else :
        data["errorMsg"] = "Error: File does not exist for Site and Position"

      '''
      END CHECK EXISTING FIRST
      '''
    else:
      data["thisYearsPlayerArray"] = []
      data["thisYearsPlayerTxtArray"] = []
      data["lastWeeksPlayerDict"] = {}
      data["lastWeeksPlayerArray"] = []
      data["lastWeeksPlayerTxtArray"] = []
      data["forceReload"] = False
      data["foundMatch"] = False
      data["success"] = 'true'

    # END if not Kicker and DK
    return data

  '''
  *****************************************************************************************
  RELOAD SLATE SALARY DATA
  *****************************************************************************************
  '''
  def reload_salary_files(analysisYear, analysisWeek, season, site):
    data = {"errorMsg":"","success":"","slates":[]}

    weekTxt = str(season) + str(analysisWeek)

    slatesList = []
    salaryColHeads = ""
    file_path = SITE_ROOT + STATIC_PROJECTS + 'weekupdate' + '/' + str(analysisYear) + '/' + str(weekTxt) + '/' + site + '/'
    salary_path = SITE_ROOT + STATIC_PROJECTS + 'salary' + '/' + str(analysisYear) + '/' + str(weekTxt) + '/' + site + '/'
    slate_file = file_path + 'slates.csv'
  
    extension = '.csv' # this is the extension you want to detect

    if (analysisWeek != 0 and analysisYear != 0 and analysisWeek > 0 and analysisWeek < 18 and analysisYear > 2012 and analysisYear <= (datetime.now().year + 1)) :
      # Loop through all CSV files in the appropriate Year and Week folder to get list of slate files and player salaries
      for root, dirs_list, files_list in os.walk(salary_path):
        for file_name in files_list:
          if os.path.splitext(file_name)[-1] == extension:
            allVals = []
            '''
            print file_name
            print file_name_path   # This is the full path of the filter file    
            '''
            file_name_path = os.path.join(root, file_name)
            just_name = file_name[:-4]
            slateInfo = [str(analysisYear),str(weekTxt),str(just_name)]
            slatesList.append(str(just_name))
            # READ SALARY FILE
            with open(file_name_path, 'r') as content_file:
              salary_content = content_file.read()
            foundHeading = False
          
          
            csvLines = csv.reader(salary_content.splitlines(), quotechar='"', delimiter=',', quoting=csv.QUOTE_MINIMAL, skipinitialspace=True)
          
            for salaryVals in csvLines:
              #if groupline.strip():
              #salaryVals = groupline.strip().split(',')
              if (site == "DK"):
                if (len(salaryVals) > 10) :
                  theseVals = [x.strip() for x in salaryVals[10:]]
                  if (len(theseVals) > 0):
                    if (foundHeading) :
                      newVals = []
                      newVals.extend(slateInfo)
                      newVals.extend([theseVals[3],theseVals[2],theseVals[0],theseVals[5],theseVals[6],theseVals[7],'','0.0','',''])
                      allVals.append(",".join(newVals))
                    if (theseVals[0] == 'Position') :
                      foundHeading = True
                      newVals = ['Year','Week','Slate','ID','Name','Position','Salary','GameInfo','Team','Opponent','FPPG','InjuryStatus','InjuryDetails']
                      #newVals.extend(theseVals)
                      salaryColHeads = ",".join(newVals)
              elif (site == "Fanduel") :
                if (len(salaryVals) > 10) :
                  if (foundHeading) :
                    newVals = []
                    newVals.extend(slateInfo)
                    newVals.extend([salaryVals[0],salaryVals[3],salaryVals[1],salaryVals[7],salaryVals[8].replace("JAC","JAX"),salaryVals[9].replace("JAC","JAX"),salaryVals[10].replace("JAC","JAX"),salaryVals[5],salaryVals[11],salaryVals[12]])
                    allVals.append(",".join(newVals))
                  if (salaryVals[0] == 'Id') :
                    foundHeading = True
                    newVals = ['Year','Week','Slate','ID','Name','Position','Salary','GameInfo','Team','Opponent','FPPG','InjuryStatus','InjuryDetails']
                    #newVals.extend(salaryVals)
                    salaryColHeads = ",".join(newVals)
                
            # READ SALARY FILE END

            # Write our CSV to files 
            salary_file = file_path + 'slate_salaries_' + just_name + '.csv'
            strToWrite1 = ""
            strToWrite2 = ""
            if (salaryColHeads) :
              strToWrite1 = salaryColHeads + "\n"
            if (len(allVals) > 0) :
              strToWrite2 = "\n".join(allVals) + "\n"
            file = open(salary_file,'wb') 
            file.write(str(str(strToWrite1) + str(strToWrite2)).encode('utf-8')) 
            file.close()

      strToWrite1 = ""
      if (len(slatesList) > 0):
        strToWrite1 = "\n".join(slatesList) + "\n"
        data["slates"] = slatesList
        data["success"] = "true"
        file = open(slate_file,'wb') 
        file.write(str(strToWrite1).encode('utf-8')) 
        file.close()
      else :
        data["errorMsg"] = "Error: no slate files found. Please add CSV files to week folder for site"

    else:
      data["errorMsg"] = "Error in data submitted - Need Week and Year"

    return data

  '''
  *****************************************************************************************
  GET THE SALARY DATA FOR A SLATE
  *****************************************************************************************
  '''
  def get_salary_data(analysisYear, analysisWeek, season, site, slate, reload):
    data = {"errorMsg":"","success":"","player_data":[]}

    weekTxt = str(season) + str(analysisWeek)
    playerList = []

    file_path = SITE_ROOT + STATIC_PROJECTS + 'weekupdate' + '/' + str(analysisYear) + '/' + str(weekTxt) + '/' + site + '/'
    salary_file = file_path + 'slate_salaries_' + slate + '.csv'

    player_content = ""
    if (analysisWeek != 0 and analysisYear != 0 and analysisWeek > 0 and analysisWeek < 18 and analysisYear > 2012 and analysisYear <= (datetime.now().year + 1)) :
      if (not os.path.exists(salary_file) or reload == 'true'):
        reloadStatus = Data_Manager.reload_salary_files(analysisYear, analysisWeek, season, site)
        if (reloadStatus["success"] != "true"):
          data["errorMsg"] = reloadStatus["errorMsg"]
    
      if (os.path.exists(salary_file)):
        with open(salary_file, 'r') as content_file:
          player_content = content_file.read()

        player_data = player_content.splitlines()
        if (len(player_data) > 0) :
          data["player_data"] = player_data
          data["success"] = "true"
        else :
          data["errorMsg"] = data["errorMsg"] + "Error: No players found for slate"
      else:
        data["errorMsg"] = data["errorMsg"] + "Error: No Slate Salary file found - try reloading salaries"
    else:
      data["errorMsg"] = "Error in data submitted - Need Week and Year"
 
    return data

