#!/usr/bin/env python3
import ffmpeg
import sys
import requests
import logging
import json
from contact_sheet import ContactSheet

def main():
	#label = "AMP Contact Sheets " + datetime.today().strftime("%b %d %Y %H:%M:%S")
	print(sys.argv)
	input_file = sys.argv[1]
	type = sys.argv[2]
	frame_seconds = 0
	if sys.argv[3] != '':
		frame_seconds = int(sys.argv[3])
	frame_quantity = 0
	if sys.argv[4] != '':
		frame_quantity = int(sys.argv[4])
	amp_shots = sys.argv[5]
	amp_facial_recognition = sys.argv[6]
	amp_contact_sheets = sys.argv[7]

	number_of_columns = 4
	photow = 300
	margin = 10
	padding = 3

	if sys.argv[8] != '':
		number_of_columns = int(sys.argv[8])
	if sys.argv[9] != '':
		photow = int(sys.argv[9])
	if sys.argv[10] != '':
		margin = int(sys.argv[10])
	if sys.argv[11] != '':
		padding = int(sys.argv[11])

	# Print for debugging purposes
	print("Input File: " + input_file)
	print("type: " + type)
	print("frame_seconds: " + str(frame_seconds))
	print("frame_quantity: " + str(frame_quantity))
	print("amp_shots: " + amp_shots)
	print("amp_facial_recognition: " + amp_facial_recognition)
	print("Output File: " + amp_contact_sheets)
	print("Number of Columns: " + str(number_of_columns))
	print("Photo Width: " + str(photow))
	print("Margin: " + str(margin))
	print("Padding: " + str(padding))

	# Initialize the contact sheet
	c = ContactSheet(input_file, amp_contact_sheets, number_of_columns, photow, margin, padding)

	# Based on input, create the contact sheet
	if type == 'time':
		c.create_time(frame_seconds)
	elif type == 'quantity':
		c.create_quantity(frame_quantity)
	elif type == 'shot':
		shots = read_json_file(amp_shots)
		c.create_shots(shots)
	elif type == 'facial':
		fr = read_json_file(amp_facial_recognition)
		c.create_facial(fr)

def read_json_file(input):
	with open(input) as f:
		data = json.load(f)
		return data

if __name__ == "__main__":
	main()
