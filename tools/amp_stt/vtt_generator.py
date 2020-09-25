#!/usr/bin/env python3
import json
import sys
import os.path
from os import path

class JsonToVtt:
	output = ''
	max_words = 6
	def writeHeader(self):
		#this fuction writes the header of the vtt file
		return "WEBVTT"+"\n"
	
	def generateVtt(self, seg_file, stt_file, output_file):
		#This function reads the json input and parses it to write a vtt output
		out_file = open(output_file, "w")
		out_file.write(self.writeHeader())
		out_file.write(self.writeEmptyLine())

		segment = {}
		words = {}
		if path.exists(seg_file):
			json_seg = open(seg_file)
			dict_seg = json.loads(json_seg.read())
			segment = dict_seg['segments']
		if path.exists(stt_file):
			json_stt = open(stt_file)
			dict_stt = json.loads(json_stt.read())
			words = dict_stt['result']['words']
		
		end = start = 0
		line = ''
		curr_speaker = ''
		new_line = -1
		for i, word in enumerate(words):
			if word['type'] != 'punctuation':
				if self.getSpeaker(word['start'], word['end'], segment) != curr_speaker and curr_speaker != '':
					new_line = 0
			if new_line == 0:                  #new_line= '0' signifies ready for wrting in a new line. 
				if word['type'] == 'punctuation':
					line += word['text']
					continue
				else:
					new_line = 1
			if new_line == 1:                  #new_line= 1 signifies start wrting a new line
				out_file.write(self.writeTime(start, end))
				out_file.write(self.writeLine(curr_speaker,line))
				out_file.write(self.writeEmptyLine())
				line = ''
				new_line = -1		
			
			if len(line) == 0:
				start = word['start'] 
			line += ' '+word['text']
			if 'end' in word:
				end = word['end']
				curr_speaker = self.getSpeaker(word['start'], word['end'], segment)
			if word['type'] == 'punctuation' or len(line) == self.max_words:
				new_line = 0

		#writing the last sentence to file if left
		if len(line) > 0:
			out_file.write(self.writeTime(start, end))
			out_file.write(self.writeLine(curr_speaker,line))
			out_file.write(self.writeEmptyLine())
		out_file.close()
		return self.output

	#This function gets the current speaker from the segmenattion file
	def getSpeaker(self, start, end, speakers):
		speaker_found = 'No Speaker'
		for ele in speakers:
			if ele['start'] <= start and ele['end'] >= end:
				speaker_found = ele['speakerLabel']
				break
		return speaker_found
	
	def writeLine(self, speaker, text):
		#This function writes a new line to the vtt output
		return "<v "+speaker+">"+text+"\n"

	def writeEmptyLine(self):
		# This function writes an empty line to the vtt output
		return "\n"

	def writeTime(self, start_time, end_time):
		#This function writes a time entry to the vtt output
		return str(start_time)+" --> "+str(end_time)+"\n"

	def getOutput():
		#This function writes the content to the vtt output
		return self.output
	
def main():
	(seg_file, stt_file, output_name) =  sys.argv[1:4] #('Galaxy10-[AWS_Transcribe_on_data_3].json', 'Galaxy9-[AWS_Transcribe_on_data_3] (1).json', 'ouput.vtt' )#
	invoke = JsonToVtt()
	output = invoke.generateVtt(seg_file, stt_file, output_name)


if __name__ == "__main__":
	main()
		
