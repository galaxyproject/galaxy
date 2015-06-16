import requests
from PIL import Image
from StringIO import StringIO
import json
import csv
import sys
import os
import operator

#Command Line Arguments
#thumbs.py input.tsv html_file.files_path galaxy_authentication_4_json html_file.dataset.dataset.id
#	     argv[1]        argv[2]              argv[3]                      argv[4]

f = open(sys.argv[1],'r')
try:
  fd = open(sys.argv[3],'r')
except IOError:
  print_error_and_exit('Could not open input file '+sys.argv[1])
try:
  auth_json = json.load(fd)
except IOError:
  print_error_and_exit('Could not open auth file '+sys.argv[3])
filesPath = sys.argv[2]
jsonPath = files_path+'data/jsonFile.json'
jsonFile = open(jsonPath,'w')
credentials = {"galaxy": auth_json}
json.dump(credentials,jsonFile)

datasetId = sys.argv[4]

#sort tsv by omero server to reduce session connections
parsedTSV = csv.reader(f, delimiter='\t')
header = []
imageBody = []
firstLine = True
login_payload = {'username':'client','password':'bigdata','server':'1'}
#Sort tsv by omero_host to reduce the number of session connections
sortedList = sorted(parsedTSV, key=operator.itemgetter(1), reverse=True)
s = requests.Session()
#Has a session been established with the OMERO server?
previousSession = ''
for row in sortedList:
  if firstLine:
    header = row
    firstLine = False
    continue
  entry =  dict(zip(header,row))   
  if entry['omeroHost'] != previousSession:
    try:
      resp = s.get(entry['omeroHost']+"webclient/login/",params=login_payload)
    except requests.exceptions.ConnectionError:
      print ('Connection Error with OMERO Server: '+entry['omeroHost'])
      sys.exit(1) 
    #Chunked Encoding Error typically encountered on first connection attempt with OMERO Server.
    except requests.exceptions.ChunkedEncodingError:
      print 'Chunked Encoding Error: '+entry['omeroHost'] 
    while  resp.status_code != 200:
      time.sleep(1.0)
      try:
        resp = s.get(entry['omeroHost']+"webclient/login/",params=login_payload)
      except requests.exceptions.ChunkedEncodingError:
        print 'Chunked Encoding Error: '+entry['omeroHost']
    previousSession = entry['omeroHost']
  rawImage = s.get(entry['omeroHost']+"webgateway/render_thumbnail/{0}/".format(entry['omeroImageId']))  
  print entry['omeroHost']+"webgateway/render_thumbnail/{0}/".format(entry['omeroImageId'])
  #()print rawImage.content
  thumbnail = Image.open(StringIO(rawImage.content))
  #thumbnailUrl should be "{datasetId}/data/images/cccDid.jpg"
  entry['thumbnailUrl'] = datasetId+'/data/images/'+entry['cccDid']+'.jpg'
  #save to $html_file.files_path/data/images/cccDid.jpg
  thumbnail.save(filesPath+'data/images/'+entry['cccDid']+'.jpg')
  imageBody.append(entry)

imageJSON = {"images": imageBody}
json.dump(imageJSON,jsonFile)
jsonFile.close()
f.close()
fd.close()
