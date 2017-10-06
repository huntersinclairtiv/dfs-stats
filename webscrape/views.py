import sys
import logging
import time
import os
import re
import collections
from django.http import HttpResponse
from django.shortcuts import render, redirect
from bs4 import BeautifulSoup, Comment
import urllib.request
from datetime import datetime
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
  
def get_context(text, word, tokenMap, origText, span=2, separatorL=' ', separatorR=' ',width=80, lines=25):
  """
  Gets a context around ``word`` with the specified original text.

  :param text: The target body of Text() - type:Text(tokens)
  :param word: The target word or phrase - type: str
  :param tokenMap: The tokens with index or start and end in original text - type: array of arrays [["token", startIndex, endIndex],...]
  :param origText: The original text to pull context from - type: str
  :param width: The width of each line, in characters (default=80) - type:int
  :param lines: The number of lines to display (default=25) - type: int
  :param separatorL: left str separator for target phrase for instance "<b>" to bold. - type:str
  :param separatorR: left str separator for target phrase for instance "</b>" to bold. - type:str
   
  returns array of result strings
  """
  resultsArray = []
  tokenLinesArray = []
  lowerWord = word.lower().strip()
  half_width = (width - len(lowerWord) - 2) // 2
  half_token_count = half_width // 4 # approx number of tokens on either side of middle
  wordArr = [i.strip() for i in lowerWord.split(' ')]
  numWords = len(wordArr)
  currentWordNum = 0
  wordsFound = []
  numLines = 0
  startIndx = -1
  endIndx = -1
  
  for idx, tokenInfo in enumerate(tokenMap):
    if (len(tokenInfo) == 3) :
      if (numWords > 1) :
        if (wordArr[0] == tokenInfo[0]):
          #matches first word in phrase. Now check for surrounding words
          phraseExists = True
          wordsFound = [tokenInfo]
          for i, thisWord in enumerate(wordArr[1:]):
            endIdx = idx+span
            if endIdx > len(tokenMap):
              endIdx = len(tokenMap)
            theseTokens = [j[0] for j in tokenMap[idx+1:endIdx]]
            logging.debug('tokens spread:'+str(theseTokens))
            if (not (thisWord in theseTokens)):
              phraseExists = False
            else:
              logging.debug('idx:'+str(idx))
              logging.debug('theseTokens.index:'+str(theseTokens.index(thisWord)))
              for w in GetAllIndexes(theseTokens, thisWord):
                wordsFound.append(tokenMap[idx + w + 1])
              # wordsFound.append(tokenMap[idx + theseTokens.index(thisWord) + 1]) #old way of just adding first one
          logging.debug('phrase exists:'+str(phraseExists))
          logging.debug('wordsFound:'+str(wordsFound))
          if (phraseExists and (len(wordsFound) >= numWords)) :
            numLines += 1
            firstWordIndex = wordsFound[0][1]
            endWordEndIndex = wordsFound[0][2]
            for thisWord in wordsFound:
              if (thisWord[2] > endWordEndIndex):
                endWordEndIndex = thisWord[2]
            
            leftIndex = firstWordIndex - half_width
            if leftIndex < 0 :
              leftIndex = 0
            rightIndex = endWordEndIndex + half_width
            if (rightIndex > len(origText)):
              rightIndex = len(origText)
            left = origText[leftIndex:firstWordIndex]
            middle = ''
            right = origText[endWordEndIndex:rightIndex]
            
            wordsFoundSorted = sorted(wordsFound, key=lambda x: x[1])
            lastIndex = 0
            for idx2, sortedWord in enumerate(wordsFoundSorted):
              logging.debug('lastIndex:'+str(lastIndex))
              logging.debug('sortedWord1:'+str(sortedWord[1]))
              logging.debug('sortedWord2:'+str(sortedWord[2]))
              logging.debug('word:'+str(origText[sortedWord[1]:sortedWord[2]]))
              if (idx2 == 0):
                middle = separatorL + origText[sortedWord[1]:sortedWord[2]] + separatorR
              else:
                logging.debug('inbetween:'+str(origText[lastIndex:sortedWord[1]]))
                middle = middle + origText[lastIndex:sortedWord[1]] + separatorL + origText[sortedWord[1]:sortedWord[2]] + separatorR
              lastIndex = sortedWord[2]

            middle = middle + origText[lastIndex:endWordEndIndex]
            
            # Get the very first index of tokens and the very last
            if startIndx < 0 :
              startIndx = idx - half_token_count
              if (startIndx < 0):
                startIndx = 0
            endIndx = idx + half_token_count
            if (endIndx > len(tokenMap)):
              endIndx = len(tokenMap)        

            resultsArray.append(str(left + middle + right))
            # resultsArray.append(str(origText[firstWordIndex:endWordEndIndex]))   # for checking original middle
           
      else :
        #single word
        if (tokenInfo[0] == lowerWord) :
          numLines += 1
          wordIndex = tokenInfo[1]
          wordIndexEnd = tokenInfo[2]
          leftIndex = wordIndex - half_width
          if leftIndex < 0 :
            leftIndex = 0
          rightIndex = wordIndexEnd + half_width
          if (rightIndex > len(origText)):
            rightIndex = len(origText)
          left = origText[leftIndex:wordIndex]
          middle = origText[wordIndex:wordIndexEnd]
          right = origText[wordIndexEnd:rightIndex]

          # Get the very first index of tokens and the very last
          if startIndx < 0 :
            startIndx = idx - half_token_count
            if (startIndx < 0):
              startIndx = 0
          endIndx = idx + half_token_count
          if (endIndx > len(tokenMap)):
            endIndx = len(tokenMap)

          resultsArray.append(str(left + separatorL + middle + separatorR + right))         

  if (startIndx < 0):
    slicedTokens = []
  else :
    slicedTokens = [x[0] for x in tokenMap[startIndx:endIndx]]

  lines = min(lines, numLines)
  if (numLines > 0):
    finalArr = ["Displaying %s of %s matches:" % (lines, numLines)]
    finalArr.extend(resultsArray)
  else :
    finalArr = ["No Matches"]
  return [finalArr, lines, slicedTokens]
  

def get_concordance_tokens(text, word, width=80):
  """
  Gets a concordance for ``word`` with the specified context window.

  :param text: The target body of Text()
  :type text: Text(tokens)
  :param word: The target word
  :type word: str
  :param width: The width of each line, in characters (default=80)
  :type width: int

  returns array of result strings
  """
  concord = nltk.ConcordanceIndex(text.tokens, key = lambda s: s.lower())

  half_width = (width - len(word) - 2) // 2
  context = width // 4 # approx number of words of context
  results_list = []

  offsets = concord.offsets(word)
  if offsets:
    for i in offsets:
      # logging.debug('Offset of:'+str(i))
      start = i-context
      index = context
      if (start < 0):
        index = context + start
        start = 0
      end = i+context
      if (end > len(concord._tokens)):
        end = len(concord._tokens)
      results_list.append([concord._tokens[start:end], index])

  return results_list


def get_concordance(text, word, separatorL=' ', separatorR=' ',width=80, lines=25):
  """
  Gets a concordance for ``word`` with the specified context window.

  :param text: The target body of Text()
  :type text: Text(tokens)
  :param word: The target word
  :type word: str
  :param width: The width of each line, in characters (default=80)
  :type width: int
  :param lines: The number of lines to display (default=25)
  :type lines: int
  :param separatorL: left str separator for target phrase for instance "<b>" to bold.
  :param separatorR: left str separator for target phrase for instance "</b>" to bold.
   
  returns array of result strings
  """
  lowerWord = word.lower()
  concordArr = get_concordance_tokens(text, lowerWord, width)

  half_width = (width - len(lowerWord) - 2) // 2
  context = width // 4 # approx number of words of context
  results_list2 = []

  if len(concordArr) > 0:
    lines = min(lines, len(concordArr))
    results_list2.append("Displaying %s of %s matches:" % (lines, len(concordArr)))
    for concordGroup in concordArr:
      concord = concordGroup[0]
      index = concordGroup[1]
      # logging.debug('tokens of:'+str(concord))

      if lines <= 0:
        break
      # index = indexlower(concord, lowerWord)
      if index: 
        left = (' ' * half_width +
                ' '.join(concord[0:index]))
        right = ' '.join(concord[index+1:len(concord)])
        toCrop = half_width
        if (toCrop > len(left)):
          toCrop = len(left)         
        left = left[-toCrop:]
        toCrop = half_width
        if (toCrop > len(left)):
          toCrop = len(left)
        right = right[:toCrop]
        results_list2.append(left + separatorL + concord[index] + separatorR + right)
        lines -= 1
  else:
    results_list2.append("No matches")
  return [results_list2, len(concordArr)]

def get_concordance_ngrams_tokens(text, phrase, width=80):
  """
  Gets a concordance for ``phrase`` ngrams with the specified context window.

  :param text: The target body of Text()
  :type text: Text(tokens)
  :param phrase: The target phrase
  :type phrase: str
  :param width: The width of each line, in characters (default=80)
  :type width: int
  
  returns array of result strings
  """
  #concordance replication via https://simplypython.wordpress.com/2014/03/14/saving-output-of-nltk-text-concordance/

  half_width = (width - len(phrase) - 2) // 2
  left_margin = width // 4 # approx number of words of context
  right_margin = left_margin

  phraseList=phrase.split(' ')

  c = nltk.ConcordanceIndex(text.tokens, key = lambda s: s.lower())

  #Find the offset for each token in the phrase
  offsets=[c.offsets(x) for x in phraseList]
  offsets_norm=[]
  #For each token in the phraselist, find the offsets and rebase them to the start of the phrase
  for i in range(len(phraseList)):
    offsets_norm.append([x-i for x in offsets[i]])
  #We have found the offset of a phrase if the rebased values intersect
  #--
  # http://stackoverflow.com/a/3852792/454773
  #the intersection method takes an arbitrary amount of arguments
  #result = set(d[0]).intersection(*d[1:])
  #--
  intersects=set(offsets_norm[0]).intersection(*offsets_norm[1:])

  #concordance_array = ([text.tokens[list(map(lambda x: x-left_margin if (x-left_margin)>0 else 0,[offset]))[0]:offset+len(phraseList)+right_margin] for offset in intersects])

  concordance_array = []
  for offset in intersects:
    left = offset - left_margin
    index = left_margin
    if (left < 0):
      index = left_margin + left
      left = 0
    right = offset + len(phraseList) + right_margin
    if (right > len(text.tokens)):
      right = len(text.tokens)
    # start = list(map(lambda x: x-left_margin if (x-left_margin)>0 else 0,[offset]))[0]
    # end = offset+len(phraseList)+right_margin
    concordance_array.append([text.tokens[left:right], index])
  
  
  return concordance_array

def get_concordance_ngrams(text, phrase, separatorL=' ', separatorR=' ',width=80, lines=25):
  """
  Gets a concordance for ``phrase`` ngrams with the specified context window.

  :param text: The target body of Text()
  :type text: Text(tokens)
  :param phrase: The target phrase
  :type phrase: str
  :param width: The width of each line, in characters (default=80)
  :type width: int
  :param lines: The number of lines to display (default=25)
  :type lines: int
  :param separatorL: left str separator for target phrase for instance "<b>" to bold.
  :param separatorR: left str separator for target phrase for instance "</b>" to bold.
  
  returns array of result strings
  """
  half_width = (width - len(phrase) - 2) // 2
  concordArr = get_concordance_ngrams_tokens(text, phrase, width)
  phraseLen = len(phrase.split(' '))
  outputs = []
  results_list2 = []
  if len(concordArr) > 0:
    lines = min(lines, len(concordArr))
    results_list2.append("Displaying %s of %s matches:" % (lines, len(concordArr)))
    for con_sub_group in concordArr:
      concord = con_sub_group[0]
      index = con_sub_group[1]

      if lines <= 0:
        break

      if index: 
        left = (' ' * half_width +
                ' '.join(concord[0:index]))
        right = ' '.join(concord[index+phraseLen:len(concord)])
        toCrop = half_width
        if (toCrop > len(left)):
          toCrop = len(left)         
        left = left[-toCrop:]
        toCrop = half_width
        if (toCrop > len(left)):
          toCrop = len(left)
        right = right[:toCrop]
        results_list2.append(left + separatorL + ''.join([x+' ' for x in concord[index:index+phraseLen]]) + separatorR + right)
        lines -= 1
  else:
    results_list2.append("No matches")
  return [results_list2, len(concordArr)]


def getConcordanceTokensForKeyword(myText, phrase, width=80):
  lowerPhrase = phrase.lower()
  concordArr = []
  if (len(lowerPhrase.split(' ')) > 0):
    concordArr = get_concordance_ngrams_tokens(myText, lowerPhrase, width)
  else:
    concordArr = get_concordance_tokens(myText, lowerPhrase, width)
  
  tokens = []
  if (len(concordArr) > 0):
    for concord in concordArr:
      tokens.extend(concord[0])
  
  return tokens


def getCollocationsForKeyword(fdArray, myText, my_stopwords, phrase, width=80, num=20, window_size=2, lowerlimit=2):
  lowerPhrase = phrase.lower()
  tokens = getConcordanceTokensForKeyword(myText, lowerPhrase, width)
  logging.debug('Debug for tokens: '+str(tokens))
  newText = Text(tokens)
  collos = get_collocations(fdArray, newText, my_stopwords, num, window_size, lowerlimit)
  
  return collos


def collocations2(myText):
  bigram_measures = nltk.collocations.BigramAssocMeasures()
  trigram_measures = nltk.collocations.TrigramAssocMeasures()

  # change this to read in your data
  finder = BigramCollocationFinder.from_words(myText)

  # only bigrams that appear 3+ times
  finder.apply_freq_filter(3) 

  # return the 10 n-grams with the highest PMI
  collocations = finder.nbest(bigram_measures.pmi, 10)
  return collocations

def get_collocations(fdArray, myText, my_stopwords, scoreDictArr, colloProbDict, num=20, window_size=2, lowerlimit=2):
  """
  Print collocations derived from the text, ignoring stopwords.

  :seealso: find_collocations
  :param num: The maximum number of collocations to print.
  :type num: int
  :param window_size: The number of tokens spanned by a collocation (default=2)
  :type window_size: int
  """

  from nltk.corpus import stopwords
  ignored_words = stopwords.words('english')
  words = myText.tokens
  words = [i for i in words if (len(i) >= 2 and (not i.lower() in ignored_words) and (not i.lower() in my_stopwords))]
  finder = BigramCollocationFinder.from_words(words, window_size)
  finder.apply_freq_filter(lowerlimit)
  finder.apply_word_filter(lambda w: (len(w) < 2 or (w.lower() in ignored_words) or (w.lower() in my_stopwords)))
  bigram_measures = BigramAssocMeasures()
  # collocations = finder.nbest(bigram_measures.likelihood_ratio, num)

  ngrams = finder.score_ngrams( bigram_measures.likelihood_ratio  )
  #bigrams = [tuple(words[i:i + window_size]) for i in range(len(words) - 1)]
  skipNum = 0
  if ((window_size-2) > 0):
    skipNum = window_size-2
  bigrams = list(skipgrams(words, 2, skipNum))
  # logging.debug('Debug for bigrams: '+str(bigrams))
  ngramCount = len(bigrams)
  scoreDictArr[1] = ngramCount
  ngram_counter = 0
  bottomPosAdjVal = scoreDictArr[2]
  for key, scores in ngrams:
    colloProbDict[key[0]].append((key[1], scores)) #store first word of collo in dict to lookup top X collo words for each token.
  for key in bigrams:
    posScore = 1.0 - ((ngram_counter / ngramCount) * bottomPosAdjVal)
    # scoreDictArr[3][key].append((key[1], scores))
    if (key in scoreDictArr[3]) :
      scoreDictArr[3][key]['indices'].append(ngram_counter) #add the index number to the first item in array
      scoreDictArr[3][key]['total_score'] += posScore
    else :
      scoreDictArr[3][key] = {}
      scoreDictArr[3][key]['indices'] = [ngram_counter]
      scoreDictArr[3][key]['total_score'] = posScore
    ngram_counter += 1
  #end for loop

  items = finder.ngram_fd
  # logging.debug('Debug for item: '+str([(k, items[k]) for k in sorted(items, key=items.get, reverse=True)]))
  fdArray.append(items)
  sortVal = [(k, items[k]) for k in sorted(items, key=items.get, reverse=True) if (not (str(k[0] + " " + k[1]).lower().strip() in my_stopwords))]

  return sortVal[:num]
  # return collocations
  # colloc_strings = [w1+' '+w2 for w1, w2 in collocations]
  # return tokenwrap(colloc_strings, separator="; ")

def getTotalFreqDistForCollos(fdArray, my_stopwords, num=20):
  
  '''  This was to test to make sure it worked how I thought below
  items = []
  for item in fdArray:
    #sortedFdArray = [(k, items[k]) for k in sorted(item, key=item.get, reverse=True)]
    # logging.debug('Debug for item: '+str([(k, item[k]) for k in sorted(item, key=item.get, reverse=True)]))
    for fdItem in item:
      foundIt = False
      for idx, myItem in enumerate(items):
        if (fdItem[0] == myItem[0][0] and fdItem[1] == myItem[0][1]):
          items[idx][1] += item[fdItem]
          foundIt = True
      if (not foundIt):
        items.append([fdItem, item[fdItem]])
  sortVal = sorted(items, key=lambda x: x[1], reverse=True)
            
  # logging.debug('Debug for item: '+str(sortVal))

  '''
  items = FreqDist()
  for item in fdArray:
    items += item

  sortVal = [(k, items[k]) for k in sorted(items, key=items.get, reverse=True) if (not (str(k[0] + " " + k[1]).lower().strip() in my_stopwords))]


  '''
  Example:
  [
    [
      ('crm', 'crm'), 
      [10, 3, 3, 3, 464, 5, 488]
    ], 
    [
      ('crm', 'servic'), 
      [3, 0, 0, 0, 73, 0, 76]
    ],
    ...
  ] 
  '''

  totalsArray = []
  for fd in sortVal[:num]:
    perUrlArray = []
    for item in fdArray:
      perUrlArray.append(item[fd[0]])
    perUrlArray.append(fd[1])
    totalsArray.append([fd[0], perUrlArray])
  
  # logging.debug('Debug for item: '+str(totalsArray))
    
  return totalsArray

# pass in fdArray with the FreqDist object in the index 0 of inner array
def getFreqDistArrayForAllWords(fdArray, colHeadArray):
  items = FreqDist()
  for item in fdArray:
    items += item[0]

  sortVal = [(k, items[k]) for k in sorted(items, key=items.get, reverse=True)]
  totalsArray = []

  for urlRow in fdArray:
    perUrlArray = []
    perUrlArray.extend(urlRow[1].split(','))
    for fd in sortVal:
      perUrlArray.append(str(urlRow[0][fd[0]]))
    totalsArray.append(','.join(perUrlArray))

  
  totalRowArray = [] #totals row
  for i in range(len(colHeadArray)):
    if (i <= 1):
      totalRowArray.append('Totals')
    else:
      totalRowArray.append('')

  for fd in sortVal:
    colHeadArray.append(str(fd[0]).replace(',','.'))
    totalRowArray.append(str(fd[1]))
  totalsArray.insert(0, ','.join(colHeadArray))
  totalsArray.append(','.join(totalRowArray))
   
  return totalsArray

#RETURN index of key in dict
def indexInDict(myDict, value):
    try:
        a = list(myDict.keys()).index(value)
    except ValueError:
        return -1
    else:
        return a

# pass in fdArray with the FreqDist object in the index 0 of inner array
# charLen is the min length of the word to return
# count is the min number of occurances inf frequency dist
# ranking type is the setting on what to display freq, freqavg, position, firstpos
# num is the total max number to return in list
# tidyDataPerUrl is array of url arrays containing all the position scores for each word for each url.
def getFreqDistAvgArrayForAllWords(fdArray, tidyDataPerUrl=[], num=50, rankingType='freqavg', charLen=2, count=1, my_stopwords=[], group_by='url', grouping_calc='highest', indexOfColHead=0, allurl_rows=[], allheads=[]):
  # logging.debug('Debug for FDARRAY: '+str(fdArray))
  items = FreqDist()
  for item in fdArray:
    items += item

  # logging.debug('Debug for ITEMS: '+str(items.items()))
  avgArr = []
  for item in items:
    urlAvgArr = []
    urlFreqArr = []
    urlPosScoreArr = collections.OrderedDict()
    urlFirstPosScoreArr = []
    urlPerArr = collections.OrderedDict()
    numUrls = 0
    urlsWithPos = 0
    totalTokenCnt = 0
    totalThisTokenCnt = 0
    maxFreqCnt = 0
    avgSum = 0
    maxAvg = 0
    posScoreTotal = 0
    maxScore = 0
    posFirstScoreTotal = 0
    maxFirstScore = 0
    '''  LOOP through all URLs and add value for each to the arrays which we add for each keyword.
          This is also where we will do any groupings
    '''
    for urlCnt, urlRow in enumerate(fdArray):
      # Get the indices of this keyword in each token array for each url:
      # GetAllIndexes(tidyDataPerUrl[urlCnt])
      tokenScoreDict = tidyDataPerUrl[urlCnt][3] #get score dictionary for keywords for this url
      bottomPosAdjVal = tidyDataPerUrl[urlCnt][2] #get the last keywords pos value default 0.50
      #urlTokenCount = len(urlRow) #get length of freqDist dict # NOTE: THIS IS NOT CORRECT - this is count of unique tokens
      urlTokenCount = tidyDataPerUrl[urlCnt][1] #get the total count of all keywords or keyphrases occurances
      tokenScore = 0
      firstPosScore = 0
      if (item in tokenScoreDict):
        tokenScore = tokenScoreDict[item]['total_score'] #get specific words score
        firstPosIdx = tokenScoreDict[item]['indices'][0] #get for first position of this word for this url
      totalTokenCnt += urlTokenCount
      freqCount = 0
      posScore = 0 #score base on position divided by total number of tokens - inverted
      avgTokenDist = 0 #avg of occurrence of token to total num of tokens for this url
      if (urlTokenCount > 0):
        freqCount = urlRow.get(item, 0)
        if (freqCount > maxFreqCnt):
          maxFreqCnt = freqCount #change max to value if this one is bigger than last
        avgTokenDist = freqCount/urlTokenCount
        if (avgTokenDist > maxAvg):
          maxAvg = avgTokenDist #change max to value if this one is bigger than last
        totalThisTokenCnt += freqCount
        if (tokenScore > 0) : 
          posScore = tokenScore
          if (posScore > maxScore):
            maxScore = posScore
          firstPosScore = 1.0 - ((firstPosIdx / urlTokenCount) * bottomPosAdjVal)
          if (firstPosScore > maxFirstScore):
            maxFirstScore = firstPosScore
          urlsWithPos += 1
      numUrls += 1
      avgSum += avgTokenDist
      posScoreTotal += posScore
      posFirstScoreTotal += firstPosScore
      urlAvgArr.append(avgTokenDist)
      urlFreqArr.append(freqCount)
      #urlPosScoreArr.append(posScore)
      urlColValue = allurl_rows[urlCnt][indexOfColHead]
      if (urlColValue in urlPerArr):
        urlPerArr[urlColValue]['groupCount'] += 1
        urlPerArr[urlColValue]['groupScoreTotal'] += posScore
        if (posScore > 0):
          urlPerArr[urlColValue]['groupCountWithPos'] += 1

        ''' THIS IS WHERE WE WOULD CHECK FOR "HIGHEST" "TOTAL" "ETC" '''
        ''' TODO - ADD for other 3 - POSITION COMPLETE EXCEPT FOR KEYWORD TOTALS / AVGERGES / ETC '''
        if (grouping_calc == 'avg'):
          if (urlPerArr[urlColValue]['groupCount'] > 0):
            urlPerArr[urlColValue]['groupPosScore'] = urlPerArr[urlColValue]['groupScoreTotal'] / urlPerArr[urlColValue]['groupCount']
          else :
            urlPerArr[urlColValue]['groupPosScore'] = 0       
        elif (grouping_calc == 'nonzero'):
          if (urlPerArr[urlColValue]['groupCountWithPos'] > 0):
            urlPerArr[urlColValue]['groupPosScore'] = urlPerArr[urlColValue]['groupScoreTotal'] / urlPerArr[urlColValue]['groupCountWithPos']
          else :
            urlPerArr[urlColValue]['groupPosScore'] = 0       
        elif (grouping_calc == 'total'):
          urlPerArr[urlColValue]['groupPosScore'] += posScore        
        else :  # grouping_calc == 'highest'
          if (posScore > urlPerArr[urlColValue]['groupPosScore']): #check and only store highest for group
            urlPerArr[urlColValue]['groupPosScore'] = posScore        
      else : #else grouping is not yet added - so just add value
        urlPerArr[urlColValue] = {'groupScoreTotal':posScore, 'groupCount':1, 'groupCountWithPos':0, 'groupPosScore':0}
        if (posScore > 0):
          urlPerArr[urlColValue]['groupCountWithPos'] = 1
        if (urlPerArr[urlColValue]['groupCountWithPos'] <= 0 and (grouping_calc == 'nonzero')):
          urlPerArr[urlColValue]['groupPosScore'] = 0
        else :
          urlPerArr[urlColValue]['groupPosScore'] = posScore
      
      urlPosScoreArr[urlColValue] = urlPerArr[urlColValue]['groupPosScore']
      urlFirstPosScoreArr.append(firstPosScore)
    # end of urls loop

    avgAvg = 0  #avg of the averages of this token for each url. 
    freqAvg = 0
    posScoreAvg = 0
    posFirstScoreAvg = 0
    if (numUrls > 0):
      avgAvg = avgSum / numUrls
      freqAvg = totalThisTokenCnt / numUrls
      posScoreAvg = posScoreTotal / numUrls
      posFirstScoreAvg = posFirstScoreTotal / numUrls
    nonZeroAvgAvg = 0 #average of non zero values
    nonZeroFreqAvg = 0
    nonZeroPosScoreAvg = 0
    nonZeroPosFirstScoreAvg = 0
    if (urlsWithPos > 0):
      nonZeroAvgAvg = avgSum / urlsWithPos
      nonZeroFreqAvg = totalThisTokenCnt / urlsWithPos
      nonZeroPosScoreAvg = posScoreTotal / urlsWithPos
      nonZeroPosFirstScoreAvg = posFirstScoreTotal / urlsWithPos
    # avgRaw = 0  #avg of this tokens total count across total tokens count for all sites    
    # if (totalTokenCnt > 0):
    #  avgRaw = totalThisTokenCnt / totalTokenCnt #TODO - I think we are ditching this value
    urlAvgArr.append(avgSum) #Total of all urls avg values
    urlAvgArr.append(avgAvg) #Average of all urls avg values
    urlAvgArr.append(nonZeroAvgAvg) #Average of all urls non zero avg values
    urlAvgArr.append(maxAvg) #max url avg value.
    urlAvgArr.append(urlsWithPos) #num of non-zero urls
    
    urlFreqArr.append(totalThisTokenCnt)
    urlFreqArr.append(freqAvg)
    urlFreqArr.append(nonZeroFreqAvg)
    urlFreqArr.append(maxFreqCnt)
    urlFreqArr.append(urlsWithPos)
    
    '''
    urlPosScoreArr.append(posScoreTotal)
    urlPosScoreArr.append(posScoreAvg)
    urlPosScoreArr.append(nonZeroPosScoreAvg)
    urlPosScoreArr.append(maxScore)
    urlPosScoreArr.append(urlsWithPos)
    '''
    urlPosScoreArr['col_total'] = posScoreTotal
    urlPosScoreArr['col_avg'] = posScoreAvg
    urlPosScoreArr['col_nonzeroavg'] = nonZeroPosScoreAvg
    urlPosScoreArr['col_max'] = maxScore
    urlPosScoreArr['col_occurs'] = urlsWithPos

    urlFirstPosScoreArr.append(posFirstScoreTotal)
    urlFirstPosScoreArr.append(posFirstScoreAvg)
    urlFirstPosScoreArr.append(nonZeroPosFirstScoreAvg)
    urlFirstPosScoreArr.append(maxFirstScore)
    urlFirstPosScoreArr.append(urlsWithPos)

    #logging.debug('Debug for URLAVGARR: '+str(item)+ ' - ' +str(urlFreqArr))
    sortValue = avgSum
    if (rankingType == 'freq') :
      sortValue = totalThisTokenCnt
    elif (rankingType == 'position') :
      sortValue = posScoreTotal
    elif (rankingType == 'firstpos') :
      sortValue = posFirstScoreTotal
    avgArr.append([item, urlAvgArr, urlFreqArr, urlPosScoreArr, urlFirstPosScoreArr, sortValue])

  logging.debug('Debug for PRESORTED: '+str(avgArr))
  # sortVal = sorted(avgArr, key=lambda x: x[5], reverse=True)
  if (not isinstance(item, str)):
    sortVal = sorted((w for w in avgArr if len(w[0][0]) >= charLen and len(w[0][1]) >= charLen and w[2][-5] > count and (not (str(w[0][0] + " " + w[0][1]).lower().strip() in my_stopwords))), key=lambda x: x[5], reverse=True)
  else:
    sortVal = sorted((w for w in avgArr if len(w[0]) >= charLen and w[2][-1] > count), key=lambda x: x[5], reverse=True)
  logging.debug('Debug for SORTED: '+str(sortVal))
  
  return sortVal[:num]



# Not needed or used
def format_concordance(concord, keyphrase):
  concordModdedIndex = concord.lower().find(keyphrase)
  keyphraseLen = keyphrase.len()
  concordModded = concord[:-(concord.len() - concordModdedIndex)] + "<b>" + concord[concordModdedIndex:concordModdedIndex+keyphraseLen] + "</b>" + concord[:(concordModdedIndex + keyphraseLen)]

'''
def get_long_words(text1, charLen=7):
  V = set(text1)
  fdist1 = FreqDist(text1)
  long_words = [w for w in V if len(w) > charLen]
  # return sorted(long_words)
  return sorted(((w, fdist1[w]) for w in V if len(w) > charLen), key=lambda x: x[1], reverse=True)

def get_top_freq_words(fdArray, text1, count=50):
  from nltk.corpus import stopwords
  ignored_words = stopwords.words('english')
  V = set(text1)
  fdist1 = FreqDist(text1)
  fdArray.append(fdist1)
  # return fdist1.most_common(count)
  return sorted(((w, fdist1[w]) for w in V if len(w) > 2 and not (w.lower() in ignored_words)), key=lambda x: x[1], reverse=True)[:count]

def get_freq_long_words(fdArray, text1, charLen=7, count=5):
  V = set(text1)
  fdist1 = FreqDist(text1)
  fdArray.append(fdist1)
  return sorted(((w, fdist1[w]) for w in V if len(w) > charLen and fdist1[w] > count), key=lambda x: x[1], reverse=True)
'''

def get_long_words(fdist1, charLen=7):
  # long_words = [w for w in textSet if len(w) > charLen]
  # return sorted(long_words)
  return sorted(((w[0], w[1]) for w in fdist1.items() if len(w[0]) > charLen), key=lambda x: x[1], reverse=True)

def get_top_freq_words(fdist1, count=50, minFreq=0):
  from nltk.corpus import stopwords
  ignored_words = stopwords.words('english')
  # return fdist1.most_common(count)
  return sorted(((w[0], w[1]) for w in fdist1.items() if len(w[0]) > 2 and not (w[0].lower() in ignored_words) and w[1] > minFreq), key=lambda x: x[1], reverse=True)[:count]

def get_freq_long_words(fdist1, charLen=7, count=5):
  return sorted(((w[0], w[1]) for w in fdist1.items() if len(w[0]) > charLen and w[1] > count), key=lambda x: x[1], reverse=True)

def getTotalFreqDistForLongWords(fdArray, num=50, charLen=7, count=5):
  items = FreqDist()
  for item in fdArray:
    items += item

  sortVal = sorted(((w[0], w[1]) for w in items.items() if len(w[0]) > charLen and w[1] > count), key=lambda x: x[1], reverse=True)
  
  totalsArray = []
  for fd in sortVal[:num]:
    perUrlArray = []
    for item in fdArray:
      perUrlArray.append(item[fd[0]])
    perUrlArray.append(fd[1])
    totalsArray.append([fd[0], perUrlArray])
    
  return totalsArray

def getTotalFreqDistForWords(fdArray, num=50):
  from nltk.corpus import stopwords
  ignored_words = stopwords.words('english')

  items = FreqDist()
  for item in fdArray:
    items += item

  sortVal = sorted(((w[0], w[1]) for w in items.items() if len(w[0]) > 2 and not (w[0].lower() in ignored_words)), key=lambda x: x[1], reverse=True)
  
  totalsArray = []
  for fd in sortVal[:num]:
    perUrlArray = []
    for item in fdArray:
      perUrlArray.append(item[fd[0]])
    perUrlArray.append(fd[1])
    totalsArray.append([fd[0], perUrlArray])
    
  return totalsArray

class Analyses(object):
  def __init__(self):
    self.allurls = []
    self.allkeys = []
    self.results = []
    self.concordance = []
    self.collocations = []
    self.long_words = []
    self.top_freq_words = []
    self.freq_long_words = []
    self.error = ''

class Analysis(object):
  def __init__(self):
    self.url = ""
    self.filename = ""
    self.key = ""
    self.concordance = []
    self.collocations = []
    self.long_words = []
    self.top_freq_words = []
    self.freq_long_words = []
    self.error = ''


# @print_http_response
# Create your views here.
def index(request):
  my_stopwords = []
  htmlResults = Analyses()
  if request.method == "POST":
    allurls = request.POST['urls'].splitlines()
    allkeys = []
    if (request.POST.get('newkeyphrase', False)):
      allkeys.append(request.POST.get('newkeyphrase', ''))
    else:
      allkeys = request.POST['keyphrases'].splitlines()
    htmlResults.allurls = allurls
    htmlResults.allkeys = allkeys
    htmlResults.urlstext = request.POST['urls']
    htmlResults.keystext = request.POST['keyphrases']

    sankeytext = ""
    fdColloArray = []
    fdArray = []
    for url in allurls :
      htmlResult = Analysis()
      htmlResult.url = url

      req = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
      html = req.text

      # url = allurls[0] # 'https://worldview.stratfor.com/'
      # req = Request(url, headers={'User-Agent': 'Googlebot'})
      # with urllib.request.urlopen(req) as response:
      #  html = response.read()

      soup = BeautifulSoup(html, 'html.parser', from_encoding="utf-8")

      for script in soup(["script", "style"]):
        script.decompose()    # rip it out

      if (soup.body is not None):
        justtext = soup.body.get_text(separator=u' ')
        filename = url.replace(".", "_").replace("://", "_").replace("/", "_") + '.txt'
        htmlResult.filename = filename.replace('.txt', '')
  
        file = open(SITE_ROOT+'/'+filename,'wb') 
        file.write(justtext.encode('utf-8')) 
        file.close()

        tokens = nltk.word_tokenize(justtext)
        # textList = Text(nltk.corpus.gutenberg.words('/Developer/insight/insights/' + filename))
        textList = Text(tokens)

        concordanceArray = []
        for thisKey in allkeys :
          # logging.debug('Debug for :'+str(thisKey) + ' in : ' + url)
          if (len(thisKey.split(' ')) > 1):
            # thisBigrams=ngrams(token,2)
            concordanceArray.append(get_concordance_ngrams(textList, thisKey, ' <b>', '</b> ', 200, 50))
          else:
            concordanceArray.append(get_concordance(textList, thisKey, ' <b>', '</b> ', 200, 50))

        htmlResult.concordance = concordanceArray

        if (len(allkeys) >= 1):
          htmlResult.key = allkeys[0]
          htmlResult.collocations = getCollocationsForKeyword(fdColloArray, textList, my_stopwords, allkeys[0], 200, 20, 2, 2)
        else:
          htmlResult.collocations = get_collocations(fdColloArray, textList, my_stopwords)


        textSet = set(textList)
        fdist1 = FreqDist(textList)
        fdArray.append(fdist1)

        longWords = get_long_words(fdist1, 7)
        # htmlResult.long_words = longWords
        htmlResult.top_freq_words = get_top_freq_words(fdist1, 50)
        htmlResult.freq_long_words = get_freq_long_words(fdist1, 7, 2)

        # source,target,value
        # Barry,Elvis,2

        for keywd in longWords[:20] :
          sankeytext = sankeytext + url.lower() + "," + keywd[0].lower() + "," + str(keywd[1]) + "\n"

      htmlResults.results.append(htmlResult)

    htmlResults.totalCollos = getTotalFreqDistForCollos(fdColloArray, my_stopwords, 20)
    htmlResults.totalFreqWords = getTotalFreqDistForWords(fdArray, 50)
    htmlResults.totalFreqLongWords = getTotalFreqDistForLongWords(fdArray, 50, 7, 2)
    file = open(SITE_ROOT+'/static/sankey2.csv','wb')
    file.write('source,target,value\n'.encode('utf-8'))
    file.write(sankeytext.encode('utf-8')) 
    file.close()


    # print('<html><head></head><body style="font-family: monospace;">')
    # print("Results for :")
    # print(allurls[0].lower())
    # print(allkeys[0].lower() + "<br />")
    # print(get_concordance(nltk.ConcordanceIndex(tokens, key = lambda s: s.lower()), allkeys[0].lower()))
    # print(get_collocations(textList))
    # print (get_long_words(textList, 7))
    # print (get_top_freq_words(textList, 100))
    # print (get_freq_long_words(textList, 7, 5))
    # textList.concordance('stratfor')
    # textList.collocations()
    # print('</body></html>')
    # tagged = nltk.pos_tag(tokens)
    # textList.dispersion_plot(["Stratfor", "analysis", "Palestinian", "president"])
    # mpld3.show()

    # for link in soup.find_all('a'):
    #  print(link.get('href'))
    # return HttpResponse(justtext)
  else:
    htmlResults.error = 'You need to submit the form here <a href="/webscrape">Keyphrase Analyzer</a>.'
    # print ('You need to submit the form here <a href="/webscrape">Keyphrase Analyzer</a>.')
  return render(request, 'webscrape/keyword_results.html', {'htmlResults': htmlResults})


def keyword(request):
  return render(request, 'webscrape/keyword.html', {})

def create_project_old(request):
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
            if (len(colHeads) < 2 or colHeads[0].lower() != 'url'):
              errorMsg = "Your first row must start with headers : url,company,..."
            elif (len(colHeads) >= 2):
              if (colHeads[1].lower() != 'company'):
                errorMsg = "Your first row must start with headers : url,company,..."
              else:
                # Now we have good headers - lets populate our list skip first row
                # logging.debug('Debug for 6 ' + str(errorMsg))
                projectdata = []
                projectdata.append(csvdataArray[0] + ',htmlfile,textfile,linksfile,navfile,bodyfile,wordcount')
                tidydata = []
                attrHeads = ''
                if (len(colHeads) > 2):
                  attrHeads = ',' + ','.join(colHeads[2:])
                tidydata.append(str(colHeads[1]) + ',' + str(colHeads[0]) +  attrHeads + ',raw_location,raw_percent,scrub_location,scrub_percent,word')
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
                  for thisDataStr in csvdataArray[1:]:
                    # logging.debug('Debug for 8 : ' + str(thisDataStr))
                    thisData = thisDataStr.split(",")
                    if (len(thisData) != len(colHeads)):
                      errorMsg = errorMsg + str(thisData[0]) + " row did not have the correct number of values.<br />"
                    thisUrl = thisData[0]
                    thisCompany = thisData[1]
                    filename = thisUrl.replace(".", "_").replace("://", "_").replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_").replace("%", "_").replace("+", "_").replace(" ", "_")
                    filename = thisCompany.replace(" ", "_") + "--" + filename
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
                    soup2 = BeautifulSoup(html, 'html.parser', from_encoding="utf-8")
                    
                    urlfiledata[0] = path + filename + "--html.txt"
                    file = open(path + filename + "--html.txt",'wb') 
                    file.write(soup.prettify().encode('utf-8')) 
                    file.close()

                    for script in soup(["script", "style"]):
                      script.decompose()    # rip it out
                    for comment in soup.find_all(string=lambda text:isinstance(text,Comment)):
                      comment.extract()    # rip it out
                    for hidden in soup.select('.hidden-lg,.hidden-md,.modal,.hidden,.hide,.lightbox'):
                      hidden.extract()    # rip it out

                    for script in soup2(["script", "style", "footer", "header", "nav", "button"]):
                      script.decompose()    # rip it out
                    for comment in soup2.find_all(string=lambda text:isinstance(text,Comment)):
                      comment.extract()    # rip it out
                    for hidden in soup2.select('.hidden-lg,.hidden-md,.modal,.hidden,.hide,.lightbox,.btn,.button'):
                      hidden.extract()    # rip it out


                    if (soup.body is not None):                    
                      justtext = soup.body.get_text(separator=u' ')
                      justtext = " \n".join(line.strip() for line in justtext.splitlines() if not line.isspace())
                    
                      urlfiledata[1] = path + filename + "--text.txt"
                      file = open(path + filename + "--text.txt",'wb') 
                      file.write(justtext.encode('utf-8')) 
                      file.close()

                      # appendTidyAndDocTermData(tidydata, fdTextArray, justtext, ignored_words, thisData, thisDataStr, urlfiledata)
                      tokens = nltk.word_tokenize(justtext)
                      scrubbed_tokens = [word for word in tokens if ((word not in ignored_words) and (len(word) > 2))]
                      wordcount = len(tokens)
                      scrubcount = len(scrubbed_tokens)
                      tokentext = Text(scrubbed_tokens)
                      fdTextArray.append([FreqDist(tokentext), thisDataStr])
                      urlfiledata[5] = str(wordcount)
                      tidycnt = 0
                      for i in range(wordcount):
                        tidyrow = [thisData[1],thisData[0]]
                        tidyrow.extend(thisData[2:])
                        thisWord = tokens[i]
                        if ((thisWord.lower() not in ignored_words) and (len(thisWord) > 2)):
                          tidycnt += 1
                          tidyrow.extend([str(i+1),str((i+1)/wordcount),str(tidycnt),str(tidycnt/scrubcount),str(thisWord)])
                          tidydata.append(','.join(tidyrow))

                      # textList = Text(tokens)
                      
                      if (soup2.body is not None):                    
                        justinnerbody = soup2.body.get_text(separator=u' ')
                        justinnerbody = " \n".join(line.strip() for line in justinnerbody.splitlines() if not line.isspace())
                    
                        urlfiledata[4] = path + filename + "--body.txt"
                        file = open(path + filename + "--body.txt",'wb') 
                        file.write(justinnerbody.encode('utf-8')) 
                        file.close()

                    
                      linksArray = []
                      for link in soup.findAll('a'):
                        linksArray.extend(link.get_text(separator=u' ').splitlines())
                      linksText = " \n".join(line.strip() for line in linksArray if (not line.isspace() and line))
                    
                      urlfiledata[2] = path + filename + "--links.txt"
                      file = open(path + filename + "--links.txt",'wb') 
                      file.write(linksText.encode('utf-8')) 
                      file.close()

                      navArray = []
                      for nav in soup.findAll('nav'):
                        navElems = [thisTxt for thisTxt in nav.find_all(text=True) if thisTxt.parent.name != "ul"]
                        navArray.extend(navElems)
                        # navArray.extend(nav.get_text(separator=u' ').splitlines())
                      for ul in soup.findAll('ul'):
                        for link in ul.findAll('a'):
                          navElems = [thisTxt for thisTxt in link.find_all(text=True) if (thisTxt.parent.name != "button" and thisTxt.parent.name != "nav")]
                          navArray.extend(navElems)
                          # navArray.extend(link.get_text(separator=u' ').splitlines())
                        for button in ul.findAll('button'):
                          navElems = [thisTxt for thisTxt in button.find_all(text=True) if (thisTxt.parent.name != "a" and thisTxt.parent.name != "nav")]
                          navArray.extend(navElems)
                          # navArray.extend(button.get_text(separator=u' ').splitlines())
                      navText = " \n".join(line.strip() for line in navArray if not line.isspace())
                    
                      urlfiledata[3] = path + filename + "--nav.txt"
                      file = open(path + filename + "--nav.txt",'wb') 
                      file.write(navText.encode('utf-8')) 
                      file.close()

                      zf = zipfile.ZipFile(path + 'alldata.zip', mode='a')
                      try:
                          zf.write(path + filename + "--html.txt", arcname=filename + "--html.txt", compress_type=compression)
                          zf.write(path + filename + "--text.txt", arcname=filename + "--text.txt", compress_type=compression)
                          zf.write(path + filename + "--body.txt", arcname=filename + "--body.txt", compress_type=compression)
                          zf.write(path + filename + "--links.txt", arcname=filename + "--links.txt", compress_type=compression)
                          zf.write(path + filename + "--nav.txt", arcname=filename + "--nav.txt", compress_type=compression)
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
                    
                    file = open(path + "tidydata.csv",'wb') 
                    file.write("\n".join(tidydata).encode('utf-8')) 
                    file.close()

                    colHeadArray = []
                    colHeadArray.extend(colHeads)
                    docterm_array = getFreqDistArrayForAllWords(fdTextArray, colHeadArray)
                    file = open(path + "docterms_data.csv",'wb') 
                    file.write("\n".join(docterm_array).encode('utf-8')) 
                    file.close()

                    # modes = { zipfile.ZIP_DEFLATED: 'deflated', zipfile.ZIP_STORED:   'stored', }
                    zf = zipfile.ZipFile(path + 'alldata.zip', mode='a')
                    try:
                        zf.write(path + "docterms_data.csv", arcname="docterms_data.csv", compress_type=compression)
                        zf.write(path + "tidydata.csv", arcname="tidydata.csv", compress_type=compression)
                        zf.write(path + "projectdata.csv", arcname="projectdata.csv", compress_type=compression)
                    finally:
                        zf.close()


                # end of if else project exists       
            else:
              errorMsg = "Your first row must start with headers : url,company,..."
    if (errorMsg != ""):
      return render(request, 'webscrape/create_project.html', {'projectname':projectname, 'csvdata': csvdata, 'errorMsg':errorMsg})
    else:
      response = redirect('/webscrape/project/')
      response['Location'] += '?project=' + projectname
      return response
  return render(request, 'webscrape/create_project.html', {})

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
                  
                  
                  teams = ['ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC','LAC','LAR','MIA','MIN','NE','NO','NYG','NYJ','OAK','PHI','PIT','SEA','SF','TB','TEN','WAS']
                  positions = {2:'QB',3:'RB',4:'WR',5:'TE',11:'DST'}
                  seasonTypes = {0:'REG',1:'PRE',2:'POST'}
                  weeksArr = [{'weekStart':0, 'weekStop':4, 'season':0},{'weekStart':5, 'weekStop':9, 'season':0},{'weekStart':10, 'weekStop':14, 'season':0},{'weekStart':15, 'weekStop':16, 'season':0},{'weekStart':1, 'weekStop':4, 'season':1},{'weekStart':0, 'weekStop':3, 'season':2}]
                  weekNumStart = 1 #this will get -1 since zero based.  Put real week here
                  weekNumStart = weekNumStart - 1
                  weekNumStop = 5 #this will get -1 since zero based.  Put real week here
                  weekNumStop = weekNumStop - 1
                  seasonType = 0 #0 reg, 1 pre, 2 post
                  team = 1 #1 to 32 as in array above.
                  position = 4 #2-QB, 3-RB, 4-WR, 5-TE, 11-DST
                  scoringType = 'FantasyPointsDraftKings'
                  nflYear = 2016 #this will get subtracted from current year to get integer for sn value
                  nflYear = int(datetime.now().year)-nflYear
          
                  queryurl = 'https://fantasydata.com/nfl-stats/nfl-fantasy-football-stats.aspx?fs=3&stype=' + str(seasonType) + '&sn=' + str(nflYear) + '&scope=1&w=' + str(weekNumStart) + '&ew=' + str(weekNumStop) + '&s=&t=' + str(team) + '&p=' + str(position) + '&st=' + str(scoringType) + '&d=1&ls=&live=false&pid=false&minsnaps=4'
                  
                  fantasyDataWeek = True
                  fantasyDataHistory = False
                  allGames = False
                  gameinformation = False
                  
                  if (fantasyDataHistory == True):
                    for pos in positions:
                      position = pos

                      headerRow = ''
                      year = 2010
                      while (year > 2006) :
                        year = year - 1
                        nflYear = int(datetime.now().year) - year
                        fantasydataRows = []
                      
                        for weekObj in weeksArr:
                          weekNumStart = weekObj['weekStart']
                          weekNumStop = weekObj['weekStop']
                          seasonType = weekObj['season']
                  
                          for teamIndex in range(len(teams)):
                            team = teamIndex + 1
                            teamTxt = teams[teamIndex]
                            queryurl = 'https://fantasydata.com/nfl-stats/nfl-fantasy-football-stats.aspx?fs=3&stype=' + str(seasonType) + '&sn=' + str(nflYear) + '&scope=1&w=' + str(weekNumStart) + '&ew=' + str(weekNumStop) + '&s=&t=' + str(team) + '&p=' + str(position) + '&st=' + str(scoringType) + '&d=1&ls=&live=false&pid=false&minsnaps=4'
                    
                            txtYear = str(int(datetime.now().year) - nflYear)
                            filename = 'fantasydata_' + teamTxt + '_' + positions[position] + '_'  + txtYear + '_'  + seasonTypes[seasonType] + '_'  + str(weekNumStart + 1) + '_'  + str(weekNumStop + 1) + ''

                            r = requests.get(queryurl, headers={'User-Agent': 'Mozilla/5.0'})
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
                                headerRow = 'Year,Season,' + datatextlines[0].replace('Fantasy Points','FantasyPts').replace(' ',',')
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
                        if os.path.exists(path + "fantasydata_" + positions[pos] + ".csv"):
                          append_write = 'ab' # append if already exists
                        else:
                          append_write = 'wb' # make a new file if not
                          datatext = headerRow + '\n' + datatext
                        file = open(path + "fantasydata_" + positions[pos] + ".csv",append_write) 
                        file.write(datatext.encode('utf-8')) 
                        file.close()
                        
                        
                  elif (fantasyDataWeek == True):
                    # TODO add code for appending new weeks data each week
                    logging.debug('Debug for week data ')
                    for pos in positions:
                      position = pos

                      headerRow = ''
                      year = 2017
                      nflYear = int(datetime.now().year) - year
                      txtYear = str(int(datetime.now().year) - nflYear)
                      fantasydataRows = []
                      
                      weekNumStart = 2
                      weekNumStop = 2
                      seasonType = 0
              
                      for teamIndex in range(len(teams)):
                        team = teamIndex + 1
                        teamTxt = teams[teamIndex]
                        queryurl = 'https://fantasydata.com/nfl-stats/nfl-fantasy-football-stats.aspx?fs=3&stype=' + str(seasonType) + '&sn=' + str(nflYear) + '&scope=1&w=' + str(weekNumStart) + '&ew=' + str(weekNumStop) + '&s=&t=' + str(team) + '&p=' + str(position) + '&st=' + str(scoringType) + '&d=1&ls=&live=false&pid=false&minsnaps=4'
                
                        filename = 'fantasydata_' + teamTxt + '_' + positions[position] + '_'  + txtYear + '_'  + seasonTypes[seasonType] + '_'  + str(weekNumStart + 1) + '_'  + str(weekNumStop + 1) + ''

                        r = requests.get(queryurl, headers={'User-Agent': 'Mozilla/5.0'})
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
                            headerRow = 'Year,Season,' + datatextlines[0].replace('Fantasy Points','FantasyPts').replace('QB Rating','QBRating').replace('QB Hits','QBHits').replace('Fum Rec','FumRec').replace('Def TD','DefTD').replace('Return TD','ReturnTD').replace('Pts Allowed','PtsAllowed').replace(' ',',')
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
                      datatext = "\n".join(fantasydataRows)
                      #urlfiledata[1] = path + "fantasydata_" + filename + ".txt"
                      #file = open(path + "fantasydata_" + filename + ".txt",'wb') 
                      if os.path.exists(path + "fantasydata_" + txtYear + "_" +  str(weekNumStart) + "_" + positions[pos] + ".csv"):
                        append_write = 'ab' # append if already exists
                      else:
                        append_write = 'wb' # make a new file if not
                        datatext = headerRow + '\n' + datatext
                      file = open(path + "fantasydata_" + txtYear + "_" +  str(weekNumStart) + "_" + positions[pos] + ".csv", append_write) 
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
      return render(request, 'webscrape/create_project.html', {'projectname':projectname, 'csvdata': csvdata, 'errorMsg':errorMsg})
    else:
      response = redirect('/webscrape/project/')
      response['Location'] += '?project=' + projectname
      return response
  return render(request, 'webscrape/create_project.html', {})

def projects(request):
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
  return render(request, 'webscrape/projects.html', {'projects' : projectsArray})



class ProjectStats(object):
  def __init__(self):
    self.wordcount = 0
    self.companycount = 0
    self.urlcount = 0
    self.attributes = ''
    self.explorecount = 0

class ProjectData(object):
  def __init__(self):
    self.url = ''
    self.company = ''
    self.attributevalues = []
    self.htmlContent = ['/path.txt', 'content']
    self.textContent = ['/path.txt', 'content']
    self.linkContent = ['/path.txt', 'content']
    self.navContent = ['/path.txt', 'content']
    self.bodyContent = ['/path.txt', 'content']
    self.wordcount = 0

class ExploreData(object):
  def __init__(self):
    self.data = []
    self.colheads = []

class Project(object):
  def __init__(self):
    self.name = ""
    self.stats = ProjectStats()
    self.explorations = ExploreData()
    self.data = []
    self.sourcedata = ''
    self.attributes = []
    self.errorMsg = ''

def mk_int(s):
    s = s.strip()
    return int(s) if s else 0
    
def projectSpecific(request):
  thisProject = Project()
  companyList = {}
  if request.method == "POST":
    thisProject.name = request.POST.get('project', '')
  else:
    thisProject.name = request.GET.get('project', '')
  headerCols = []
  sourcedata = []
  cols = 2
  path = SITE_ROOT + STATIC_PROJECTS + thisProject.name + '/'
  if (os.path.exists(path + "projectdata.csv")):
    project_content = ''
    with open(path + "projectdata.csv", 'r') as content_file:
      project_content = content_file.read()
    if (project_content == ''):
      thisProject.errorMsg = "Error: There is no projectdata for this project."
    else:
      projectDataLines = project_content.splitlines()
      for fileline in projectDataLines:
        if (fileline and (fileline.strip() != '')):
          linevals = [x.strip() for x in fileline.split(',')]
          if (linevals[0].lower() == 'url'):
            headerCols.extend(linevals)
            cols = len(headerCols)
            if (cols >= 7):
              # default cols url,company,...,htmlfile,textfile,linksfile,navfile,bodyfile,wordcount
              thisProject.stats.attributes = ','.join(headerCols[1:-6])
              thisProject.attributes = headerCols[1:-6]
              sourcedata.append(",".join(headerCols[:-6]))
          else:
            thisData = ProjectData()
            thisProject.stats.urlcount += 1
            if (companyList.get(linevals[0], False)):
              companyList[linevals[0]] += 1
            else:
              thisProject.stats.companycount += 1
              companyList[linevals[0]] = 1
            if (headerCols[cols-1].lower() == 'wordcount'):
              thisProject.stats.wordcount += mk_int(linevals[cols-1])
            if (cols >= 7):
              thisData.url = linevals[0]
              thisData.company = ''
              if (cols > 7):
                thisData.attributevalues = linevals[1:-6]
              thisData.htmlContent = linevals[-6].replace(SITE_ROOT,'')
              thisData.textContent = linevals[-5].replace(SITE_ROOT,'')
              thisData.linkContent = linevals[-4].replace(SITE_ROOT,'')
              thisData.navContent = linevals[-3].replace(SITE_ROOT,'')
              thisData.bodyContent = linevals[-2].replace(SITE_ROOT,'')
              thisData.wordcount = mk_int(linevals[-1])
              sourcedata.append(",".join(linevals[:-6]))
            thisProject.data.append(thisData)
      thisProject.sourcedata = "\n".join(sourcedata)
            
  else:
    # No projectdata or project folder found
    thisProject.errorMsg = "The Project Data could not be found - maybe you deleted it."

  exploreHeaderCols = []
  cols = 0
  if (os.path.exists(path + "saved_explorations.csv")):
    explore_content = ''
    with open(path + "saved_explorations.csv", 'r') as content_file:
      explore_content = content_file.read()
    if (not (explore_content == '')):
      exploreDataLines = explore_content.splitlines()
      linecnt = 0
      thisProject.explorations = ExploreData()
      for fileline in exploreDataLines:
        if (fileline and (fileline.strip() != '')):
          linecnt = linecnt + 1
          linevals = [x.strip() for x in fileline.split(',')]
          if (linecnt == 1):
            exploreHeaderCols.extend(linevals)
            cols = len(exploreHeaderCols)
            if (cols > 0): # TODO
              # default cols TODO
              thisProject.explorations.colheads = exploreHeaderCols
          else:
            thisData = ExploreData()
            thisProject.stats.explorecount += 1
            if (cols >= 0):
              thisData = linevals
            thisProject.explorations.data.append(thisData)

  '''
  file = open(path + filename + "--nav.txt",'wb') 
  file.write(navText.encode('utf-8')) 
  file.close()
  '''

    
  return render(request, 'webscrape/project.html', {'project': thisProject})

def saveFile(request):
  data = {"errorMsg":"","success":""}
  if request.method == "POST":
    # logging.debug('Debug for post : ' + str(request.POST)) 
    file_path = request.POST.get('file-path', '')
    file_text = request.POST.get('file-text', '')
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
      data["success"] = "true"
  else:
    data["errorMsg"] = "Error in data submitted - No GET requests"
  
  return JsonResponse(data)

def start_explore(request):
  data = {"errorMsg":"","success":"","page":"/webscrape/explore_collect"}

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
        data["page"] = "/webscrape/explore_assess?projectname=" + project_name + "&explorename=" + explore_name
      else :
        # This is the "collect" action to start exploration
        data["page"] = "/webscrape/explore_collect?projectname=" + project_name + "&explorename=" + explore_name
      
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
      file.write(new_explore_row.encode('utf-8')) 
      file.close()
  
      data["success"] = "true"
    # END IF ELSE form_action is None ( big if elif else field validation statements)
  else: #not POST
    data["errorMsg"] = "Error in data submitted - No GET requests"
  
  return JsonResponse(data)

def TextTokenIndexes(txt, tokens, useStem = False):
  offset = 0
  returnVal = []
  for token in tokens:
    thisToken = token
    saveToken = token
    if (useStem):
      thisToken = token[1]
      saveToken = token[0]
    offset = txt.find(thisToken, offset)
    returnVal.append([saveToken, offset, offset+len(thisToken)])
    offset += len(thisToken)
  return returnVal

def GetGroupKeyword(allkeys, token):
  for x in allkeys:
    if (len(x) > 1):
      for y in x[1:]:
        if (token == y):
          return x[0]
  return token

def LimitTokens(tokens, limit):
  if (limit):
    try:
      word_limit = int(limit)
    except ValueError:
      logging.debug('Debug for exception : cant convert to int : ' + str(limit)) 
      return tokens
    else:
      if (len(tokens) > word_limit and word_limit > 0):
        return tokens[:word_limit] 
      else:
        return tokens

class CollectDataSettings(object):
  def __init__(self):
    self.text_document = "text"
    self.keyword_frequency_max_results = "50"
    self.keyword_min_frequency = "2"
    self.long_word_length = "7"
    self.long_word_min_frequency = "2"
    self.long_word_max_results = "20"
    self.collo_word_width = "2"
    self.collo_freq_min = "2"
    self.collo_max_results = "20"
    self.context_sentence_length = "200"
    self.context_max_results = "50"
    self.lda_topics_count = "10"
    self.lda_word_per_topic = "10"
    self.lda_passes = "100"
    self.use_stem_words = "1"
    self.use_groups = "1"
    self.ranking_type = "freqavg"
    self.group_by = "url"
    self.grouping_calc = "highest"
    self.word_limit = "0"
    self.last_word_value = "0.50"

class CollectData(object):
  def __init__(self):
    self.allurls = []
    self.allkeys = []
    self.projectdata_cols = []
    self.allurl_rows = []
    self.selected_keyphrase = ''
    self.selected_url = ''
    self.projectname = ''
    self.explorename = ''
    self.results = []
    self.concordance = []
    self.collocations = []
    self.long_words = []
    self.top_freq_words = []
    self.freq_long_words = []
    self.stopwords = []
    self.totalCollos = []
    self.totalFreqWords = []
    self.totalFreqLongWords = []
    self.settings = CollectDataSettings()
    self.error = ''


class URLdata(object):
  def __init__(self):
    self.url = ""
    self.filename = ""
    self.key = ""
    self.concordance = []
    self.collocations = []
    self.long_words = []
    self.top_freq_words = []
    self.freq_long_words = []
    self.error = ''

def explore_collect(request):
  htmlResults = CollectData()
  selected_keyphrase = ''
  project_name = ''
  explore_name = ''
  changed_settings = False
  changed_settings_text = "false"
  if request.method == "GET":
    project_name = str(request.GET.get('projectname', ''))
    explore_name = str(request.GET.get('explorename', ''))
    selected_keyphrase = str(request.GET.get('newkeyphrase', ''))
    if (not selected_keyphrase):
      selected_keyphrase = str(request.GET.get('selected_keyphrase', ''))
  elif request.method == "POST":
    project_name = str(request.POST.get('projectname', ''))
    explore_name = str(request.POST.get('explorename', ''))
    selected_keyphrase = str(request.POST.get('newkeyphrase', ''))
    if (not selected_keyphrase):
      selected_keyphrase = str(request.POST.get('selected_keyphrase', ''))
    changed_settings_text = str(request.POST.get('changed_settings', ''))
  if (changed_settings_text == "true"):
    changed_settings = True
    htmlResults.settings.text_document = str(request.POST.get('text_document', 'text'))
    htmlResults.settings.keyword_frequency_max_results = str(request.POST.get('keyword_frequency_max_results', '50'))
    htmlResults.settings.keyword_min_frequency = str(request.POST.get('keyword_min_frequency', '2'))
    htmlResults.settings.long_word_length = str(request.POST.get('long_word_length', '7'))
    htmlResults.settings.long_word_min_frequency = str(request.POST.get('long_word_min_frequency', '2'))
    htmlResults.settings.long_word_max_results = str(request.POST.get('long_word_max_results', '20'))
    htmlResults.settings.collo_word_width = str(request.POST.get('collo_word_width', '2'))
    htmlResults.settings.collo_freq_min = str(request.POST.get('collo_freq_min', '2'))
    htmlResults.settings.collo_max_results = str(request.POST.get('collo_max_results', '20'))
    htmlResults.settings.context_sentence_length = str(request.POST.get('context_sentence_length', '200'))
    htmlResults.settings.context_max_results = str(request.POST.get('context_max_results', '50'))
    htmlResults.settings.lda_topics_count = str(request.POST.get('lda_topics_count', '10'))
    htmlResults.settings.lda_word_per_topic = str(request.POST.get('lda_word_per_topic', '10'))
    htmlResults.settings.lda_passes = str(request.POST.get('lda_passes', '100'))
    htmlResults.settings.ranking_type = str(request.POST.get('ranking_type', 'freqavg'))
    htmlResults.settings.group_by = str(request.POST.get('group_by', 'url'))
    htmlResults.settings.grouping_calc = str(request.POST.get('grouping_calc', 'highest'))
    htmlResults.settings.word_limit = str(request.POST.get('word_limit', '0'))
    htmlResults.settings.last_word_value = str(request.POST.get('last_word_value', '0.50'))
    if (len(request.POST.getlist('use_stem_words')) > 0) :
      htmlResults.settings.use_stem_words = '1'
    else:
      htmlResults.settings.use_stem_words = '0'
    if (len(request.POST.getlist('use_groups')) > 0) :
      htmlResults.settings.use_groups = '1'
    else:
      htmlResults.settings.use_groups = '0'
      
    
  #  ***** TODO : NEED TO READ KEYWORDS FROM FILE, Add to allkeys, run through analysis outputs with or without selected
  #  ***** Next step is to allow ADD / DELETE of keywords to list (save to file)
  #  ***** Grouping??  Maybe wait until assessment page to do keyword groupings.
  
  if (not project_name or not explore_name) :
    htmlResults.error = "There was an error reading the project name or exploration name"
  else :
    # Have valid names
    explore_name_scrubbed = re.sub('[^a-zA-Z0-9\n\.]', '_', explore_name)
    project_path = SITE_ROOT + STATIC_PROJECTS + project_name + "/"
    project_data_path = project_path + "projectdata.csv"
    csv_path = project_path + "saved_explorations.csv"
    explore_root = project_path + "explorations/"
    explore_path = explore_root + explore_name + "/"
    explore_keywords_path = explore_path + explore_name_scrubbed + "_keywords.csv"
    explore_stopwords_path = explore_path + explore_name_scrubbed + "_stopwords.csv"
    explore_settings_path = explore_path + explore_name_scrubbed + "_settings.csv"

    if (os.path.exists(explore_keywords_path) and os.path.exists(project_data_path)):
      allkeys = []
      keyword_content = ''
      project_content = ''
      projectdata_cols = []
      allurl_rows = []
      allurls = []
      allheads = collections.OrderedDict()
      indexOfColHead = 0
      my_stopwords = []
      stopwords_content = ''
      my_settings = []
      settings_content = ''
      
      
      # LOAD MY SETTINGS DATA
      if (os.path.exists(explore_settings_path) and (not changed_settings)):
        with open(explore_settings_path, 'r') as content_file:
          settings_content = content_file.read()
        my_settings.extend([x.strip().split(',') for x in settings_content.lower().splitlines() if x.strip()])

        for setting in my_settings:
          if (len(setting) == 2):
            if (htmlResults.settings.__dict__.get(setting[0], '')):
              htmlResults.settings.__dict__[setting[0]] = str(setting[1])

      if (changed_settings):
        settingsArr = []
        for thisAttr, thisVal in htmlResults.settings.__dict__.items():
          settingsArr.append(str(thisAttr) + "," + str(thisVal))
        file = open(explore_settings_path,'wb') 
        file.write(str("\n".join(settingsArr)).encode('utf-8')) 
        file.close()
      # LOAD MY SETTINGS DATA

      # LOAD MY STOPWORDS DATA
      if (os.path.exists(explore_stopwords_path)):
        with open(explore_stopwords_path, 'r') as content_file:
          stopwords_content = content_file.read()
        my_stopwords.extend([x.strip() for x in stopwords_content.lower().splitlines() if x.strip()])
      # LOAD MY STOPWORDS DATA
      
      # LOAD KEYWORD DATA
      with open(explore_keywords_path, 'r') as content_file:
        keyword_content = content_file.read()
      for groupline in keyword_content.splitlines():
        if groupline.strip():
          theseKeys = [x.strip() for x in groupline.strip().split(',') if x.strip()]
          if (len(theseKeys) > 0):
            allkeys.append(theseKeys)
      # allkeys.extend([x.strip() for x in keyword_content.splitlines() if x.strip()])
      # LOAD KEYWORD DATA END
      
      # LOAD URL DATA
      with open(project_data_path, 'r') as content_file:
        project_content = content_file.read()
      for x in project_content.splitlines():
        if x.strip():
          urlrow_col_values = [y.strip() for y in x.split(",") if y.strip()]
          if (len(urlrow_col_values) > 0):
            if (urlrow_col_values[0].lower() == "url"):
              #colhead row
              projectdata_cols.extend(urlrow_col_values)
            else:
              allurls.append(urlrow_col_values[0])
              allurl_rows.append(urlrow_col_values)
              indexOfColHead = indexlower(projectdata_cols, htmlResults.settings.group_by)
              if (indexOfColHead >= 0) :
                if (not (urlrow_col_values[indexOfColHead] in allheads)):
                  allheads[urlrow_col_values[indexOfColHead]] = urlrow_col_values[indexOfColHead]
                
      # LOAD URL DATA END

      htmlResults.projectname = project_name
      htmlResults.explorename = explore_name
      htmlResults.selected_keyphrase = selected_keyphrase
      htmlResults.selected_url = ''
      htmlResults.allurls = allurls
      htmlResults.group_by_col_heads = allheads
      htmlResults.projectdata_cols = projectdata_cols
      htmlResults.allurl_rows = allurl_rows
      htmlResults.allkeys = allkeys
      #htmlResults.urlstext = request.POST['urls']
      #htmlResults.keystext = request.POST['keyphrases']

      ''' LDA Stuff '''
      tokenizer = RegexpTokenizer(r'\w+')
      # create English stop words list
      en_stop = get_stop_words('en')
      # Create p_stemmer of class PorterStemmer
      p_stemmer = PorterStemmer()
      ldaTokenGroups = []
      ''' LDA Stuff '''

      sankeytext = ""
      fdColloArray = []
      fdArray = []
      tidyDataPerUrl = []
      tinyColloDataPerUrl = []
      colloProbPerUrl = []
      for urlData in allurl_rows :
        if (len(urlData) > 1):
          htmlResult = URLdata()
          htmlResult.url = urlData[0]

          thisUrl = urlData[0]
          thisCompany = urlData[1]
          filename = thisUrl.replace(".", "_").replace("://", "_").replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_").replace("%", "_").replace("+", "_").replace(" ", "_")
          filename = thisCompany.replace(" ", "_") + "--" + filename

          htmlResult.filename = filename
          text_filepath = project_path + filename + '--text.txt'
          body_filepath = project_path + filename + '--body.txt'
          links_filepath = project_path + filename + '--links.txt'
          nav_filepath = project_path + filename + '--nav.txt'
          
          useThisTextPath = project_path + filename + '--' + htmlResults.settings.text_document + '.txt'

          if (os.path.exists(useThisTextPath) and os.path.exists(text_filepath) and os.path.exists(body_filepath) and os.path.exists(links_filepath) and os.path.exists(nav_filepath)):

            # LOAD TEXT DATA
            # TODO - based on filter param - change to links, body, nav instead
            with open(useThisTextPath, 'r') as content_file:
              this_text_content = content_file.read()

            ''' LDA STUFF '''
            loweredText = this_text_content.lower()
            loweredTokens = tokenizer.tokenize(loweredText)
            # remove stop words from tokens
            stopped_tokens = [i for i in loweredTokens if ((not i in en_stop) and (not i in my_stopwords) and (len(i) > 1))]
            stopped_tokens = LimitTokens(stopped_tokens, htmlResults.settings.word_limit) #get the first 100 or X tokens (populated from setting)
            # add tokens to list
            useStem = False
            textTokenMapping = []
            if (htmlResults.settings.use_stem_words == '0'):
              if (htmlResults.settings.use_groups == '0'):
                ldaTokenGroups.append(stopped_tokens)
                tokens = stopped_tokens
                textTokenMapping = TextTokenIndexes(loweredText, tokens, useStem)
              else :
                tokens = [str(GetGroupKeyword(allkeys, i)) for i in stopped_tokens]
                ldaTokenGroups.append(tokens)
                grouped_tokens_map = [[str(GetGroupKeyword(allkeys, i)), i] for i in stopped_tokens]
                textTokenMapping = TextTokenIndexes(loweredText, grouped_tokens_map, True)
             
            else:
              # stem tokens
              useStem = True
              stemmed_tokens = [str(p_stemmer.stem(i)) for i in stopped_tokens]
              stemmed_stopped_tokens = [i for i in stemmed_tokens if ((not i in en_stop) and (not i in my_stopwords))]
              if (htmlResults.settings.use_groups == '0'):
                ldaTokenGroups.append(stemmed_stopped_tokens)
                tokens = stemmed_stopped_tokens
                stemmed_tokens_map = [[str(p_stemmer.stem(i)), i] for i in stopped_tokens]
                stemmed_stopped_tokens_map = [i for i in stemmed_tokens_map if ((not i[0] in en_stop) and (not i[0] in my_stopwords))]
                textTokenMapping = TextTokenIndexes(loweredText, stemmed_stopped_tokens_map, useStem)
              else :
                tokens = [str(GetGroupKeyword(allkeys, i)) for i in stemmed_stopped_tokens]
                ldaTokenGroups.append(tokens)
                stemmed_tokens_map = [[str(GetGroupKeyword(allkeys, p_stemmer.stem(i))), i] for i in stopped_tokens]
                stemmed_stopped_tokens_map = [i for i in stemmed_tokens_map if ((not i[0] in en_stop) and (not i[0] in my_stopwords))]
                textTokenMapping = TextTokenIndexes(loweredText, stemmed_stopped_tokens_map, useStem)

            
            if (htmlResults.settings.word_limit):
              try:
                word_limit = int(htmlResults.settings.word_limit)
              except ValueError:
                logging.debug('Debug for exception : cant convert to int : ' + str(htmlResults.settings.word_limit)) 
              else:
                if (len(tokens) > word_limit and word_limit > 0):
                  tokens = tokens[:word_limit]  
            #logging.debug('Debug for tokens ' + str(tokens)) 
            # Loop through all the words in document and get position and score.
            wordcount = len(tokens)
            bottomPosValue = 0.5
            try:
              last_word_value = float(htmlResults.settings.last_word_value)
            except ValueError:
              logging.debug('Debug for exception : cant convert to float : ' + str(htmlResults.settings.last_word_value)) 
            else:
              bottomPosValue = last_word_value

            bottomPosAdjVal = 0.5 #default bottom value is 50%
            if (bottomPosValue >= 0 and bottomPosValue < 1.0):
              bottomPosAdjVal = 1.0 - bottomPosValue
            tidycnt = 0
            tidydata = []
            thisUrlDict = {}
            for i in range(wordcount):
              thisWord = tokens[i].lower().strip()
              posScore = 1.0 - ((i / wordcount) * bottomPosAdjVal)
              tidyrow = [str(thisWord),i,wordcount,posScore]
              tidydata.append(tidyrow)
              if (thisWord in thisUrlDict) :
                thisUrlDict[thisWord]['indices'].append(i) #add the index number to the first item in array
                thisUrlDict[thisWord]['total_score'] += posScore
              else :
                thisUrlDict[thisWord] = {}
                thisUrlDict[thisWord]['indices'] = [i]
                thisUrlDict[thisWord]['total_score'] = posScore
            #end for loop
            
            tidyDataPerUrl.append([urlData, wordcount, bottomPosAdjVal, thisUrlDict, tidydata])

            ''' LDA STUFF '''

            
            # logging.debug('Debug for TEXT_TOKENS : ' + str(textTokenMapping)) 

            ''' #replaced with LDA above method
            ignored_words = stopwords.words('english')
            justtext = str(this_text_content)
            # tokens = nltk.word_tokenize(justtext)
            tokens = [i for i in nltk.word_tokenize(justtext.lower()) if ((not i.strip() in ignored_words) and (not i.strip() in my_stopwords) and (len(i) > 1))]
            # textList = Text(nltk.corpus.gutenberg.words('/Developer/insight/insights/' + filename))
            '''
            textList = Text(tokens)

            concordanceArray = [] # keeping this even though we only have 1 in array - we used to do it for all selected keywords but now you can only select 1 at a time.
            contextConcordanceArr = get_context(textList, selected_keyphrase, textTokenMapping, this_text_content, int(htmlResults.settings.collo_word_width), '<b>', '</b>', int(htmlResults.settings.context_sentence_length), int(htmlResults.settings.context_max_results))
            concordanceArray.append(contextConcordanceArr)
            ''' Old way of doing the above before we rewrote it
            if (selected_keyphrase and len(selected_keyphrase.split(' ')) > 1):
              # thisBigrams=ngrams(token,2)
              concordanceArray.append(get_concordance_ngrams(textList, selected_keyphrase, ' <b>', '</b> ', int(htmlResults.settings.context_sentence_length), int(htmlResults.settings.context_max_results)))
            else:
              concordanceArray.append(get_concordance(textList, selected_keyphrase, ' <b>', '</b> ', int(htmlResults.settings.context_sentence_length), int(htmlResults.settings.context_max_results)))
            '''

            '''
            # not going to do this for all keywords since we only need selected one
            for thisKey in allkeys :
              # logging.debug('Debug for :'+str(thisKey) + ' in : ' + url)
              if (len(thisKey.split(' ')) > 1):
                # thisBigrams=ngrams(token,2)
                concordanceArray.append(get_concordance_ngrams(textList, thisKey, ' <b>', '</b> ', 200, 50))
              else:
                concordanceArray.append(get_concordance(textList, thisKey, ' <b>', '</b> ', 200, 50))
            '''
            htmlResult.concordance = concordanceArray

            '''
              Change the tokens and Text for below so they are limited to only the sentences returned as part of selected keyphrase.
            '''
            if (selected_keyphrase):
              htmlResult.key = selected_keyphrase
              tokens = contextConcordanceArr[2]
              textList = Text(tokens)
  
            '''  OLD way before we had it filtered above
            if (selected_keyphrase):
              htmlResult.key = selected_keyphrase
              htmlResult.collocations = getCollocationsForKeyword(fdColloArray, textList, my_stopwords, selected_keyphrase, int(htmlResults.settings.context_sentence_length), int(htmlResults.settings.collo_max_results), int(htmlResults.settings.collo_word_width), int(htmlResults.settings.collo_freq_min))
            else:
              htmlResult.collocations = get_collocations(fdColloArray, textList, my_stopwords, int(htmlResults.settings.collo_max_results), int(htmlResults.settings.collo_word_width), int(htmlResults.settings.collo_freq_min))
            '''
            scoreDictArr = [urlData, 0, bottomPosAdjVal, collections.defaultdict(dict)]
            colloProbDict = collections.defaultdict(list)
            htmlResult.collocations = get_collocations(fdColloArray, textList, my_stopwords, scoreDictArr, colloProbDict, int(htmlResults.settings.collo_max_results), int(htmlResults.settings.collo_word_width), int(htmlResults.settings.collo_freq_min))
            tinyColloDataPerUrl.append(scoreDictArr)
            colloProbPerUrl.append(colloProbDict)

            #textSet = set(textList)
            fdist1 = FreqDist(textList)
            fdArray.append(fdist1)

            longWords = get_long_words(fdist1, int(htmlResults.settings.long_word_length))
            # htmlResult.long_words = longWords
            htmlResult.top_freq_words = get_top_freq_words(fdist1, int(htmlResults.settings.keyword_frequency_max_results), int(htmlResults.settings.keyword_min_frequency))
            htmlResult.freq_long_words = get_freq_long_words(fdist1, int(htmlResults.settings.long_word_length), int(htmlResults.settings.long_word_min_frequency))

            # source,target,value
            # Barry,Elvis,2

            for keywd in htmlResult.top_freq_words[:20] :
              sankeytext = sankeytext + thisUrl.lower() + "," + keywd[0].lower() + "," + str(keywd[1]) + "\n"

            htmlResults.results.append(htmlResult)
          else:
            htmlResults.error = htmlResults.error + " A file was missing for " + filename + "."

      ''' ********** LDP ************ '''
      # turn our tokenized documents into a id <-> term dictionary
      ldaDistFreqDict = corpora.Dictionary(ldaTokenGroups)
      # convert tokenized documents into a document-term matrix
      ldaDocTermMatrix = [ldaDistFreqDict.doc2bow(theseTokens) for theseTokens in ldaTokenGroups]
      # generate LDA model
      ldaModel = gensim.models.ldamodel.LdaModel(ldaDocTermMatrix, num_topics=int(htmlResults.settings.lda_topics_count), id2word = ldaDistFreqDict, passes=int(htmlResults.settings.lda_passes))
      htmlResults.ldaModel = ldaModel.show_topics(num_topics=int(htmlResults.settings.lda_topics_count), num_words=int(htmlResults.settings.lda_word_per_topic), log=False, formatted=False)
      ''' ********** LDP ************ '''

      htmlResults.stopwords = my_stopwords;
      # htmlResults.totalCollos = getTotalFreqDistForCollos(fdColloArray, my_stopwords, int(htmlResults.settings.collo_max_results))
      htmlResults.totalCollos = getFreqDistAvgArrayForAllWords(fdColloArray, tinyColloDataPerUrl, int(htmlResults.settings.collo_max_results), htmlResults.settings.ranking_type, my_stopwords=my_stopwords, group_by=htmlResults.settings.group_by, grouping_calc=htmlResults.settings.grouping_calc, indexOfColHead=indexOfColHead, allurl_rows=allurl_rows, allheads=allheads)
      # htmlResults.totalFreqWords = getTotalFreqDistForWords(fdArray, int(htmlResults.settings.keyword_frequency_max_results))
      htmlResults.totalFreqWords = getFreqDistAvgArrayForAllWords(fdArray, tidyDataPerUrl, int(htmlResults.settings.keyword_frequency_max_results), htmlResults.settings.ranking_type, group_by=htmlResults.settings.group_by, grouping_calc=htmlResults.settings.grouping_calc, indexOfColHead=indexOfColHead, allurl_rows=allurl_rows, allheads=allheads)
      # logging.debug('Debug for totalFreqWordsh : ' + str(htmlResults.totalFreqWords)) 
      # htmlResults.totalFreqLongWords = getTotalFreqDistForLongWords(fdArray, int(htmlResults.settings.long_word_max_results), int(htmlResults.settings.long_word_length), int(htmlResults.settings.long_word_min_frequency))
      htmlResults.totalFreqLongWords = getFreqDistAvgArrayForAllWords(fdArray, tidyDataPerUrl, int(htmlResults.settings.long_word_max_results), htmlResults.settings.ranking_type, int(htmlResults.settings.long_word_length), int(htmlResults.settings.long_word_min_frequency), group_by=htmlResults.settings.group_by, grouping_calc=htmlResults.settings.grouping_calc, indexOfColHead=indexOfColHead, allurl_rows=allurl_rows, allheads=allheads)

      
      file = open(SITE_ROOT+'/static/sankey2.csv','wb')
      file.write('source,target,value\n'.encode('utf-8'))
      file.write(sankeytext.encode('utf-8')) 
      file.close()
    else :
      htmlResults.error = "No Keywords File found for this exploration.  Contact admin."


  return render(request, 'webscrape/explore_collect.html', {'htmlResults': htmlResults})

def explore_collect_keyword(request):
  data = {"errorMsg":"","success":"","keywords":[],"stopwords":[]}
  if request.method == "POST":
    project_name = str(request.POST.get('projectname', ''))
    explore_name = str(request.POST.get('explorename', ''))
    keyword = str(request.POST.get('keyword', '')).lower()
    newkeyword = str(request.POST.get('newkeyword', '')).lower() #for edit only
    group = str(request.POST.get('group', '')).lower() #for add to group only

    action_mode = str(request.POST.get('action', '')).lower()
    if (keyword and explore_name and project_name and action_mode):

      # Have valid names
      explore_name_scrubbed = re.sub('[^a-zA-Z0-9\n\.]', '_', explore_name)
      project_path = SITE_ROOT + STATIC_PROJECTS + project_name + "/"
      csv_path = project_path + "saved_explorations.csv"
      explore_root = project_path + "explorations/"
      explore_path = explore_root + explore_name + "/"
      explore_keywords_path = explore_path + explore_name_scrubbed + "_keywords.csv"
      explore_stopwords_path = explore_path + explore_name_scrubbed + "_stopwords.csv"

      if (os.path.exists(explore_keywords_path)):
        allkeys = []
        keyword_content = ''
        my_stopwords = []
        stopwords_content = ''
        
        # LOAD STOP WORDS
        if ((action_mode == "remove") or (action_mode == "unignore")):
          if (os.path.exists(explore_stopwords_path)):
            with open(explore_stopwords_path, 'r') as content_file:
              stopwords_content = content_file.read()
            my_stopwords.extend([x.strip() for x in stopwords_content.lower().splitlines() if (x.strip() and (x.strip() != keyword.strip().lower()))])
          if (action_mode == "remove"): #don't add the keyword back to the array if it is being removed from stopwords (ie: unignore), only add it it is being removed (ie: added to stopwords)
            my_stopwords.append(keyword.lower().strip())
          data["stopwords"] = my_stopwords

          file = open(explore_stopwords_path,'wb') 
          file.write(str("\n".join(my_stopwords)).encode('utf-8')) 
          file.close()
        # LOAD STOP WORDS

      
        # LOAD KEYWORD DATA
        with open(explore_keywords_path, 'r') as content_file:
          keyword_content = content_file.read()
        keyword_content = keyword_content.lower()
        
        keywordGroups = [x.strip() for x in keyword_content.splitlines() if x.strip()]
        
        replacedKeyword = False
        for keywordGroup in keywordGroups:
          groupkeys = []
          groupedKeywords = keywordGroup.split(',')
          if (len(groupedKeywords) > 0):
            if (action_mode == "delete" or action_mode == "remove"):
              if (groupedKeywords[0].strip() != keyword.strip()): #make sure we are not deleting the entire group - if we are then the whole line goes away
                groupkeys.extend([x.strip() for x in groupedKeywords if (x.strip() and (x.strip() != keyword.strip()))])
            elif (action_mode == "unignore"):
              groupkeys.extend([x.strip() for x in groupedKeywords if x.strip()])
            elif (action_mode == "save"):
              for x in groupedKeywords:
                if (x.strip() and ((x.strip() == keyword.strip()) or (x.strip() == newkeyword.strip()))):
                  groupkeys.append(newkeyword.lower().strip())
                  replacedKeyword = True
                elif (x.strip()):
                  groupkeys.append(x.strip())
            else : #add
              # logging.debug('Debug for groupedKeywords : ' + groupedKeywords) 
              if (group and group == groupedKeywords[0].strip()):
                # logging.debug('Debug for group match : ' + groupedKeywords[0].strip()) 
                replacedKeyword = True
                replacedKeywordInGroup = False
                for x in groupedKeywords:
                  if (x.strip() and (x.strip() == keyword.strip())):
                    groupkeys.append(x.strip())
                    replacedKeywordInGroup = True
                  elif (x.strip()):
                    groupkeys.append(x.strip())
                if (not replacedKeywordInGroup):
                  groupkeys.append(keyword.strip())
              else : #not dropping into a group so just read the existing groups into our groupkeys array
                for x in groupedKeywords:
                  if (x.strip() and (x.strip() == keyword.strip())):
                    groupkeys.append(newkeyword.lower().strip())
                    replacedKeyword = True
                  elif (x.strip()):
                    groupkeys.append(x.strip())
                
          
            if (len(groupkeys) > 0):
              allkeys.append(groupkeys)
              
        if ((not replacedKeyword) and (action_mode == "save")):
          allkeys.append([newkeyword.lower().strip()])
        elif ((not replacedKeyword) and (action_mode == "add")):
          allkeys.append([keyword.strip()])

        '''
          if (action_mode == "delete" or action_mode == "remove"):
            allkeys.extend([x.strip() for x in keyword_content.splitlines() if (x.strip() and (x.strip() != keyword.strip()))])
          elif (action_mode == "unignore"):
            allkeys.extend([x.strip() for x in keyword_content.splitlines() if x.strip()])
          elif (action_mode == "save"):
            allkeys.extend([x.strip() for x in keyword_content.splitlines() if (x.strip() and (x.strip() != keyword.strip()) and (x.strip() != newkeyword.strip()))])
            if (newkeyword.lower().strip()):
              allkeys.append(newkeyword.lower().strip())
          else : #add
            allkeys.extend([x.strip() for x in keyword_content.splitlines() if (x.strip() and (x.strip() != keyword.strip()))])
            allkeys.append(keyword.strip())
        '''
        writekeys = [",".join(x) for x in allkeys]
        
        file = open(explore_keywords_path,'wb') 
        file.write(str("\n".join(writekeys)).encode('utf-8')) 
        file.close()
        # LOAD KEYWORD DATA END


        data["keywords"] = allkeys
        data["success"] = "true"
      else:
        data["errorMsg"] = "Could not find saved keywords for exploration."

    else:
      data["errorMsg"] = "Error in data submitted - missing required data"
  
  return JsonResponse(data)


