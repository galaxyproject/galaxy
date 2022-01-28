#!/usr/bin/env python3

# Python imports
import pytesseract
import os
import json
import sys
import time
import subprocess
import shlex
import pprint
import tempfile
# Python imports
try:
    from PIL import Image
except ImportError:
    import Image

from datetime import datetime
from pytesseract import Output

from mgm_logger import MgmLogger
import mgm_utils


def main():
	with tempfile.TemporaryDirectory(dir = "/tmp") as tmpdir:
		(input_file, output_name) = sys.argv[1:3]
		dateTimeObj = datetime.now()

		#ffmpeg extracts the frames from the video input
		command = "ffmpeg -i "+input_file+ " -an -vf fps=2 '"+tmpdir+"/frame_%05d_"+str(dateTimeObj)+".jpg'"
		subprocess.call(command, shell=True)
		
		#Tesseract runs the ocr on frames extracted
		script_start = time.time()
		#output_name =  input_file[:-4]+ "-ocr_"+str(dateTimeObj)+".json"
		
		# Get some stats on the video
		(dim, frameRate, numFrames) = findVideoMetada(input_file)

		output = {"media": {"filename": input_file,
					"frameRate": frameRate,
					"numFrames": numFrames,
					"resolution": {
							"width": int(dim[0]),
							"height": int(dim[1])
						}
			
				},
			"frames": []
			}
		
		#for every saved frame
		start_time = 0
		for num, img in enumerate(sorted(os.listdir(tmpdir))): 
			start_time =+ (.5*num) 
			frameList = {"start": str(start_time),
				"objects": []
				}
		
			#Run OCR
			result = pytesseract.image_to_data(Image.open(tmpdir+"/"+img), output_type=Output.DICT)
			
			#For every result, make a box & add it to the list of boxes for this framecalled frameList
			for i in range(len(result["text"])): 
				if result["text"][i].strip(): #if the text isn't empty/whitespace
					box = {
						"text": result["text"][i],
						"score": {
							"type":"confidence",
							"value": result["conf"][i]
								},
							# relative coords
							"vertices": {
							"xmin": result["left"][i]/output["media"]["resolution"]["width"],
							"ymin": result["top"][i]/output["media"]["resolution"]["height"],
							"xmax": (result["left"][i] + result["width"][i])/output["media"]["resolution"]["width"],
							"ymax": (result["top"][i] + result["height"][i])/output["media"]["resolution"]["height"]
							}
						}
					frameList["objects"].append(box)
		
				#save frame if it had text
			if len(frameList["objects"]) > 0:
				output["frames"].append(frameList)
		
		# save the output json file
		mgm_utils.write_json_file(output, output_name)
	

# UTIL FUNCTIONS
def findVideoMetada(pathToInputVideo):
	cmd = "ffprobe -v quiet -print_format json -show_streams"
	args = shlex.split(cmd)
	args.append(pathToInputVideo)
	
	# run the ffprobe process, decode stdout into utf-8 & convert to JSON
	ffprobeOutput = subprocess.check_output(args).decode('utf-8')
	ffprobeOutput = json.loads(ffprobeOutput)

	# prints all the metadata available:  ---->for debugging
	#pp = pprint.PrettyPrinter(indent=2)
	#pp.pprint(ffprobeOutput)

	#find height and width
	height = ffprobeOutput['streams'][0]['height']
	width = ffprobeOutput['streams'][0]['width']
	frame_rate = ffprobeOutput['streams'][0]['avg_frame_rate']
	numFrames = ffprobeOutput['streams'][0]['nb_frames']

	return ([height, width], frame_rate, numFrames)


if __name__ == "__main__":
	main()
