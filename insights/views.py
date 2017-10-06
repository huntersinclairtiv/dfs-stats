import sys
import logging
import time
import os
import re
from django.http import HttpResponse
from django.shortcuts import render, redirect
from bs4 import BeautifulSoup, Comment
import urllib.request
from urllib.request import Request, urlopen
import requests
import nltk
import nltk.corpus  
from nltk.text import Text, FreqDist, ContextIndex
from nltk.util import tokenwrap, LazyConcatenation
from nltk.metrics import f_measure, BigramAssocMeasures, TrigramAssocMeasures
from nltk.collocations import BigramCollocationFinder
from os import walk
import os.path
import zipfile
from django.http import JsonResponse

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

# @print_http_response
# Create your views here.
def home(request):
  return render(request, 'home.html', {})

