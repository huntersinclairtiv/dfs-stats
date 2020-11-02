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

requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL'
try:
    requests.packages.urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST = 'ALL'
except AttributeError:
    # no pyopenssl support used / needed / available
    pass

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
# logging.debug('A debug message!')
# logging.info('We processed %d records', len(processed_records))

#import matplotlib
#matplotlib.use('TkAgg')
#import matplotlib.pyplot as pyplot, mpld3

# 
# from tkinter import *
# root = Tk()
# def task():
#     print("hello")
#     root.after(2000, task)  # reschedule event in 2 seconds
# root.after(2000, task)
# root.mainloop()


class NFL_Utilities:
  #converts date objects in json to datetime object
  #used like j = json.loads(jsonText, object_hook=NFL_Utilities.parseMyJSONDates)
  def parseMyJSONDates(dct):
    if 'Date' in dct:
      timestamp = int(int(dct['Date'][6:-2])/1000)
      dct['Date'] = datetime.fromtimestamp(timestamp)
    return dct

  def convertJSONDate(dateVal):
    if (len(dateVal) > 8):
      timestamp = int(int(dateVal[6:-2])/1000)
      return datetime.fromtimestamp(timestamp)
    return dateVal

  def makeDirIfDoesNotExist(path):
    if not os.path.exists(path):
      try:
        os.makedirs(path)
      except OSError as e:
        logging.debug('ERROR for making directory: ' + str(path))
        if e.errno != errno.EEXIST:
          raise    

  def indexlower(array, word):
    for i, v in enumerate(array):
      if v.lower() == word.lower():
        logging.debug('Index of:'+str(i))
        return i
    return -1

  def print_http_response(f):
    """ Wraps a python function that prints to the console, and
    returns those results as a HttpResponse (HTML)"""

    class WritableObject:
      def __init__(self):
        self.content = []
      def write(self, string):
        self.content.append(string)

    def new_f(*args, **kwargs):
      printed = WritableObject()
      sys.stdout = printed
      f(*args, **kwargs)
      sys.stdout = sys.__stdout__
      return HttpResponse(['<BR>' if c == '\n' else c for c in printed.content ])
  
    return new_f

  def GetAllIndexes(arrObj, value):
    returnVal = []
    for idx, obj in enumerate(arrObj):
      if (obj == value) :
        returnVal.append(idx)
    return returnVal

  #RETURN index of key in dict
  def indexInDict(myDict, value):
      try:
          a = list(myDict.keys()).index(value)
      except ValueError:
          return -1
      else:
          return a

  def mk_int(s):
      s = s.strip()
      return int(s) if s else 0

  def saveFileWithContents(file_path, file_text):
      try:
        if (file_path and file_path != '') :
          pathIndex = str(file_path).find(STATIC_PROJECTS)
          # logging.debug('Debug for STATIC_PROJECTS : ' + str(STATIC_PROJECTS)) 
          # logging.debug('Debug for pathIndex : ' + str(pathIndex)) 
          if (pathIndex >= 0):
            file_path = SITE_ROOT + str(file_path)[pathIndex:]
          else:
            file_path = SITE_ROOT + str(file_path)
          # logging.debug('Debug for file-path : ' + str(file_path)) 
          file = open(file_path,'wb') 
          file.write(str(file_text).encode('utf-8')) 
          file.close()
          return true
        else:
          return false
      except IOError as err:
          print("I/O in saveFileWithContents error: {0}".format(err))
          return false
      except:
          print("Unexpected error in saveFileWithContents:", sys.exc_info()[0])
          return false

  def start_explore(request):
    data = {"errorMsg":"","success":"","page":"/nfl_research/explore_collect"}

    if request.method == "POST":
      form_action = str(request.POST.get('form-action', ''));
      # logging.debug('Debug for post : ' + str(request.POST)) 
      project_name = str(request.POST.get('project-name', ''))
      explore_name = str(request.POST.get('explore-name', ''))
      keywords_text = str(request.POST.get('keywords-text', ''))
      explore_name_scrubbed = re.sub('[^a-zA-Z0-9\n\.]', '_', explore_name)
      project_path = SITE_ROOT + STATIC_PROJECTS + project_name + "/"
      csv_path = project_path + "saved_explorations.csv"
      explore_root = project_path + "explorations/"
      explore_path = explore_root + explore_name + "/"
      explore_keywords_path = explore_path + explore_name_scrubbed + "_keywords.csv"

      #logging.debug('Debug for name : ' + explore_name) 
      if (not form_action) :
        data["errorMsg"] = "Not sure what button was pressed. Try again."
      elif (not project_name) :
        data["errorMsg"] = "No project name detected. Contact support"
      elif (not explore_name) :
        data["errorMsg"] = "You must provide a name for the Exploration"
      elif (not (re.match(r'[ \w-]+$', explore_name))):
        data["errorMsg"] = "Your exploration name contains illegal characters.  Please use only letters, numbers, _, or -"
      elif (not os.path.exists(project_path)):
        data["errorMsg"] = "The project folder can't be found - this is likely due to some bad characters is project name. Tell admin."
      elif (os.path.exists(explore_path)):
        data["errorMsg"] = "That exploration name already exists. Please create a unique new one."
      elif (os.path.exists(explore_keywords_path)):
        data["errorMsg"] = "That exploration name already exists. Please create a unique new one."
      elif ((form_action == 'assess') and (not keywords_text)) :
        data["errorMsg"] = "You can't assess NOTHING. Fill out keywords OR go to the Collect step."
      else:
        # start exploration - field validation done 
        if (form_action == 'assess'):
          # This is where we save keywords and skip to assessment page by just returning true  just check for empty
          data["page"] = "/nfl_research/explore_assess?projectname=" + project_name + "&explorename=" + explore_name
        else :
          # This is the "collect" action to start exploration
          data["page"] = "/nfl_research/explore_collect?projectname=" + project_name + "&explorename=" + explore_name
      
        # for both actions above we need to save keywords and add the new exploration to the list
        if (not os.path.exists(explore_root)):
          os.makedirs(explore_root)

        if (not os.path.exists(explore_path)):
          os.makedirs(explore_path)
      
        keywords_for_write = []
        keywords_text_array = keywords_text.splitlines()
        for keywordline in keywords_text_array :
          if (keywordline.strip()):
            keyvals = [x.strip() for x in keywordline.split(',') if x.strip()]
            keywords_for_write.extend(keyvals)
       
        keywords_count = len(keywords_for_write)
        file = open(explore_keywords_path,'wb') 
        file.write(str("\n".join(keywords_for_write)).encode('utf-8')) 
        file.close()

        if (not os.path.exists(csv_path)):
          file = open(csv_path,'wb') 
          file.write(str("name,path,scrubbed_name,keyword_count\n").encode('utf-8')) 
          file.close()
      
        new_explore_row = str(str(explore_name) + "," + str(explore_path) + "," + str(explore_name_scrubbed) + "," + str(keywords_count) + "\n")
        file = open(csv_path,'ab+') 
        file.write(str(new_explore_row).encode('utf-8')) 
        file.close()
  
        data["success"] = "true"
      # END IF ELSE form_action is None ( big if elif else field validation statements)
    else: #not POST
      data["errorMsg"] = "Error in data submitted - No GET requests"
  
    return JsonResponse(data)
