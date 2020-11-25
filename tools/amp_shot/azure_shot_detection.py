#!/usr/bin/env python3
import sys
import logging
import time
import json
import tempfile
import os
from datetime import timedelta
from datetime import datetime
import math

from requests_toolbelt import MultipartEncoder

sys.path.insert(0, os.path.abspath('../../../../../tools/amp_schema'))
from shot_detection import ShotDetection, ShotDetectionMedia, ShotDetectionShot

def main():
	(input_video, azure_video_index, amp_shots) = sys.argv[1:4]

	# You must initialize logging, otherwise you'll not see debug output.
	logging.basicConfig()

	# Get Azure video index json
	with open(azure_video_index, 'r') as azure_index_file:
		azure_index_json = json.load(azure_index_file)

	# Create AMP Shot object
	amp_shots_obj = create_amp_shots(input_video, azure_index_json)
	
	# write AMP Video OCR JSON file
	write_json_file(amp_shots_obj, amp_shots)

# Parse the results
def create_amp_shots(input_video, azure_index_json):
	amp_shots = ShotDetection()

	# Create the media object
	duration = azure_index_json["summarizedInsights"]["duration"]["seconds"]
	amp_media  = ShotDetectionMedia(input_video, duration)
	amp_shots.media = amp_media

	amp_shots.shots = []
	
	# in our case, there should be only one video in videos, but let's loop through the list just in case
	for video in azure_index_json['videos']:
		# Currently we don't use Azure scenes, only shots
# 	 	# Add shots from Azure scenes 
# 	 	addShots(amp_shots.shots, video['insights']['scenes'], 'scene')
		
		# Add shots from Azure shots 
		addShots(amp_shots.shots, video['insights']['shots'], 'shot')	

	return amp_shots

# Add the given Azure shot list to the given AMP shot list using the given type.
def addShots(amp_shot_list, azure_shot_list, type):
	for shot in azure_shot_list:
		for instance in shot['instances']:
			start = convertTimestampToSeconds(instance['start'])
			end = convertTimestampToSeconds(instance['end'])
			shot = ShotDetectionShot(type, start, end)
			amp_shot_list.append(shot)
	# Note: 
	# We can either use each instance of an Azure shot as an AMP shot; or
	# we can combine all instances of an Azure shot (i.e. take start of the first instance and end of the last instance) into one AMP shot.  
	# Here we use the former option. In reality the instances most likely only contain one instance.

# Convert the timestamp to total seconds
def convertTimestampToSeconds(timestamp):
	try:
		x = datetime.strptime(timestamp, '%H:%M:%S.%f')
	except ValueError:
		x = datetime.strptime(timestamp, '%H:%M:%S')
	hourSec = x.hour * 60.0 * 60.0
	minSec = x.minute * 60.0
	total_seconds = hourSec + minSec + x.second + x.microsecond/600000
	return total_seconds

# Serialize obj and write it to output file
def write_json_file(obj, output_file):
	# Serialize the object
	with open(output_file, 'w') as outfile:
		json.dump(obj, outfile, default=lambda x: x.__dict__)

if __name__ == "__main__":
	main()
