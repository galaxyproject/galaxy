#!/usr/bin/env python3
import sys
import os
import json

sys.path.insert(0, os.path.abspath('../../../../../tools/amp_schema'))
from contact_sheet import ContactSheet

def main():

	print(sys.argv)
	number_of_columns = 4
	photow = 300
	margin = 10
	padding = 3

	input_file = sys.argv[1]
	context_json = sys.argv[2]
	amp_contact_sheets = sys.argv[3]

	context = json.loads(context_json)
	collection_id = context["collectionId"]
	
	c = ContactSheet(input_file, amp_contact_sheets, number_of_columns, photow, margin, padding)

	video_length_seconds = c.get_length(input_file)
	print("Collection: " + collection_id)
	print("Duration: " + str(video_length_seconds))
	if int(collection_id) in (3, 4):
		if video_length_seconds < 2000:
			print("Creating a frame per 20 seconds")
			c.create_time(20)
		else:
			print("Creating a frame every 1%: " + str(video_length_seconds * .01) + " seconds")
			c.create_time(int(video_length_seconds * .01))
	else:
		if video_length_seconds < 300:
			print("Creating a frame per 10 seconds")
			c.create_time(10)
		elif video_length_seconds < 1800:
			print("Creating a frame per 60 seconds")
			c.create_time(60)
		else:
			print("Creating a frame per 120 seconds")
			c.create_time(120)



if __name__ == "__main__":
	main()
