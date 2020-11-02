import sys
import logging
import time
import os
import re
import csv
import collections
from django.views import View
from django.views.generic import TemplateView
from jsonview.views import JsonView
from pandas.io.json import json_normalize
from django_pandas.io import read_frame

from nfl_research.constants import teamNames
from nfl_research.utilities import NFL_Utilities
from nfl_research.data_manager import Data_Manager
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
STATIC_DATA = '/static/data/'
STATIC_PROJECTS = '/static/projects/'

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
class MyView(View):
    def get(self, request):
        # <view logic>
        return HttpResponse('result')

'''
*****************************************************************************************
DEFAULT NFL_RESEARCH HOME 
*****************************************************************************************
'''
class Home(TemplateView):
  template_name = "home.html"
  
  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    return data


def create_project(request):
  from nltk.corpus import stopwords
  ignored_words = stopwords.words('english')

  if request.method == "POST":
    projectname = request.POST.get('projectname', '')
    csvdata = request.POST.get('urls', '')
    overwrite = request.POST.get('overwrite', False)

    # logging.debug('Debug for projectname : ' + str(projectname))
    # logging.debug('Debug for csvdata : ' + str(csvdata))
    errorMsg = ""
    if (projectname == ''):
      errorMsg = "You must provide a Project Name"
    else:
      # logging.debug('Debug for 1 ' + str(errorMsg))
      if (not (re.match(r'[\w-]+$', projectname))):
        errorMsg = "Your name contains illegal characters.  Please use only letters, numbers, _, or -"
        # logging.debug('Debug for 2 ' + str(errorMsg))
      else:
        # logging.debug('Debug for 3 ' + str(errorMsg))
        if (csvdata == ''):
          errorMsg = "You must provide your list of URLs"
        else:
          # logging.debug('Debug for 4 ' + str(errorMsg))
          csvdataArray = csvdata.splitlines()
          if (len(csvdataArray) <= 0):
            errorMsg = "Error parsing CSV data - check please"
          else:
            # logging.debug('Debug for 5 ' + str(errorMsg))
            colHeads = csvdataArray[0].split(',')
            if (len(colHeads) < 1 or colHeads[0].lower() != 'url'):
              errorMsg = "Your first row must start with headers : url,..."
            elif (len(colHeads) >= 1):
              if (colHeads[0].lower() != 'url'):
                errorMsg = "Your first row must start with headers : url,..."
              else:
                # Now we have good headers - lets populate our list skip first row
                # logging.debug('Debug for 6 ' + str(errorMsg))
                projectdata = []
                projectdata.append(csvdataArray[0] + ',htmlfile,textfile,linksfile,navfile,bodyfile,wordcount')
                tidydata = []
                attrHeads = ','.join(colHeads)
                tidydata.append(attrHeads + ',raw_location,raw_percent,scrub_location,scrub_percent,word')
                fdTextArray = []

                path = SITE_ROOT + STATIC_PROJECTS + projectname + '/'

                if (os.path.exists(path) and not overwrite):
                  errorMsg = "A Project with that name already exists - please rename or check to overwrite."
                else:
                  if (not os.path.exists(path)):
                    os.makedirs(path)
                  zf = zipfile.ZipFile(path + 'alldata.zip', mode='w')
                  zf.close()
                  # logging.debug('Debug for 7 : ' + str(path))
                  
                  thisYear = int((datetime.today() - timedelta(days=60)).year) # subtracting 60 days since some games played into new year
                  teams = ['ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC','LAC','LAR','MIA','MIN','NE','NO','NYG','NYJ','OAK','PHI','PIT','SEA','SF','TB','TEN','WAS']
                  positions = {2:'QB',3:'RB',4:'WR',5:'TE',11:'DST',10:'K'}
                  seasonTypes = {0:'REG',1:'PRE',2:'POST'}
                  #weeksArr = [{'weekStart':0, 'weekStop':4, 'season':0},{'weekStart':5, 'weekStop':9, 'season':0},{'weekStart':10, 'weekStop':14, 'season':0},{'weekStart':15, 'weekStop':16, 'season':0},{'weekStart':1, 'weekStop':4, 'season':1},{'weekStart':0, 'weekStop':3, 'season':2}]
                  weeksArr = [{'weekStart':0, 'weekStop':4, 'season':0},{'weekStart':5, 'weekStop':9, 'season':0},{'weekStart':1, 'weekStop':4, 'season':1}]
                  weekNumStart = 1 #this will get -1 since zero based.  Put real week here
                  weekNumStart = weekNumStart - 1
                  weekNumStop = 5 #this will get -1 since zero based.  Put real week here
                  weekNumStop = weekNumStop - 1
                  seasonType = 0 #0 reg, 1 pre, 2 post
                  team = 1 #1 to 32 as in array above.
                  position = 4 #2-QB, 3-RB, 4-WR, 5-TE, 11-DST
                  site = "Fanduel"
                  scoringType = 'FantasyPointsDraftKings' 
                  fsNum = 3
                  if (site == "Fanduel"):
                    fsNum = 2
                    scoringType = 'FantasyPointsFanDuel'

                  nflYear = 2016 #this will get subtracted from current year to get integer for sn value
                  nflYear = thisYear-nflYear
          
                  queryurl = 'https://fantasydata.com/nfl-stats/nfl-fantasy-football-stats.aspx?fs=' + str(fsNum) + '&stype=' + str(seasonType) + '&sn=' + str(nflYear) + '&scope=1&w=' + str(weekNumStart) + '&ew=' + str(weekNumStop) + '&s=&t=' + str(team) + '&p=' + str(position) + '&st=' + str(scoringType) + '&d=1&ls=&live=false&pid=false&minsnaps=4'
                  
                  fantasyDataWeek = False
                  fantasyDataHistory = True
                  allGames = False
                  gameinformation = False
                  
                  if (fantasyDataHistory == True):
                    for pos in positions:
                      position = pos

                      headerRow = ''
                      year = 2018
                      while (year > 2017) :
                        year = year - 1
                        nflYear = thisYear - year
                        fantasydataRows = []
                      
                        for weekObj in weeksArr:
                          weekNumStart = weekObj['weekStart']
                          weekNumStop = weekObj['weekStop']
                          seasonType = weekObj['season']
                  
                          for teamIndex in range(len(teams)):
                            team = teamIndex + 1
                            teamTxt = teams[teamIndex]
                            queryurl = 'https://fantasydata.com/nfl-stats/nfl-fantasy-football-stats.aspx?fs=' + str(fsNum) + '&stype=' + str(seasonType) + '&sn=' + str(nflYear) + '&scope=1&w=' + str(weekNumStart) + '&ew=' + str(weekNumStop) + '&s=&t=' + str(team) + '&p=' + str(position) + '&st=' + str(scoringType) + '&d=1&ls=&live=false&pid=false&minsnaps=4'
                    
                            txtYear = str(thisYear - nflYear)
                            filename = 'fantasydata_' + teamTxt + '_' + positions[position] + '_'  + txtYear + '_'  + seasonTypes[seasonType] + '_'  + str(weekNumStart + 1) + '_'  + str(weekNumStop + 1) + ''

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
                                headerRow = 'Year,Season,' + datatextlines[0].replace('Fantasy Points','FantasyPts').replace('QB Rating','QBRating').replace('QB Hits','QBHits').replace('Fum Rec','FumRec').replace('Def TD','DefTD').replace('Return TD','ReturnTD').replace('Pts Allowed','PtsAllowed').replace('/','Per').replace(' ',',')
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

                                newdatalines.append(txtYear + ',' + seasonTypes[seasonType] + ',' + newline)
                        
                              fantasydataRows.extend(newdatalines)
                      
                        #Write file out per position type and year
                        datatext = "\n".join(fantasydataRows) + '\n'
                        #urlfiledata[1] = path + "fantasydata_" + filename + ".txt"
                        #file = open(path + "fantasydata_" + filename + ".txt",'wb') 
                        if os.path.exists(path + "fantasydata_" + site + "_" + positions[pos] + ".csv"):
                          append_write = 'ab' # append if already exists
                        else:
                          append_write = 'wb' # make a new file if not
                          datatext = headerRow + '\n' + datatext
                        file = open(path + "fantasydata_" + site + "_" + positions[pos] + ".csv",append_write) 
                        file.write(datatext.encode('utf-8')) 
                        file.close()
                        
                        
                  elif (fantasyDataWeek == True):
                    # TODO add code for appending new weeks data each week
                    logging.debug('Debug for week data ')
                    for pos in positions:
                      position = pos

                      headerRow = ''
                      year = 2017
                      nflYear = thisYear - year
                      txtYear = str(thisYear - nflYear)
                      fantasydataRows = []
                      
                      weekNumStart = 1
                      weekNumStop = 5
                      seasonType = 0
              
                      for teamIndex in range(len(teams)):
                        team = teamIndex + 1
                        teamTxt = teams[teamIndex]
                        queryurl = 'https://fantasydata.com/nfl-stats/nfl-fantasy-football-stats.aspx?fs=' + str(fsNum) + '&stype=' + str(seasonType) + '&sn=' + str(nflYear) + '&scope=1&w=' + str(weekNumStart) + '&ew=' + str(weekNumStop) + '&s=&t=' + str(team) + '&p=' + str(position) + '&st=' + str(scoringType) + '&d=1&ls=&live=false&pid=false&minsnaps=4'
                
                        filename = 'fantasydata_' + teamTxt + '_' + positions[position] + '_'  + txtYear + '_'  + seasonTypes[seasonType] + '_'  + str(weekNumStart + 1) + '_'  + str(weekNumStop + 1) + ''

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
                            headerRow = 'Year,Season,' + datatextlines[0].replace('Fantasy Points','FantasyPts').replace('QB Rating','QBRating').replace('QB Hits','QBHits').replace('Fum Rec','FumRec').replace('Def TD','DefTD').replace('Return TD','ReturnTD').replace('Pts Allowed','PtsAllowed').replace('/','Per').replace(' ',',')
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

                            newdatalines.append(txtYear + ',' + seasonTypes[seasonType] + ',' + newline)
                    
                          fantasydataRows.extend(newdatalines)
                  
                      #Write file out per position type and year
                      datatext = "\n".join(fantasydataRows) + '\n'
                      #urlfiledata[1] = path + "fantasydata_" + filename + ".txt"
                      #file = open(path + "fantasydata_" + filename + ".txt",'wb') 
                      if os.path.exists(path + "fantasydata_" + site + "_" + txtYear + "_" +  str(weekNumStart) + "_" + positions[pos] + ".csv"):
                        append_write = 'ab' # append if already exists
                      else:
                        append_write = 'wb' # make a new file if not
                        datatext = headerRow + '\n' + datatext
                      file = open(path + "fantasydata_" + site + "_" + txtYear + "_" +  str(weekNumStart) + "_" + positions[pos] + ".csv", append_write) 
                      file.write(datatext.encode('utf-8')) 
                      file.close()


                  
                  elif (allGames == True):
                    # https://www.pro-football-reference.com/years/2016/games.htm
                    headerRow = ''
                    year = 2015
                    while (year > 2012) :
                      year = year - 1

                      thisUrl = 'https://www.pro-football-reference.com/years/' + str(year) + '/games.htm'

                      txtYear = str(year)
                      filename = 'gamedata_' + txtYear + ''

                      urldata = ['url']
                      urlfiledata = ['','','','','','']

                      r = requests.get(thisUrl, headers={'User-Agent': 'Mozilla/5.0'})
                      html = r.text
                  
                      soup = BeautifulSoup(html, 'html.parser', from_encoding="utf-8")

                      urlfiledata[0] = path + filename + "--html.txt"
                      file = open(path + filename + "--html.txt",'wb') 
                      file.write(soup.prettify().encode('utf-8')) 
                      file.close()

                      fantasydata = soup.find(id="games")
                      fantasydata = fantasydata.find(name="tbody")
                      for thead in fantasydata.select('.thead'):
                        thead.extract()    # rip it out
            
                      justBoxscoreUrls = []
                      gametextlines = []
                      if (fantasydata is not None):
                        datatext = fantasydata.get_text(separator=u',')
                        datalinks = fantasydata.findAll('a', href=True)
                        gametextlines = list(line.strip().replace('@,','').replace(',N,',',').replace('boxscore,','') for line in datatext.splitlines() if not line.isspace() and line.strip() and line.strip() != ',' and line.strip() != ',Playoffs,')
                        
                        lineCnt = 0
                        for lineIndex in range(len(gametextlines)):
                          if len(gametextlines[lineIndex]) > 0:
                            gametextlines[lineIndex] = gametextlines[lineIndex][1:]
                          weekNum = gametextlines[lineIndex].split(',')[0]
                          if (len(datalinks) > (lineCnt + 2)):
                            justBoxscoreUrls.append('https://www.pro-football-reference.com' + datalinks[lineCnt+2]['href'])
                            gametextlines[lineIndex] = gametextlines[lineIndex] + 'https://www.pro-football-reference.com' + datalinks[lineCnt]['href'] + ',' + 'https://www.pro-football-reference.com' + datalinks[lineCnt+1]['href'] + ',' + 'https://www.pro-football-reference.com' + datalinks[lineCnt+2]['href']
                          lineCnt = lineCnt + 3

                        
                        datatext = "\n".join(gametextlines)
                        datatext = 'Week,Day,Date,Time,Winner/tie,Loser/tie,PtsWin,PtsLose,YdsWin,TurnOversWin,YdsLose,TurnOversLose,WinUrl,LoseUrl,GameUrl\n' +  datatext
                        urlfiledata[1] = path + filename + "--fantasydata.csv"
                        file = open(path + filename + "--fantasydata.csv",'wb') 
                        file.write(datatext.encode('utf-8')) 
                        file.close()                 

                        dataurls = "\n".join(justBoxscoreUrls)
                        urlfiledata[2] = path + filename + "--boxscoreurls.csv"
                        file = open(path + filename + "--boxscoreurls.csv",'wb') 
                        file.write(dataurls.encode('utf-8')) 
                        file.close()                

                      urldata.extend(urlfiledata)
                      projectdata.append(",".join(urldata))
                    
                      #now iterate through the URLs to get each games data:
                      if (len(gametextlines) > 0):
                        keysObj = {'Game':'','Week':''}
                        gamedataArr = []
                        snapsdataArr = []
                        for gameRow in gametextlines:
                          if (gameRow.strip() != ''):
                            gameRowArr = gameRow.split(',')
                            gameUrl = gameRowArr[-1]
                            gameId = gameUrl.replace('https://www.pro-football-reference.com/boxscores/','').replace('.htm','')
                            weekNum = gameRowArr[0]
                          
                            thisUrl = gameUrl
                          
                            if (gameUrl is not None and thisUrl != ''):
                              r = requests.get(gameUrl, headers={'User-Agent': 'Mozilla/5.0'})
                              html = r.text
                              html = html.replace("<!--", "<").replace("-->", ">")

                              soup = BeautifulSoup(html, 'html.parser', from_encoding="utf-8")

                              urlfiledata[0] = path + filename + gameId + "--html.txt"
                              file = open(path + filename + gameId + "--html.txt",'wb') 
                              file.write(soup.prettify().encode('utf-8')) 
                              file.close()
                      
                              gameinfo = soup.find(id="game_info")
                              #gameinfo = gameinfo.find(name="tbody")
                      
                              teamstats = soup.find(id="team_stats")                  
                              #teamstats = teamstats.find(name="tbody")

                              homesnaps = soup.find(id="home_snap_counts")                  
                              vissnaps = soup.find(id="vis_snap_counts")                  

                              if (homesnaps is not None and vissnaps is not None):
                                homesnaps = homesnaps.find(name="tbody")
                                vissnaps = vissnaps.find(name="tbody")
                                     
                              gamedataObj = {'Game':gameId,'Week':weekNum}

                              if (gameinfo is not None):
                                datatext = gameinfo.get_text(separator=u',,')
                                datatextlines = list(line.strip()[2:-2].strip() for line in datatext.splitlines() if not line.isspace() and line.strip() and line.strip() != ',,')
                        
                                for gamelineStr in datatextlines[1:]:
                                  gamelineKey = gamelineStr.split(',,')[0]
                                  gamelineVal = gamelineStr.split(',,')[1]
                                  gamedataObj[gamelineKey.strip()] = gamelineVal.strip()
                                  keysObj[gamelineKey.strip()] = ''

                              homeTeam = ''
                              visTeam = ''
                              if (teamstats is not None):
                                datatext = teamstats.get_text(separator=u',,')
                                datatextlines = list(line.strip()[2:-2].strip() for line in datatext.splitlines() if not line.isspace() and line.strip() and line.strip() != ',,')

                                if (len(datatextlines) > 3):
                                  gamedataObj['Home'] = datatextlines[2].strip()
                                  homeTeam = datatextlines[2].strip()
                                  gamedataObj['Visitor'] = datatextlines[1].strip()
                                  visTeam = datatextlines[1].strip()
                                  for gamelineStr in datatextlines[3:]:
                                    gamelineHomeKey = gamelineStr.split(',,')[0] + ' Home'
                                    gamelineHomeVal = gamelineStr.split(',,')[2]
                                    gamelineVisKey = gamelineStr.split(',,')[0] + ' Visitor'
                                    gamelineVisVal = gamelineStr.split(',,')[1]
                                    gamedataObj[gamelineHomeKey.strip()] = gamelineHomeVal.strip()
                                    gamedataObj[gamelineVisKey.strip()] = gamelineVisVal.strip()
                                    keysObj[gamelineHomeKey.strip()] = ''
                                    keysObj[gamelineVisKey.strip()] = ''

                                gamedataArr.append(gamedataObj); 

                              if (homesnaps is not None):
                                datatext = homesnaps.get_text(separator=u',')
                                datatextlines = list((txtYear + ',' + gameId + ',' + str(weekNum) + ',' + homeTeam + ',' + line.strip()[1:-1].strip()) for line in datatext.splitlines() if not line.isspace() and line.strip() and line.strip() != ',')

                                snapsdataArr.extend(datatextlines)

                              if (vissnaps is not None):
                                datatext = vissnaps.get_text(separator=u',')
                                datatextlines = list((txtYear + ',' + gameId + ',' + str(weekNum) + ',' + visTeam + ',' + line.strip()[1:-1].strip()) for line in datatext.splitlines() if not line.isspace() and line.strip() and line.strip() != ',')

                                snapsdataArr.extend(datatextlines)
                     
                        
                        #end of for in gamesUrls loop
                        if (len(snapsdataArr) > 0):
                          datatext = "\n".join(snapsdataArr) + "\n"
                          urlfiledata[3] = path + "snaps.csv"

                          if os.path.exists(path + "snaps.csv"):
                            append_write = 'ab' # append if already exists
                          else:
                            append_write = 'wb' # make a new file if not
                            datatext = 'Year,Game,Week,Team,Player,Pos,OffSnaps,OffPct,DefSnaps,DefPct,STSnaps,STPct\n' + datatext
                          file = open(path + "snaps.csv", append_write) 
                          file.write(datatext.encode('utf-8')) 
                          file.close()
                          
                        if (len(gamedataArr) > 0):
                          gamedataHeaderTxt = 'Year,Week,Day,Date,Time,Winner/tie,Loser/tie,PtsWin,PtsLose,YdsWin,TurnOversWin,YdsLose,TurnOversLose,' + ','.join(str(v) for v in keysObj.keys()) + '\n'
                          gamedataTxt = ''
                          for gamedataObjInx in range(len(gamedataArr)):
                            gamedataObj = gamedataArr[gamedataObjInx]
                            gamedataTxt = gamedataTxt + txtYear + ','
                            gamedataTxt = gamedataTxt + ','.join(str(v) for v in gametextlines[gamedataObjInx].split(',')[:-3]) + ','
                            gamedataVals = []
                            for thisKey in keysObj.keys():
                              if (thisKey in gamedataObj):
                                gamedataVals.append('"' + str(gamedataObj[thisKey]).replace('-', '~') + '"')
                              else:
                                gamedataVals.append('')
                            gamedataTxt = gamedataTxt + ','.join(gamedataVals) + '\n'


                          if os.path.exists(path + "gamestats.csv"):
                            append_write = 'ab' # append if already exists
                          else:
                            append_write = 'wb' # make a new file if not
                            gamedataTxt = gamedataHeaderTxt + gamedataTxt
                          urlfiledata[4] = path + "gamestats.csv"
                          file = open(path + "gamestats.csv", append_write) 
                          file.write(gamedataTxt.encode('utf-8')) 
                          file.close()                    
                    
                    
                    # logging.debug('Debug for 9 : ' + str(errorMsg))               
                    if (errorMsg == ""):
                      #now write out the project file csv to complete project creation
                      # logging.debug('Debug for 10 : ' + str(errorMsg)) 
                      file = open(path + "projectdata.csv",'wb') 
                      file.write("\n".join(projectdata).encode('utf-8')) 
                      file.close()

                  elif (gameinformation == True):
                    # populate based on previous get all urls:
                    gameId = '201609080den'
                    weekNum = 1
                    for thisDataStr in csvdataArray[1:]:
                      # logging.debug('Debug for 8 : ' + str(thisDataStr))
                      thisData = thisDataStr.split(",")
                      if (len(thisData) != len(colHeads)):
                        errorMsg = errorMsg + str(thisData[0]) + " row did not have the correct number of values.<br />"
                      thisUrl = thisData[0]
                      filename = thisUrl.replace(".", "_").replace("://", "_").replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_").replace("%", "_").replace("+", "_").replace(" ", "_")
                      urldata = []
                      urlfiledata = ['','','','','','']
                      urldata.extend(thisData)
                        
                      r = requests.get(thisUrl, headers={'User-Agent': 'Mozilla/5.0'})
                      # r = requests.get(thisUrl, headers={'User-Agent': 'Googlebot'}) #this is not working for some sites
                      html = r.text
                      html = html.replace("<!--", "<").replace("-->", ">")
                      # logging.debug('Debug for : ' + str(html))
                      # logging.debug('Debug for : ' + str(r.status_code))
                      # logging.debug('Debug for : ' + str(r.raise_for_status()))
                    
                              
                      #req = Request(thisUrl, headers={'User-Agent': 'Googlebot'}) #note: using googlebot as agent to prevent being blocked
                      #with urllib.request.urlopen(req) as response:
                      #  html = response.read()
                  
                      soup = BeautifulSoup(html, 'html.parser', from_encoding="utf-8")

                      urlfiledata[0] = path + filename + "--html.txt"
                      file = open(path + filename + "--html.txt",'wb') 
                      file.write(soup.prettify().encode('utf-8')) 
                      file.close()

                      '''
                      for script in soup(["script", "style"]):
                        script.decompose()    # rip it out
                      for comment in soup.find_all(string=lambda text:isinstance(text,Comment)):
                        comment.extract()    # rip it out
                      for hidden in soup.select('.hidden-lg,.hidden-md,.modal,.hidden,.hide,.lightbox'):
                        hidden.extract()    # rip it out
                        
                      '''
                      
                      gameinfo = soup.find(id="game_info")
                      #gameinfo = gameinfo.find(name="tbody")
                      
                      teamstats = soup.find(id="team_stats")                  
                      #teamstats = teamstats.find(name="tbody")

                      homesnaps = soup.find(id="home_snap_counts")                  
                      homesnaps = homesnaps.find(name="tbody")
                      
                      vissnaps = soup.find(id="vis_snap_counts")                  
                      vissnaps = vissnaps.find(name="tbody")
                      
               
                      #for thead in fantasydata.select('.thead'):
                      #  thead.extract()    # rip it out
                      #fantasydata = soup.body
                      gamedataObj = {'Game':gameId,'Week':weekNum}
                      snapsdataArr = []

                      if (gameinfo is not None):
                        datatext = gameinfo.get_text(separator=u',,')
                        datatextlines = list(line.strip()[2:-2].strip() for line in datatext.splitlines() if not line.isspace() and line.strip() and line.strip() != ',,')
                        
                        for gamelineStr in datatextlines[1:]:
                          gamelineKey = gamelineStr.split(',,')[0]
                          gamelineVal = gamelineStr.split(',,')[1]
                          gamedataObj[gamelineKey.strip()] = gamelineVal.strip()
                          
                        
                        datatext = "\n".join(datatextlines)
                        urlfiledata[1] = path + filename + "--gameinfo.txt"
                        file = open(path + filename + "--gameinfo.txt",'wb') 
                        file.write(datatext.encode('utf-8')) 
                        file.close()                 

                      homeTeam = ''
                      visTeam = ''
                      if (teamstats is not None):
                        datatext = teamstats.get_text(separator=u',,')
                        datatextlines = list(line.strip()[2:-2].strip() for line in datatext.splitlines() if not line.isspace() and line.strip() and line.strip() != ',,')

                        if (len(datatextlines) > 3):
                          gamedataObj['Home'] = datatextlines[2].strip()
                          homeTeam = datatextlines[2].strip()
                          gamedataObj['Visitor'] = datatextlines[1].strip()
                          visTeam = datatextlines[1].strip()
                          for gamelineStr in datatextlines[3:]:
                            gamelineHomeKey = gamelineStr.split(',,')[0] + ' Home'
                            gamelineHomeVal = gamelineStr.split(',,')[2]
                            gamelineVisKey = gamelineStr.split(',,')[0] + ' Visitor'
                            gamelineVisVal = gamelineStr.split(',,')[1]
                            gamedataObj[gamelineHomeKey.strip()] = gamelineHomeVal.strip()
                            gamedataObj[gamelineVisKey.strip()] = gamelineVisVal.strip()

                        datatext = ','.join(str(v) for v in gamedataObj.keys()) + '\n'
                        datatext = datatext + ','.join('"' + str(v).replace('-', '~') + '"' for v in gamedataObj.values()) + '\n'
                        for objKey, objVal in gamedataObj.items():
                          gamedataObj[objKey] = '' #clear it out but keep the object with keys for next game
                        #datatext = "\n".join(datatextlines)
                        urlfiledata[2] = path + gameId + "--teamstats.csv"
                        file = open(path + gameId + "--teamstats.csv",'wb') 
                        file.write(datatext.encode('utf-8')) 
                        file.close() 

                      if (homesnaps is not None):
                        datatext = homesnaps.get_text(separator=u',')
                        datatextlines = list((gameId + ',' + str(weekNum) + ',' + homeTeam + ',' + line.strip()[1:-1].strip()) for line in datatext.splitlines() if not line.isspace() and line.strip() and line.strip() != ',')

                        snapsdataArr.extend(datatextlines)
                        datatext = "\n".join(datatextlines)
                        datatext = 'Game,Week,Team,Player,Pos,OffSnaps,OffPct,DefSnaps,DefPct,STSnaps,STPct\n' + datatext
                        urlfiledata[3] = path + filename + "--homesnaps.txt"
                        file = open(path + filename + "--homesnaps.txt",'wb') 
                        file.write(datatext.encode('utf-8')) 
                        file.close() 

                      if (vissnaps is not None):
                        datatext = vissnaps.get_text(separator=u',')
                        datatextlines = list((gameId + ',' + str(weekNum) + ',' + visTeam + ',' + line.strip()[1:-1].strip()) for line in datatext.splitlines() if not line.isspace() and line.strip() and line.strip() != ',')

                        snapsdataArr.extend(datatextlines)
                        datatext = "\n".join(datatextlines)
                        datatext = 'Game,Week,Team,Player,Pos,OffSnaps,OffPct,DefSnaps,DefPct,STSnaps,STPct\n' + datatext
                        urlfiledata[4] = path + filename + "--vissnaps.txt"
                        file = open(path + filename + "--vissnaps.txt",'wb') 
                        file.write(datatext.encode('utf-8')) 
                        file.close() 
                     
                      if (len(snapsdataArr) > 0):
                        datatext = "\n".join(snapsdataArr)
                        datatext = 'Game,Week,Team,Player,Pos,OffSnaps,OffPct,DefSnaps,DefPct,STSnaps,STPct\n' + datatext
                        urlfiledata[4] = path + filename + "--snaps.csv"
                        file = open(path + filename + "--snaps.csv",'wb') 
                        file.write(datatext.encode('utf-8')) 
                        file.close()
                                          
                      zf = zipfile.ZipFile(path + 'alldata.zip', mode='a')
                      try:
                          zf.write(path + filename + "--html.txt", arcname=filename + "--html.txt", compress_type=compression)
                      finally:
                          zf.close()

                  
                      urldata.extend(urlfiledata)
                      projectdata.append(",".join(urldata))
                    
                    # logging.debug('Debug for 9 : ' + str(errorMsg))               
                    if (errorMsg == ""):
                      #now write out the project file csv to complete project creation
                      # logging.debug('Debug for 10 : ' + str(errorMsg)) 
                      file = open(path + "projectdata.csv",'wb') 
                      file.write("\n".join(projectdata).encode('utf-8')) 
                      file.close()



                  else :
                    # just normal webscrape for testing new urls
                    for thisDataStr in csvdataArray[1:]:
                      # logging.debug('Debug for 8 : ' + str(thisDataStr))
                      thisData = thisDataStr.split(",")
                      if (len(thisData) != len(colHeads)):
                        errorMsg = errorMsg + str(thisData[0]) + " row did not have the correct number of values.<br />"
                      thisUrl = thisData[0]
                      filename = thisUrl.replace(".", "_").replace("://", "_").replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_").replace("%", "_").replace("+", "_").replace(" ", "_")
                      urldata = []
                      urlfiledata = ['','','','','','']
                      urldata.extend(thisData)
                        
                      r = requests.get(thisUrl, headers={'User-Agent': 'Mozilla/5.0'})
                      # r = requests.get(thisUrl, headers={'User-Agent': 'Googlebot'}) #this is not working for some sites
                      html = r.text
                      # logging.debug('Debug for : ' + str(html))
                      # logging.debug('Debug for : ' + str(r.status_code))
                      # logging.debug('Debug for : ' + str(r.raise_for_status()))
                    
                              
                      #req = Request(thisUrl, headers={'User-Agent': 'Googlebot'}) #note: using googlebot as agent to prevent being blocked
                      #with urllib.request.urlopen(req) as response:
                      #  html = response.read()
                  
                      soup = BeautifulSoup(html, 'html.parser', from_encoding="utf-8")

                      urlfiledata[0] = path + filename + "--html.txt"
                      file = open(path + filename + "--html.txt",'wb') 
                      file.write(soup.prettify().encode('utf-8')) 
                      file.close()

                      '''
                      for script in soup(["script", "style"]):
                        script.decompose()    # rip it out
                      for comment in soup.find_all(string=lambda text:isinstance(text,Comment)):
                        comment.extract()    # rip it out
                      for hidden in soup.select('.hidden-lg,.hidden-md,.modal,.hidden,.hide,.lightbox'):
                        hidden.extract()    # rip it out
                      '''
                      #fantasydata = soup.find(id="games")
                      #fantasydata = fantasydata.find(name="tbody")
                      #for thead in fantasydata.select('.thead'):
                      #  thead.extract()    # rip it out
                      fantasydata = soup.body
                      
                      if (fantasydata is not None):
                        datatext = fantasydata.get_text(separator=u',')
                        datatextlines = list(line.strip() for line in datatext.splitlines() if not line.isspace() and line.strip() and line.strip() != ',')
                        
                        datatext = "\n".join(datatextlines)
                        urlfiledata[1] = path + filename + "--fantasydata.txt"
                        file = open(path + filename + "--fantasydata.txt",'wb') 
                        file.write(datatext.encode('utf-8')) 
                        file.close()                 

                        
                        zf = zipfile.ZipFile(path + 'alldata.zip', mode='a')
                        try:
                            zf.write(path + filename + "--html.txt", arcname=filename + "--html.txt", compress_type=compression)
                            zf.write(path + filename + "--fantasydata.txt", arcname=filename + "--fantasydata.txt", compress_type=compression)
                        finally:
                            zf.close()

                  
                      urldata.extend(urlfiledata)
                      projectdata.append(",".join(urldata))
                    
                    # logging.debug('Debug for 9 : ' + str(errorMsg))               
                    if (errorMsg == ""):
                      #now write out the project file csv to complete project creation
                      # logging.debug('Debug for 10 : ' + str(errorMsg)) 
                      file = open(path + "projectdata.csv",'wb') 
                      file.write("\n".join(projectdata).encode('utf-8')) 
                      file.close()
                                        

                # end of if else project exists     
                
            else:
              errorMsg = "Your first row must start with headers : url,..."
    if (errorMsg != ""):
      return render(request, 'nfl_research/create_project.html', {'projectname':projectname, 'csvdata': csvdata, 'errorMsg':errorMsg})
    else:
      response = redirect('/nfl_research/project/')
      response['Location'] += '?project=' + projectname
      return response
  return render(request, 'nfl_research/create_project.html', {})


'''
*****************************************************************************************
LOAD THE PRIOR WEEKS DATA FOR ALL TEAMS FROM AJAX
- POST
- week : (int) nfl week of season (1-17 for reg)
- year : (int) 4 digit year value
- season : (str) should be 'Week', 'Post', 'Pre'
- site : (str) should be 'DK', 'Fanduel', 'FantasyDraft'
- slate : (str) should be name
- reload : (str) should be true / false - used to force reload data from remote
*****************************************************************************************
'''
class Update_Stats_Data(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      analysisWeek = int(request.POST.get('week', 0) if request.POST.get('week', 0) != '' else 0 ) #should pass in the current week
      analysisYear = int(request.POST.get('year', 0) if request.POST.get('year', 0) != '' else 0 )
      season = str(request.POST.get('season', 'Week')) #should be 'Week', 'Post', 'Pre'
      #weekTxt = str(season) + str(analysisWeek)
      reload = str(request.POST.get('reload', 'true'))
    
      if (analysisYear <= (datetime.now().year + 1)) :
        '''
        NOTE : I AM DOING THIS JUST TO TEST COMBINING FILES WITHOUT MUCKING WITH DB
        '''
        #data = Data_Manager.update_stats_data_request(analysisYear, analysisWeek, season, reload)
        data = Data_Manager.combine_files_to_one_json(analysisYear, analysisWeek, season, reload)
      else :
        data["errorMsg"] = "Year is in the future"
    else :
      data["errorMsg"] = "Must use POST method"
    return JsonResponse(data)
'''
*****************************************************************************************
LOAD THE PRIOR WEEKS DATA FOR A TEAM FROM AJAX
- POST
- week : (int) nfl week of season (1-17 for reg)
- year : (int) 4 digit year value
- season : (str) should be 'Week', 'Post', 'Pre'
- site : (str) should be 'DK', 'Fanduel', 'FantasyDraft'
- slate : (str) should be name
- team : (str) should be team initials ( "JAX" not "JAC" )
- reload : (str) should be true / false - used to force reload data from remote
*****************************************************************************************
'''
class Update_Week_Data_For_Team(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      analysisWeek = int(request.POST.get('week', 0)) #should pass in the current week
      weekNumStart = analysisWeek - 1
      analysisYear = int(request.POST.get('year', 0))
      season = str(request.POST.get('season', 'Week')) #should be 'Week', 'Post', 'Pre'
      weekTxt = str(season) + str(analysisWeek)
      site = str(request.POST.get('site', 'DK')) #should be 'DK', 'Fanduel', 'FantasyDraft'
      team = str(request.POST.get('team', '')) #should be team initials ( "JAX" not "JAC" )
      reload = str(request.POST.get('reload', 'true'))
      path = SITE_ROOT + STATIC_PROJECTS + 'historical' + '/'
    
      if (analysisWeek != 0 and analysisYear != 0 and analysisWeek > 0 and analysisWeek < 18 and analysisYear > 2012 and analysisYear <= (datetime.now().year + 1) and team != "") :
        data = Data_Manager.update_weekdata_for_team(analysisYear, analysisWeek, season, site, team, reload)
      else :
        data["errorMsg"] = "Week, Year and Team are required"
    else :
      data["errorMsg"] = "Must use POST method"
    return JsonResponse(data)

'''
*****************************************************************************************
LOAD A WEEKS DATA FOR PAGE
- POST
- week : (int) nfl week of season (1-17 for reg)
- year : (int) 4 digit year value
- season : (str) should be 'Week', 'Post', 'Pre'
- site : (str) should be 'DK', 'Fanduel', 'FantasyDraft'
- slate : (str) should be name
- reload : (str) should be true / false - used to force reload data from remote
*****************************************************************************************
'''
class Load_Week_Data(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["file"] = ""
    data["firstObj"] = {}
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      analysisWeek = int(request.POST.get('week', 0))
      analysisYear = int(request.POST.get('year', 0))
      season = str(request.POST.get('season', 'Week')) #should be 'Week', 'Post', 'Pre'
      weekTxt = str(season) + str(analysisWeek)
      site = str(request.POST.get('site', 'DK')) #should be 'DK', 'Fanduel', 'FantasyDraft'
      slate = str(request.POST.get('slate', '')) #should be name
      reload = str(request.POST.get('reload', 'true'))
      file_path = SITE_ROOT + STATIC_PROJECTS + 'weekupdate' + '/' + str(analysisYear) + '/' + str(weekTxt) + '/' + site + '/'
      data["file"] = STATIC_PROJECTS + 'weekupdate' + '/' + str(analysisYear) + '/' + str(weekTxt) + '/' + site + '/' + "weekly_nfl_data_" + str(slate) + ".json"
    
      if (analysisWeek != 0 and analysisYear != 0 and analysisWeek > 0 and analysisWeek < 18 and analysisYear > 2012 and analysisYear <= (datetime.now().year + 1)) :
        analysis_file = file_path + "weekly_nfl_data_" + str(slate) + ".json"
        projectdata_cols = []
        alldata_rows = []
        if (os.path.exists(analysis_file) and reload != 'true'):
          with open(analysis_file, 'r') as content_file:
            try:
              alldata_rows = json.load(content_file)
            except:
              alldata_rows = []
              logging.debug('bad json - possibly empty file')
          
            '''
            project_content = content_file.read()
            divisibleBySeven = [num for num in inputList if num != 0 and num % 7 == 0]
            '''
            '''
            data["maps"][0]["id"]
            data["masks"]["id"]
            data["om_points"]
            '''

        # IF WE NEED TO RELOAD DATA OR IF DATA DOES NOT EXIST FOR THIS WEEK ALREADY THEN DO THIS
        if (reload == 'true' or len(alldata_rows) < 1) :
          alldata_rows = []
          # first thing we do when reloading is get list of players on slate.
          # TODO - change this to reload = False since we likely don't want to always be reloading salary and maybe only update if it doesnt exist or on demand
          salary_data = Data_Manager.get_salary_data(analysisYear, analysisWeek, season, site, slate, reload)
          dk_full_salary_data = Data_Manager.get_salary_data(analysisYear, analysisWeek, season, "DK", "Full", 'false')        
          fd_full_salary_data = Data_Manager.get_salary_data(analysisYear, analysisWeek, season, "Fanduel", "Full", 'false')
          dk_full_salary_obj = {}
          fd_full_salary_obj = {}
        
          if (dk_full_salary_data["success"] == 'true' and dk_full_salary_data["player_data"]) :
            player_data = dk_full_salary_data["player_data"]   
            if (len(player_data) > 1):
              for player_row in player_data[1:]:
                playerValues = player_row.split(",")
                playerNames = playerValues[4].strip().split(" ")
                playerName = (str(playerNames[0]) + " " + str(playerNames[1])) if len(playerNames) > 1 else str(playerNames[0])
                teamInitials = playerValues[8]
                playerPosition = playerValues[5].strip()
                if (playerPosition == "DST" or playerPosition == "D") :
                  playerPosition = "DST"
                  teamObj = teamNames[teamInitials]
                  if (teamObj) :
                    playerName = teamObj["lookup"]
                    teamInitials = playerName
                playerName = playerName.replace("'","").replace(".","")
                lookupName = playerName + "_" + playerPosition + "_" + teamInitials
                dk_full_salary_obj[lookupName] = playerValues[6]
          if (fd_full_salary_data["success"] == 'true' and fd_full_salary_data["player_data"]) :
            player_data = fd_full_salary_data["player_data"]   
            if (len(player_data) > 1):
              for player_row in player_data[1:]:
                playerValues = player_row.split(",")
                playerNames = playerValues[4].strip().split(" ")
                playerName = (str(playerNames[0]) + " " + str(playerNames[1])) if len(playerNames) > 1 else str(playerNames[0])
                teamInitials = playerValues[8]
                playerPosition = playerValues[5].strip()
                if (playerPosition == "DST" or playerPosition == "D") :
                  playerPosition = "DST"
                  teamObj = teamNames[teamInitials]
                  if (teamObj) :
                    playerName = teamObj["lookup"]
                    teamInitials = playerName
                playerName = playerName.replace("'","").replace(".","")
                lookupName = playerName + "_" + playerPosition + "_" + teamInitials
                #logging.debug('Debug : ' + lookupName)
                fd_full_salary_obj[lookupName] = playerValues[6]
                fd_full_salary_obj[lookupName + "_OPP"] = playerValues[9]
        
          if (salary_data["success"] == 'true' and salary_data["player_data"]) :

            player_data = salary_data["player_data"]

            if (len(player_data) > 1):
              returnPlayerData = {"QB":{"thisYearsPlayerArray":[],"lastWeeksPlayerArray":[],"lastWeeksPlayerDict":{}},"RB":{},"WR":{},"TE":{},"DST":{},"K":{}}
              returnPlayerData["QB"] = Data_Manager.getLastWeekDataIfExists(analysisYear, analysisWeek, season, site, '', 'false', 'QB') #pass empty for team to get all team data for last week, AND pass false on reload so we get back the full year data for all players including last week
              returnPlayerData["RB"] = Data_Manager.getLastWeekDataIfExists(analysisYear, analysisWeek, season, site, '', 'false', 'RB') #pass empty for team to get all team data for last week, AND pass false on reload so we get back the full year data for all players including last week
              returnPlayerData["WR"] = Data_Manager.getLastWeekDataIfExists(analysisYear, analysisWeek, season, site, '', 'false', 'WR') #pass empty for team to get all team data for last week, AND pass false on reload so we get back the full year data for all players including last week
              returnPlayerData["TE"] = Data_Manager.getLastWeekDataIfExists(analysisYear, analysisWeek, season, site, '', 'false', 'TE') #pass empty for team to get all team data for last week, AND pass false on reload so we get back the full year data for all players including last week
              returnPlayerData["DST"] = Data_Manager.getLastWeekDataIfExists(analysisYear, analysisWeek, season, site, '', 'false', 'DST') #pass empty for team to get all team data for last week, AND pass false on reload so we get back the full year data for all players including last week
              returnPlayerData["K"] = Data_Manager.getLastWeekDataIfExists(analysisYear, analysisWeek, season, site, '', 'false', 'K') #pass empty for team to get all team data for last week, AND pass false on reload so we get back the full year data for all players including last week
              if (len(returnPlayerData["QB"]["lastWeeksPlayerArray"]) <= 0 or len(returnPlayerData["RB"]["lastWeeksPlayerArray"]) <= 0 or len(returnPlayerData["WR"]["lastWeeksPlayerArray"]) <= 0 or len(returnPlayerData["TE"]["lastWeeksPlayerArray"]) <= 0 or len(returnPlayerData["DST"]["lastWeeksPlayerArray"]) <= 0) :
                data["errorMsg"] = "Error:21 There was an issue loading last weeks data.  Try Reloading this data."
                return JsonResponse(data)
              #no error getting historical data on players 
              #technically we could put this in ELSE statement but we probably will have several files to check and rather than nesting we can just return if we hit erro
          
              #items = [item for item in container if item.attribute == value]
            
              for player_row in player_data[1:]:
                playerValues = player_row.split(",")
                playerNames = playerValues[4].strip().split(" ")
                playerName = (str(playerNames[0]) + " " + str(playerNames[1])) if len(playerNames) > 1 else str(playerNames[0])
                teamInitials = playerValues[8]
                playerPosition = playerValues[5].strip()
                if (playerPosition == "DST" or playerPosition == "D") :
                  playerPosition = "DST"
                  teamObj = teamNames[teamInitials]
                  if (teamObj) :
                    playerName = teamObj["lookup"]
                    teamInitials = playerName
                playerName = playerName.replace("'","").replace(".","")
                lookupName = playerName + "_" + playerPosition + "_" + teamInitials
                            
                playerData = {
                  #['Year','Week','Slate','ID','Name','Position','Salary','GameInfo','Team','Opponent','FPPG','InjuryStatus','InjuryDetails']
                 "id": playerValues[3],
                 "Name": playerValues[4],
                 "Pos": playerValues[5],
                 "Team": playerValues[8],
                 "Opp": fd_full_salary_obj.get(lookupName + "_OPP", ''),
                 "Home_Road" : "",
                 "GameInfo": playerValues[7],
                 "Salary": playerValues[6],
                 "FullSlateDKSalary": dk_full_salary_obj.get(lookupName, 0),
                 "FullSlateFDSalary": fd_full_salary_obj.get(lookupName, 0),
                 "FanPtsActual": 0.0,
                 "FanPtsArmyProj": 0.0,
                 "FanPtsMyProj": 0.0,
                 "Value": 0.0,
                 "OwnershipProjPct" : 0.0,
                 "LW_SnapPercent" : 0.00,
                 "LW_SnapCount" : 0,
                 "LW_ADOT" : 0.0,
                 "LW_AYAC" : 0.0,
                }

                playerData["LW_Opp"] = "DNP"
              
                playerData["LW_FGMade"] = 0
                playerData["LW_FGAtt"] = 0
                playerData["LW_FGPct"] = 0.0
                playerData["LW_FGLong"] = 0
                playerData["LW_XPMade"] = 0
                playerData["LW_XPAtt"] = 0
              
                playerData["LW_TklForLoss"] = 0
                playerData["LW_Sacks"] = 0
                playerData["LW_QBHits"] = 0
                playerData["LW_DefInt"] = 0
                playerData["LW_FumRec"] = 0
                playerData["LW_Safeties"] = 0
                playerData["LW_DefTD"] = 0
                playerData["LW_ReturnTD"] = 0
                playerData["LW_PtsAllowed"] = 0
              
                playerData["LW_PassComp"] = 0
                playerData["LW_PassAtt"] = 0
                playerData["LW_CompPct"] = 0.0
                playerData["LW_PassYds"] = 0
                playerData["LW_PassYdsPerAtt"] = 0.0
                playerData["LW_PassTD"] = 0
                playerData["LW_PassInt"] = 0
                playerData["LW_QBRating"] = 0

                playerData["LW_RushAtt"] = 0
                playerData["LW_RushYds"] = 0
                playerData["LW_RushYdsPerAtt"] = 0.0
                playerData["LW_RushTD"] = 0

                playerData["LW_Targets"] = 0
                playerData["LW_Rec"] = 0
                playerData["LW_RecPct"] = 0.0
                playerData["LW_RecYds"] = 0
                playerData["LW_RecTD"] = 0
                playerData["LW_RecLong"] = 0

                playerData["LW_Fum"] = 0
                playerData["LW_Lost"] = 0
                playerData["LW_FanPts"] = 0.0

                #lwPlayerData = returnPlayerData[playerPosition]["lastWeeksPlayerDict"].get(lookupName,[0,'',0,'','',0,'','',0,0,0,0,0,0,0,0,0,0,0,0,0,0.0])
                lwPlayerData = returnPlayerData[playerPosition]["lastWeeksPlayerDict"].get(lookupName,[])
           
                #Year	Season	Rk	Player	Pos	Week	Team	Opp	8Targets	Rec	Pct	Yds	TD	Long	YdsPerTarget	YdsPerRec	16Rush	Yds	TD	Fum	Lost	FantasyPts
                if (len(lwPlayerData) > 0 and (playerPosition == "WR" or playerPosition == "TE")) :
                  playerData["LW_Opp"] = lwPlayerData[7]
                  playerData["LW_Targets"] = lwPlayerData[8]
                  playerData["LW_Rec"] = lwPlayerData[9]
                  playerData["LW_RecPct"] = float(lwPlayerData[10])
                  playerData["LW_RecYds"] = lwPlayerData[11]
                  playerData["LW_RecTD"] = lwPlayerData[12]
                  playerData["LW_RecLong"] = lwPlayerData[13]
                  playerData["LW_RushAtt"] = lwPlayerData[16]
                  playerData["LW_RushYds"] = lwPlayerData[17]
                  if (int(lwPlayerData[16]) > 0):
                    playerData["LW_RushYdsPerAtt"] = round(float(lwPlayerData[17])/float(lwPlayerData[16])*100.0,1)
                  else:
                    playerData["LW_RushYdsPerAtt"] = 0.0
                  playerData["LW_RushTD"] = lwPlayerData[18]
                  playerData["LW_Fum"] = lwPlayerData[19]
                  playerData["LW_Lost"] = lwPlayerData[20]
                  playerData["LW_FanPts"] = float(lwPlayerData[21])
                #Year	Season	Rk	Player	Pos	Week	Team	Opp	Att	Yds	YdsPerAtt	TD	12Targets	Rec	Yds	TD	Fum	Lost	FantasyPts
                elif (len(lwPlayerData) > 0 and playerPosition == "RB") :
                  playerData["LW_Opp"] = lwPlayerData[7]
                  playerData["LW_Targets"] = lwPlayerData[12]
                  playerData["LW_Rec"] = lwPlayerData[13]
                  if (int(lwPlayerData[12]) > 0):
                    playerData["LW_RecPct"] = round(float(lwPlayerData[13])/float(lwPlayerData[12])*100.0,1)
                  else:
                    playerData["LW_RecPct"] = 0.0
                  playerData["LW_RecYds"] = lwPlayerData[14]
                  playerData["LW_RecTD"] = lwPlayerData[15]
                  playerData["LW_RushAtt"] = lwPlayerData[8]
                  playerData["LW_RushYds"] = lwPlayerData[9]
                  playerData["LW_RushYdsPerAtt"] = lwPlayerData[10]
                  playerData["LW_RushTD"] = lwPlayerData[11]
                  playerData["LW_Fum"] = lwPlayerData[16]
                  playerData["LW_Lost"] = lwPlayerData[17]
                  playerData["LW_FanPts"] = float(lwPlayerData[18])
                #Year	Season	Rk	Player	Pos	Week	Team	Opp	8Comp	Att	Pct	Yds	Yds/Att	TD	Int	QBRating	Att	Yds	Yds/Att	TD	FantasyPts
                elif (len(lwPlayerData) > 0 and playerPosition == "QB") :
                  playerData["LW_Opp"] = lwPlayerData[7]
                  playerData["LW_PassComp"] = lwPlayerData[8]
                  playerData["LW_PassAtt"] = lwPlayerData[9]
                  playerData["LW_CompPct"] = float(lwPlayerData[10])
                  playerData["LW_PassYds"] = lwPlayerData[11]
                  playerData["LW_PassYdsPerAtt"] = float(lwPlayerData[12])
                  playerData["LW_PassTD"] = lwPlayerData[13]
                  playerData["LW_PassInt"] = lwPlayerData[14]
                  playerData["LW_QBRating"] = lwPlayerData[15]
                  playerData["LW_RushAtt"] = lwPlayerData[16]
                  playerData["LW_RushYds"] = lwPlayerData[17]
                  playerData["LW_RushYdsPerAtt"] = float(lwPlayerData[18])
                  playerData["LW_RushTD"] = lwPlayerData[19]
                  playerData["LW_FanPts"] = float(lwPlayerData[20])
                #Year	Season	Rk	Player	Pos	Week	Team	Opp	8TFL	Sacks	QBHits	Int	FumRec	Safeties	14DefTD	ReturnTD	PtsAllowed	FantasyPts
                elif (len(lwPlayerData) > 0 and playerPosition == "DST") :
                  playerData["LW_Opp"] = lwPlayerData[7]
                  playerData["LW_TklForLoss"] = lwPlayerData[8]
                  playerData["LW_Sacks"] = lwPlayerData[9]
                  playerData["LW_QBHits"] = lwPlayerData[10]
                  playerData["LW_DefInt"] = lwPlayerData[11]
                  playerData["LW_FumRec"] = lwPlayerData[12]
                  playerData["LW_Safeties"] = lwPlayerData[13]
                  playerData["LW_DefTD"] = lwPlayerData[14]
                  playerData["LW_ReturnTD"] = lwPlayerData[15]
                  playerData["LW_PtsAllowed"] = lwPlayerData[16]
                  playerData["LW_FanPts"] = float(lwPlayerData[17])
                #Year	Season	Rk	Player	Pos	Week	Team	Opp	8FGMade	FGAtt	Pct	Long	XPMade	XPAtt	FantasyPts
                elif (len(lwPlayerData) > 0 and playerPosition == "K") :
                  playerData["LW_Opp"] = lwPlayerData[7]
                  playerData["LW_FGMade"] = lwPlayerData[8]
                  playerData["LW_FGAtt"] = lwPlayerData[9]
                  playerData["LW_FGPct"] = float(lwPlayerData[10])
                  playerData["LW_FGLong"] = lwPlayerData[11]
                  playerData["LW_XPMade"] = lwPlayerData[12]
                  playerData["LW_XPAtt"] = lwPlayerData[13]
                  playerData["LW_FanPts"] = float(lwPlayerData[14])
     
                alldata_rows.append(playerData)

          
          else : # getting salary data unsuccessfull
            data["errorMsg"] = "Error getting salary data: " + salary_data["errorMsg"]

      
        # Write our CSV to files 
        '''
        strToWrite1 = ""
        strToWrite2 = ""
        if (len(projectdata_cols) > 0) :
          strToWrite1 = "\n".join(projectdata_cols) + "\n"
        if (len(alldata_rows) > 0) :
          strToWrite2 = "\n".join(alldata_rows) + "\n"
        file = open(analysis_file,'wb') 
        file.write((strToWrite1 + strToWrite2).encode('utf-8')) 
        file.close()
        '''
        # NOW WRITE ALL THE DATA OUT TO THE FILE
        if (len(alldata_rows) > 0) :
          data["firstObj"] = alldata_rows[0]
          with open(analysis_file, 'w') as datafile:
            json.dump(alldata_rows, datafile, ensure_ascii=False)      

        if (data["errorMsg"] == ""):
          data["success"] = "true"
      else:
        data["errorMsg"] = "Error in data submitted - Need Week and Year"
    else:
      data["errorMsg"] = "Error in data submitted - No GET requests"
  
    return JsonResponse(data)


''' 
APIS
Player Season Stats : https://api.sportsdata.io/v3/nfl/stats/json/PlayerSeasonStats/2020REG?key=5f8fb37357c749b0a91651561af92cbe
Fantasy DEF Season Stats : https://api.sportsdata.io/v3/nfl/stats/json/FantasyDefenseBySeason/2020REG?key=5f8fb37357c749b0a91651561af92cbe
Current Week Num: https://api.sportsdata.io/v3/nfl/scores/json/UpcomingWeek?key=5f8fb37357c749b0a91651561af92cbe
Year of current season: https://api.sportsdata.io/v3/nfl/scores/json/UpcomingSeason?key=5f8fb37357c749b0a91651561af92cbe
Week scores : https://api.sportsdata.io/v3/nfl/scores/json/ScoresByWeek/2020/8?key=5f8fb37357c749b0a91651561af92cbe
Team Season Stats : https://api.sportsdata.io/v3/nfl/scores/json/TeamSeasonStats/2020REG?key=5f8fb37357c749b0a91651561af92cbe
Player Season Redzone Stats : https://api.sportsdata.io/v3/nfl/stats/json/PlayerSeasonRedZoneStats/2020REG?key=5f8fb37357c749b0a91651561af92cbe
Projected Player Game Stats by week : https://api.sportsdata.io/v3/nfl/projections/json/PlayerGameProjectionStatsByWeek/2020REG/8?key=1122438f4e6d46afa9404a8c51cdc194
DST Projections by week : https://api.sportsdata.io/v3/nfl/projections/json/FantasyDefenseProjectionsByGame/2020REG/8?key=1122438f4e6d46afa9404a8c51cdc194
'''

'''
*****************************************************************************************
GET CURRENT WEEK
- POST
*****************************************************************************************
'''
class Get_Current_Week(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["currentWeek"] = ""
    if request.method == "POST":
      results_obj = Data_Manager.getCurrentWeek() 
      if (results_obj != '') :
        data["currentWeek"] = results_obj
        data["success"] = "true"
      else :
        data["errorMsg"] = "Error getting currentWeek:" + results_obj
        return JsonResponse(data)
    else:
      data["errorMsg"] = "Error in data submitted - No GET requests"
  
    return JsonResponse(data)

'''
*****************************************************************************************
GET CURRENT SEASON
- POST
*****************************************************************************************
'''
class Get_Current_Season(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["currentSeason"] = ""
    if request.method == "POST":
      results_obj = Data_Manager.getCurrentSeason() 
      if (results_obj != '') :
        data["currentSeason"] = results_obj
        data["success"] = "true"
      else :
        data["errorMsg"] = "Error getting currentSeason:" + results_obj
        return JsonResponse(data)
    else:
      data["errorMsg"] = "Error in data submitted - No GET requests"
  
    return JsonResponse(data)


'''
*****************************************************************************************
GET CURRENT WEEK GAMES
- POST
- year : (int) 4 digit year value
- season : (str) should be 'REG', 'POST', 'PRE'
- site : (str) should be 'DK', 'Fanduel'
- week : (int) should be id of the game to filter by (OPTIONAL)
- reload : (str) should be true / false - used to force reload data from remote
*****************************************************************************************
'''
class Get_Current_Week_Games(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["weekGameData"] = {}
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      analysisYear = int(request.POST.get('year', 0))
      season = str(request.POST.get('season', 'REG')).upper() #should be 'REG', 'POST', 'PRE'
      site = str(request.POST.get('site', 'DK')) #should be 'DK', 'Fanduel'
      week = int(request.POST.get('week', 0)) #should be week num 
      reload = str(request.POST.get('reload', 'true'))
      forceReload = reload == 'true'

      if (analysisYear != 0 and analysisYear > 2012 and analysisYear <= (datetime.now().year + 1) and week != 0) :
        # IF WE NEED TO RELOAD DATA OR IF DATA DOES NOT EXIST FOR THIS WEEK ALREADY THEN DO THIS
        alldata_rows = []
  
        results_obj = Data_Manager.getCurrentWeekGames(analysisYear, week, forceReload) 
        if (results_obj["success"] == 'true') :
            alldata_rows = results_obj["weekGameData"]
        else :
            data["errorMsg"] = results_obj["errorMsg"]
            return JsonResponse(data)
        #.get('Data',[])
  

        if (len(alldata_rows) > 0 and data["errorMsg"] == "") :
            data["success"] = "true"
            data["weekGameData"] = alldata_rows
        else:   
            data["errorMsg"] = "No data found"
      else:
        data["errorMsg"] = "Error in data submitted - Need Year"
    else:
      data["errorMsg"] = "Error in data submitted - No GET requests"
  
    return JsonResponse(data)



#https://api.sportsdata.io/v3/nfl/scores/json/TeamSeasonStats/2020REG?key=5f8fb37357c749b0a91651561af92cbe
'''
*****************************************************************************************
GET TEAM SEASON STATS
- POST
- year : (int) 4 digit year value
- season : (str) should be 'REG', 'POST', 'PRE'
- site : (str) should be 'DK', 'Fanduel'
- reload : (str) should be true / false - used to force reload data from remote
*****************************************************************************************
'''
class Get_Team_Season_Stats(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["teamSeasonData"] = {}
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      analysisYear = int(request.POST.get('year', 0))
      season = str(request.POST.get('season', 'REG')).upper() #should be 'REG', 'POST', 'PRE'
      site = str(request.POST.get('site', 'DK')) #should be 'DK', 'Fanduel'
      reload = str(request.POST.get('reload', 'true'))
      forceReload = reload == 'true'

      if (analysisYear != 0 and analysisYear > 2012 and analysisYear <= (datetime.now().year + 1)) :
        # IF WE NEED TO RELOAD DATA OR IF DATA DOES NOT EXIST FOR THIS WEEK ALREADY THEN DO THIS
        alldata_rows = []
  
        results_obj = Data_Manager.getTeamSeasonStats(analysisYear, season, forceReload) 
        if (results_obj["success"] == 'true') :
            alldata_rows = results_obj["teamSeasonData"]
        else :
            data["errorMsg"] = results_obj["errorMsg"]
            return JsonResponse(data)
        #.get('Data',[])
  

        if (len(alldata_rows) > 0 and data["errorMsg"] == "") :
            data["success"] = "true"
            data["teamSeasonData"] = alldata_rows
        else:   
            data["errorMsg"] = "No data found"
      else:
        data["errorMsg"] = "Error in data submitted - Need Year"
    else:
      data["errorMsg"] = "Error in data submitted - No GET requests"
  
    return JsonResponse(data)


'''
*****************************************************************************************
GET TEAM PROJECTIONS
- POST
- year : (int) 4 digit year value
- season : (str) should be 'REG', 'POST', 'PRE'
- week : (int) week num
- team : (str) Team Initials (DAL)
- reload : (str) should be true / false - used to force reload data from remote
*****************************************************************************************
'''
class Get_Team_Projections(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["projData"] = {}
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      analysisYear = int(request.POST.get('year', 0))
      analysisWeek = int(request.POST.get('week', 0))
      season = str(request.POST.get('season', 'REG')).upper() #should be 'REG', 'POST', 'PRE'
      team = str(request.POST.get('team', '')).upper() #should be team initials
      reload = str(request.POST.get('reload', 'true'))
      forceReload = reload == 'true'

      if (analysisYear != 0 and analysisYear > 2012 and analysisYear <= (datetime.now().year + 1)) :
        # IF WE NEED TO RELOAD DATA OR IF DATA DOES NOT EXIST FOR THIS WEEK ALREADY THEN DO THIS
        alldata_rows = []
  
        results_obj = Data_Manager.getTeamProjections(analysisYear, season, analysisWeek, team, forceReload) 
        if (results_obj["success"] == 'true') :
            alldata_rows = results_obj["projData"]
        else :
            data["errorMsg"] = results_obj["errorMsg"]
            return JsonResponse(data)
        #.get('Data',[])
  

        if (len(alldata_rows) > 0 and data["errorMsg"] == "") :
            data["success"] = "true"
            data["projData"] = alldata_rows
        else:   
            data["errorMsg"] = "No data found"
      else:
        data["errorMsg"] = "Error in data submitted - Need Year"
    else:
      data["errorMsg"] = "Error in data submitted - No GET requests"
  
    return JsonResponse(data)


'''
*****************************************************************************************
LOAD SEASON DATA
- POST
- year : (int) 4 digit year value
- season : (str) should be 'REG', 'POST', 'PRE'
- site : (str) should be 'DK', 'Fanduel'
- game : (int) should be id of the game to filter by (OPTIONAL)
- reload : (str) should be true / false - used to force reload data from remote
*****************************************************************************************
'''
class Load_Season_Data(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["file"] = ""
    data["firstObj"] = {}
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      analysisYear = int(request.POST.get('year', 0))
      season = str(request.POST.get('season', 'REG')).upper() #should be 'REG', 'POST', 'PRE'
      site = str(request.POST.get('site', 'DK')) #should be 'DK', 'Fanduel'
      game = str(request.POST.get('game', '')) #should be id of game
      reload = str(request.POST.get('reload', 'true'))
      forceReload = reload == 'true'
      file_path = SITE_ROOT + STATIC_DATA + 'sportsdata' + '/' + str(analysisYear) + '/'
      if (not os.path.exists(file_path)):
        os.makedirs(file_path);
      data["file"] = STATIC_DATA + 'sportsdata' + '/' + str(analysisYear) + '/' + str(analysisYear) + str(season) + "_FILTERED.json"
      logging.debug('file:' + data["file"])

      if (analysisYear != 0 and analysisYear > 2012 and analysisYear <= (datetime.now().year + 1)) :
        logging.debug('1:')
        analysis_file = file_path + str(analysisYear) + str(season) + "_FILTERED.json"
        projectdata_cols = []
        alldata_rows = []
        logging.debug(os.path.exists(analysis_file))
        logging.debug(reload)
        if (os.path.exists(analysis_file) and reload != 'true'):
          logging.debug('2:')
          with open(analysis_file, 'r') as content_file:
            try:
              alldata_rows = json.load(content_file)
            except:
              alldata_rows = []
              logging.debug('bad json - possibly empty file')
          
            '''
            project_content = content_file.read()
            divisibleBySeven = [num for num in inputList if num != 0 and num % 7 == 0]
            '''
            '''
            data["maps"][0]["id"]
            data["masks"]["id"]
            data["om_points"]
            '''

        # IF WE NEED TO RELOAD DATA OR IF DATA DOES NOT EXIST FOR THIS WEEK ALREADY THEN DO THIS
        if (reload == 'true' or len(alldata_rows) < 1) :
          alldata_rows = []
          player_data = []
          
          results_obj = Data_Manager.getSeasonDataIfExists(analysisYear, season, forceReload) 
          if (results_obj["success"] == 'true') :
            player_data = results_obj["playerData"]
          else :
            data["errorMsg"] = results_obj["errorMsg"]
            return JsonResponse(data)
          #.get('Data',[])
          
          #no error getting season data on players 
      
          #items = [item for item in container if item.attribute == value]
        
          for player_row in player_data:
            playerPosition = player_row.get('FantasyPosition','')
            if (playerPosition == "DST" or playerPosition == "QB" or playerPosition == "RB" or playerPosition == "WR" or playerPosition == "TE" or playerPosition == "K") :
                        
                playerData = {
                  "PlayerID":player_row.get('PlayerID',''),
                  "PlayerSeasonID":player_row.get('PlayerSeasonID',''),
                  "Team":player_row.get('Team',''),
                  "Name":player_row.get('Name',''),
                  "ShortName":player_row.get('ShortName',''),
                  "FantasyPosition":player_row.get('FantasyPosition',''),
                  "Played":player_row.get('Played',0),
                  "Started":player_row.get('Started',0),
                  "PassingAttempts":player_row.get('PassingAttempts',0),
                  "PassingCompletions":player_row.get('PassingCompletions',0),
                  "PassingYards":player_row.get('PassingYards',0),
                  "PassingCompletionPercentage":player_row.get('PassingCompletionPercentage',0),
                  "PassingYardsPerCompletion":player_row.get('PassingYardsPerCompletion',0),
                  "PassingTouchdowns":player_row.get('PassingTouchdowns',0),
                  "PassingInterceptions":player_row.get('PassingInterceptions',0),
                  "RushingAttempts":player_row.get('RushingAttempts',0),
                  "RushingYards":player_row.get('RushingYards',0),
                  "RushingYardsPerAttempt":player_row.get('RushingYardsPerAttempt',0),
                  "RushingTouchdowns":player_row.get('RushingTouchdowns',0),
                  "ReceivingTargets":player_row.get('ReceivingTargets',0),
                  "Receptions":player_row.get('Receptions',0),
                  "ReceptionPercentage":player_row.get('ReceptionPercentage',0),
                  "ReceivingYards":player_row.get('ReceivingYards',0),
                  "ReceivingYardsPerReception":player_row.get('ReceivingYardsPerReception',0),
                  "ReceivingTouchdowns":player_row.get('ReceivingTouchdowns',0),
                  "FumblesLost":player_row.get('FumblesLost',0),
                  "FumblesForced":player_row.get('FumblesForced',0),
                  "FumblesRecovered":player_row.get('FumblesRecovered',0),
                  "FumbleReturnTouchdowns":player_row.get('FumbleReturnTouchdowns',0),
                  "Interceptions":player_row.get('Interceptions',0),
                  "InterceptionReturnTouchdowns":player_row.get('InterceptionReturnTouchdowns',0),
                  "Sacks":player_row.get('Sacks',0),
                  "BlockedKicks":player_row.get('BlockedKicks',0),
                  "FieldGoalsMade":player_row.get('FieldGoalsMade',0),
                  "FieldGoalPercentage":player_row.get('FieldGoalPercentage',0),
                  "ExtraPointsMade":player_row.get('ExtraPointsMade',0),
                  "Touchdowns":player_row.get('Touchdowns',0),
                  "OffensiveSnapsPlayed":player_row.get('OffensiveSnapsPlayed',0),
                  "DefensiveSnapsPlayed":player_row.get('DefensiveSnapsPlayed',0),
                  "OffensiveTeamSnaps":player_row.get('OffensiveTeamSnaps',0),
                  "DefensiveTeamSnaps":player_row.get('DefensiveTeamSnaps',0),
                  "FantasyPointsFanDuel":player_row.get('FantasyPointsFanDuel',0),
                  "FantasyPointsDraftKings":player_row.get('FantasyPointsDraftKings',0),
                  "FieldGoalsMade0to19":player_row.get('FieldGoalsMade0to19',0),
                  "FieldGoalsMade20to29":player_row.get('FieldGoalsMade20to29',0),
                  "FieldGoalsMade30to39":player_row.get('FieldGoalsMade30to39',0),
                  "FieldGoalsMade40to49":player_row.get('FieldGoalsMade40to49',0),
                  "FieldGoalsMade50Plus":player_row.get('FieldGoalsMade50Plus',0),
                  "TeamID":player_row.get('TeamID',0),
                  "GlobalTeamID":player_row.get('GlobalTeamID',0)
                }

                alldata_rows.append(playerData)
            #end if playerposition
        #end for loop
      
        # Write our CSV to files 
        '''
        strToWrite1 = ""
        strToWrite2 = ""
        if (len(projectdata_cols) > 0) :
          strToWrite1 = "\n".join(projectdata_cols) + "\n"
        if (len(alldata_rows) > 0) :
          strToWrite2 = "\n".join(alldata_rows) + "\n"
        file = open(analysis_file,'wb') 
        file.write((strToWrite1 + strToWrite2).encode('utf-8')) 
        file.close()
        '''
        # NOW WRITE ALL THE DATA OUT TO THE FILE
        if (len(alldata_rows) > 0) :
          data["tableData"] = alldata_rows
          #data["firstObj"] = alldata_rows[0]
          with open(analysis_file, 'w') as datafile:
            json.dump(alldata_rows, datafile, ensure_ascii=False)   
        else:   
            data["errorMsg"] = "No data found"
        if (data["errorMsg"] == ""):
          data["success"] = "true"
      else:
        data["errorMsg"] = "Error in data submitted - Need Year"
    else:
      data["errorMsg"] = "Error in data submitted - No GET requests"
  
    return JsonResponse(data)

'''
*****************************************************************************************
LOAD DATA FOR STATS PAGE
- POST
- week : (int) nfl week of season (1-17 for reg)
- year : (int) 4 digit year value
- season : (str) should be 'Week', 'Post', 'Pre'
- site : (str) should be 'DK', 'Fanduel', 'FantasyDraft'
- slate : (str) should be name
*****************************************************************************************
'''
class Load_Stats_Data(JsonView):
  
  def post(self, request):
    data = []
    #data["errorMsg"] = ""
    #data["success"] = ""
    #data["tableData"] = []
    #data["firstObj"] = {}
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      analysisWeek = int(request.POST.get('week', 0))
      analysisYear = int(request.POST.get('year', 0))
      season = str(request.POST.get('season', '')) #should be 'Week', 'Post', 'Pre'
      site = str(request.POST.get('site', 'DK')) #should be 'DK', 'Fanduel', 'FantasyDraft'
      slate = str(request.POST.get('slate', '')) #should be name

      all_data = Player_Game_Stats.objects.filter(team_game_id__game_id__week__exact=analysisWeek).filter(team_game_id__game_id__season_year__exact=analysisYear).filter(team_game_id__game_id__season_type__exact=season)
      #all_data = Player_Game_Stats.objects.filter(team_game_id__game_id__week__exact=analysisWeek).filter(team_game_id__game_id__season_year__exact=analysisYear)
      
      player = {'player__fantasy_position', 'player__first_name', 'player__id', 'player__last_name', 'player__last_updated_date', 'player__name', 'player__player_game_stats_player', 'player__position', 'player__short_name', 'player__team__initials', 'player__team__full_name'}
      team_game = {'team_game__team__initials', 'team_game__opponent__initials', 'team_game__game__home_team__initials', 'team_game__game__away_team__initials', 'team_game__game__season_year', 'team_game__game__week', 'team_game__game__season_type', 'team_game__game__location_name', 'team_game__game__game_date', 'team_game__game__home_score', 'team_game__game__away_score', 'team_game__game__game_ot', 'team_game__team_is_home', 'team_game__score_summary', 'team_game__game_result'}
      player_stats = {'assisted_tackles', 'defensive_touchdowns', 'extra_points_attempted', 'extra_points_made', 'fantasy_point_snap_percentage', 'fantasy_point_snap_percentage_draft_kings', 'fantasy_point_snap_percentage_fan_duel', 'fantasy_point_snap_percentage_fantasy_draft', 'fantasy_point_snap_percentage_half_point_ppr', 'fantasy_point_snap_percentage_ppr', 'fantasy_point_snap_percentage_six_point_pass_td', 'fantasy_point_snap_percentage_yahoo', 'fantasy_points', 'fantasy_points_draft_kings', 'fantasy_points_fan_duel', 'fantasy_points_fantasy_draft', 'fantasy_points_half_point_ppr', 'fantasy_points_per_game', 'fantasy_points_per_game_draft_kings', 'fantasy_points_per_game_fan_duel', 'fantasy_points_per_game_fantasy_draft', 'fantasy_points_per_game_half_point_ppr', 'fantasy_points_per_game_ppr', 'fantasy_points_per_game_six_point_pass_td', 'fantasy_points_per_game_yahoo', 'fantasy_points_ppr', 'fantasy_points_six_point_pass_td', 'fantasy_points_yahoo', 'field_goal_percentage', 'field_goals_attempted', 'field_goals_longest_made', 'field_goals_made', 'fumbles', 'fumbles_forced', 'fumbles_lost', 'fumbles_recovered', 'id', 'intended_touch_snap_percentage', 'interceptions', 'passes_defended', 'passing_attempts', 'passing_completion_percentage', 'passing_completions', 'passing_interceptions', 'passing_rating', 'passing_touchdowns', 'passing_yards', 'passing_yards_per_attempt', 'played', 'player', 'player_id', 'player_url_string', 'points_allowed_by_defense_special_teams', 'quarterback_hit_snap_percentage', 'quarterback_hits', 'receiving_long', 'receiving_targets', 'receiving_touchdowns', 'receiving_yards', 'receiving_yards_per_reception', 'receiving_yards_per_target', 'reception_percentage', 'receptions', 'rush_snap_percentage', 'rushing_attempts', 'rushing_touchdowns', 'rushing_yards', 'rushing_yards_per_attempt', 'sack_snap_percentage', 'sack_yards', 'sacks', 'safeties', 'snaps_per_game', 'snaps_played', 'snaps_played_percentage', 'solo_tackles', 'special_teams_touchdowns', 'started', 'tackle_snap_percentage', 'tackles_for_loss', 'target_snap_percentage', 'team_game', 'team_game_id', 'total_tackles', 'touch_snap_percentage'}
      
      args = {*player, *player_stats}
      
      data = list(all_data.values(*args))
      #df = read_frame(all_data)
      #data = df.to_json()

    #resp = HttpResponse(data, content_type="application/json")
    #return(resp)

    return JsonResponse(data, safe=False)

'''
*****************************************************************************************
RELOAD SLATE SALARY DATA - 
 - POST
 - week : (int) nfl week of season (1-17 for reg)
 - year : (int) 4 digit year value
 - season : (str) should be 'Week', 'Post', 'Pre'
 - site : (str) should be 'DK', 'Fanduel', 'FantasyDraft'
*****************************************************************************************
'''
class Reload_Slates_Salary_Data(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["slates"] = []
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      analysisWeek = int(request.POST.get('week', 0))
      analysisYear = int(request.POST.get('year', 0))
      season = str(request.POST.get('season', 'Week')) #should be 'Week', 'Post', 'Pre'
      weekTxt = str(season) + str(analysisWeek)
      site = str(request.POST.get('site', 'DK')) #should be 'DK', 'Fanduel', 'FantasyDraft'
      data = Data_Manager.reload_salary_files(analysisYear, analysisWeek, season, site)
    else:
      data["errorMsg"] = "Error in data submitted - No GET requests"
  
    return JsonResponse(data)


'''
*****************************************************************************************
GET THE SLATES FROM DOMSTATION 
 - POST
 - week : (int) nfl week of season (1-17 for reg)
 - year : (int) 4 digit year value
 - season : (str) should be 'Week', 'Post', 'Pre'
 - site : (str) should be 'DK', 'Fanduel', 'FantasyDraft'
*****************************************************************************************
'''
class Get_Slates(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["slates"] = []
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      analysisWeek = int(request.POST.get('week', 0))
      currentWeek = int(request.POST.get('currentweek', 0))
      analysisYear = int(request.POST.get('year', 0))
      season = str(request.POST.get('season', 'REG')) #should be 'REG', 'POST', 'PRE'
      weekTxt = str(season) + str(analysisWeek)
      reload = str(request.POST.get('reload', 'true'))
      forceReload = reload == 'true'
      site = str(request.POST.get('site', 'DK')) #should be 'DK', 'Fanduel',
      if (site == 'DK'):
        site = 'draftkings'
      elif (site == 'Fanduel'):
        site = 'fanduel'
      else:
        site = site.toLowerCase();
      # https://domination.dfsarmy.com/api/v1/lineup-tool/slots?sport=nfl&site=draftkings&gameType=showdown
      # https://domination.dfsarmy.com/api/v1/lineup-tool/slots?sport=nfl&site=fanduel&gameType=single-game
      # https://domination.dfsarmy.com/api/v1/lineup-tool/archived-slots?sport=nfl&site=draftkings&gameType=showdown
      # https://domination.dfsarmy.com/api/v1/lineup-tool/archived-slots?sport=nfl&site=fanduel&gameType=single-game


      if (analysisYear != 0 and analysisYear > 2012 and analysisYear <= (datetime.now().year + 1)) :
        # IF WE NEED TO RELOAD DATA OR IF DATA DOES NOT EXIST FOR THIS WEEK ALREADY THEN DO THIS
        alldata_rows = []
  
        results_obj = Data_Manager.getWeekSlates(site, analysisYear, analysisWeek, currentWeek, forceReload);
        if (results_obj["success"] == 'true') :
            alldata_rows = results_obj["slates"]
        else :
            data["errorMsg"] = results_obj["errorMsg"]
            return JsonResponse(data)
        #.get('Data',[])
  

        if (len(alldata_rows) > 0 and data["errorMsg"] == "") :
            data["success"] = "true"
            data["slates"] = alldata_rows
        else:   
            data["errorMsg"] = "No data found"
      else:
        data["errorMsg"] = "Error in data submitted - Need Year"
    else:
      data["errorMsg"] = "Error in data submitted - No GET requests"
  
    return JsonResponse(data)

'''
*****************************************************************************************
GET THE GAMES FOR A SLATES FROM DOMSTATION 
 - POST
 - slateId : (str) id for the slate
 - week : (int) nfl week of season (1-17 for reg)
 - year : (int) 4 digit year value
 - season : (str) should be 'Week', 'Post', 'Pre'
 - site : (str) should be 'DK', 'Fanduel', 'FantasyDraft'
*****************************************************************************************
'''
class Get_Slate_Games(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["games"] = []
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      analysisWeek = int(request.POST.get('week', 0))
      slateId = str(request.POST.get('slateid', ''))
      analysisYear = int(request.POST.get('year', 0))
      season = str(request.POST.get('season', 'REG')) #should be 'REG', 'POST', 'PRE'
      weekTxt = str(season) + str(analysisWeek)
      reload = str(request.POST.get('reload', 'true'))
      forceReload = reload == 'true'
      site = str(request.POST.get('site', 'DK')) #should be 'DK', 'Fanduel',
      if (site == 'DK'):
        site = 'draftkings'
      elif (site == 'Fanduel'):
        site = 'fanduel'
      else:
        site = site.toLowerCase();

      if (analysisYear != 0 and analysisYear > 2012 and analysisYear <= (datetime.now().year + 1)) :
        # IF WE NEED TO RELOAD DATA OR IF DATA DOES NOT EXIST FOR THIS WEEK ALREADY THEN DO THIS
        alldata_rows = []
  
        results_obj = Data_Manager.getSlateGames(site, analysisYear, analysisWeek, slateId, forceReload);
        if (results_obj["success"] == 'true') :
            alldata_rows = results_obj["games"]
        else :
            data["errorMsg"] = results_obj["errorMsg"]
            return JsonResponse(data)
        #.get('Data',[])
  

        if (len(alldata_rows) > 0 and data["errorMsg"] == "") :
            data["success"] = "true"
            data["games"] = alldata_rows
        else:   
            data["errorMsg"] = "No data found"
      else:
        data["errorMsg"] = "Error in data submitted - Need Year"
    else:
      data["errorMsg"] = "Error in data submitted - No GET requests"
  
    return JsonResponse(data)
    
'''
*****************************************************************************************
GET THE PLAYERS FOR A SLATES FROM DOMSTATION 
 - POST
 - slateId : (str) id for the slate
 - week : (int) nfl week of season (1-17 for reg)
 - year : (int) 4 digit year value
 - season : (str) should be 'Week', 'Post', 'Pre'
 - site : (str) should be 'DK', 'Fanduel', 'FantasyDraft'
*****************************************************************************************
'''
class Get_Slate_Players(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["players"] = []
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      analysisWeek = int(request.POST.get('week', 0))
      slateId = str(request.POST.get('slateid', ''))
      analysisYear = int(request.POST.get('year', 0))
      season = str(request.POST.get('season', 'REG')) #should be 'REG', 'POST', 'PRE'
      weekTxt = str(season) + str(analysisWeek)
      reload = str(request.POST.get('reload', 'true'))
      forceReload = reload == 'true'
      site = str(request.POST.get('site', 'DK')) #should be 'DK', 'Fanduel',
      if (site == 'DK'):
        site = 'draftkings'
      elif (site == 'Fanduel'):
        site = 'fanduel'
      else:
        site = site.toLowerCase();

      if (analysisYear != 0 and analysisYear > 2012 and analysisYear <= (datetime.now().year + 1)) :
        # IF WE NEED TO RELOAD DATA OR IF DATA DOES NOT EXIST FOR THIS WEEK ALREADY THEN DO THIS
        alldata_rows = []
  
        results_obj = Data_Manager.getSlatePlayers(site, analysisYear, analysisWeek, slateId, forceReload);
        if (results_obj["success"] == 'true') :
            alldata_rows = results_obj["players"]
        else :
            data["errorMsg"] = results_obj["errorMsg"]
            return JsonResponse(data)
        #.get('Data',[])
  

        if (len(alldata_rows) > 0 and data["errorMsg"] == "") :
            data["success"] = "true"
            data["players"] = alldata_rows
        else:   
            data["errorMsg"] = "No data found"
      else:
        data["errorMsg"] = "Error in data submitted - Need Year"
    else:
      data["errorMsg"] = "Error in data submitted - No GET requests"
  
    return JsonResponse(data)
    

'''
*****************************************************************************************
GET THE SLATES WHICH ARE LOADED 
 - POST
 - week : (int) nfl week of season (1-17 for reg)
 - year : (int) 4 digit year value
 - season : (str) should be 'Week', 'Post', 'Pre'
 - site : (str) should be 'DK', 'Fanduel', 'FantasyDraft'
*****************************************************************************************
'''
class Get_Slates_old(JsonView):
  
  def post(self, request):
    data = {}
    data["errorMsg"] = ""
    data["success"] = ""
    data["slates"] = []
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      analysisWeek = int(request.POST.get('week', 0))
      analysisYear = int(request.POST.get('year', 0))
      season = str(request.POST.get('season', 'Week')) #should be 'Week', 'Post', 'Pre'
      weekTxt = str(season) + str(analysisWeek)
      site = str(request.POST.get('site', 'DK')) #should be 'DK', 'Fanduel', 'FantasyDraft'

      file_path = SITE_ROOT + STATIC_PROJECTS + 'weekupdate' + '/' + str(analysisYear) + '/' + str(weekTxt) + '/' + site + '/'
      slate_file = file_path + 'slates.csv'

      slate_content = ""
      if (analysisWeek != 0 and analysisYear != 0 and analysisWeek > 0 and analysisWeek < 18 and analysisYear > 2012 and analysisYear <= (datetime.now().year + 1)) :
        if (not os.path.exists(slate_file)):
          reloadStatus = Data_Manager.reload_salary_files(analysisYear, analysisWeek, season, site)
          if (reloadStatus["success"] != "true"):
            data["errorMsg"] = reloadStatus["errorMsg"]
    
        if (os.path.exists(slate_file)):
          with open(slate_file, 'r') as content_file:
            slate_content = content_file.read()

          slates = slate_content.splitlines()
          if (len(slates) > 0) :
            data["slates"] = slates
            data["success"] = "true"
          else:
            data["errorMsg"] = "Error: No slates found in slate list"
        else:
          data["errorMsg"] = "Error: No Slate Salary file found - try reloading salaries"
      else:
        data["errorMsg"] = "Error in data submitted - Need Week and Year"
    else:
      data["errorMsg"] = "Error in data submitted - No GET requests"
  
    return JsonResponse(data)

'''
*****************************************************************************************
SAVE FILE - Ajax call to save a file
 - POST
 - file-path : path to the file to be saved including filename
 - file-text : content to save to file
*****************************************************************************************
'''
class Save_File(JsonView):
  
#  def get_context_data(self, **kwargs):
#    data = super().get_context_data(**kwargs)
  def post(self, request):
    data = {}
    '''
    ALERT: JUST RETURNING TO PREVENT SECURITY ISSUES UNTIL THIS IS NEEDED
    '''
    return data
    
    data["errorMsg"] = ""
    data["success"] = ""
    if request.method == "POST":
      # logging.debug('Debug for post : ' + str(request.POST)) 
      file_path = request.POST.get('file-path', '')
      file_text = request.POST.get('file-text', '')
      if (NFL_Utilities(file_path, file_text)):
        data["success"] = "true"
      else:
        data["errorMsg"] = "Error saving file: " + file_path
    else:
      data["errorMsg"] = "Error in data submitted for saveFile - No GET requests"

    return JsonResponse(data)


'''
*****************************************************************************************
NFL STATS PAGE - main page for stats.
*****************************************************************************************
'''
class Showdown(TemplateView):
  template_name = "nfl_research/showdown.html"
  
  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    data['projects'] = [] #self.get_projects_array() #page no longer takes input - fully ajax
    return data

'''
*****************************************************************************************
NFL STATS PAGE - main page for stats.
*****************************************************************************************
'''
class NFL_Stats(TemplateView):
  template_name = "nfl_research/nfl_stats.html"
  
  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    data['projects'] = [] #self.get_projects_array() #page no longer takes input - fully ajax
    return data

  '''
  def get_projects_array(self):
    mypath = SITE_ROOT + STATIC_PROJECTS
    filenames = []
    directorynames = []
    for (dirpath, dirnames, fnames) in walk(mypath):
      filenames.extend(fnames)
      directorynames.extend(dirnames)
      break
  
    projectsArray = []
    for dir in directorynames:
      lastModified = time.ctime(max(os.path.getmtime(root) for root,_,_ in os.walk(mypath + dir)))
      projectsArray.append([dir, lastModified, mypath + dir])
    
    filenames = [x for x in filenames if x.find('.txt') >= 0]
  
    logging.debug('Debug for :'+str(filenames) + ' in : ' + str(directorynames))
    logging.debug('Debug for :' + str(time.ctime(max(os.path.getmtime(root) for root,_,_ in os.walk(mypath)))))
    return projectsArray
  '''

'''
*****************************************************************************************
Data Loader page - main page for reloading data.
*******************************\**********************************************************
'''
class Data_Loader(TemplateView):
  template_name = "nfl_research/data_loader_sportsdata.html"
  
  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    return data

