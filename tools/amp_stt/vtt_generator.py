#!/usr/bin/env python3
import json
import sys
import os
from _ast import Or


def writeHeader():
	#this fuction writes the header of the vtt file
	return "WEBVTT"+"\n"

#This function reads the json input and parses it to write a vtt output
def generateVtt(seg_file, stt_file, output_file):
	out_file = open(output_file, "w")
	out_file.write(writeHeader())
	out_file.write(writeEmptyLine())

	segments = []
	words = []
	if os.path.exists(seg_file):
		json_seg = open(seg_file)
		dict_seg = json.loads(json_seg.read())
		segments = dict_seg['segments']
	if os.path.exists(stt_file):
		json_stt = open(stt_file)
		dict_stt = json.loads(json_stt.read())
		words = dict_stt['results']['words']
	
	# initialize current line status
	nword = 0	# number of pronunciation words in current line so far 
	curseg = 0	# index of current segment (to get current speaker)
	start = end = 0	# start/end timestamp for current line: -1 indicates uninitialized
	line = ''	# text of current line	
				
	# process all words which are in time order
	# note that if punctuation words before the first pronunciation word will be ignored
	for i, word in enumerate(words):
		newline = False	# true if current word is the start of a new line
		# the current word should be the start of a new line if it's pronunciation and  
		if word['type'] == 'pronunciation':
			# no previous line, this is the very first word
			if (len(line) == 0):
				newline = True
			# there are already 10 words in current line
			elif nword == 10:
				newline = True
			# or there are at least 6 words plus punctuation in current line	
			elif nword >= 6 and words[i-1]['type'] == 'punctuation':
				newline = True
			# or it's from a new speaker
			else:
				iseg = findWordSegmentIndex(word, segments, curseg)
				if iseg > curseg:
					newline = True
					curseg = iseg
		
		# starting a new line	
		if newline:
			# write the current line before starting a new line
			if (len(line) > 0):
				out_file.write(writeTime(start, end))
 				out_file.write(writeLine(getSpeaker(segments, curseg), line))
 				out_file.write(writeEmptyLine())
			# reset status of the new line
			nword = 0 
			# new line always starts with a pronunciation, use its start time as line start time
			start = word['start']	 
			line = ''	
		
		# update current line with current word
		if word['type'] == 'pronunciation':
			nword += 1
			# record potential line end time from current pronunciation (can't end time of last word on a line since it may be punctuation)
			end = word['end']
		line += ' ' + word['text']
		
# 		start = end = -1	# start/end timestamp for current line: -1 indicates uninitialized
# 		nword = 0;	# number of pronunciation words in current line so far 
# 		line = ''	# text of current line
# 		curr_speaker = ''	# speaker of current line
# 		status = -1	# status of current line: start: -1, continue: 0, end: 1
				
# 		for i, word in enumerate(words):
# 			if word['type'] == 'pronunciation':
# 				if getSpeaker(word['start'], word['end'], segments) != curr_speaker and curr_speaker != '':
# 					new_line = 0
# 			if new_line == 0:                  # 0 signifies ready for wrting in a new line. 
# 				if word['type'] == 'punctuation':
# 					line += word['text']
# 					continue
# 				else:
# 					new_line = 1
# 			if new_line == 1:                  #new_line= 1 signifies start wrting a new line
# 				out_file.write(writeTime(start, end))
# 				out_file.write(writeLine(curr_speaker,line))
# 				out_file.write(writeEmptyLine())
# 				line = ''
# 				new_line = -1		
# 			
# 			if len(line) == 0:
# 				start = word['start'] 
# 			line += ' '+word['text']
# 			if 'end' in word:
# 				end = word['end']
# 				curr_speaker = getSpeaker(word['start'], word['end'], segments)
# 			if word['type'] == 'punctuation' or len(line) == max_words:
# 				new_line = 0

	#writing the last line to file if left
	if len(line) > 0:
		out_file.write(writeTime(start, end))
		out_file.write(writeLine(getSpeaker(segments, curseg), line))
		out_file.write(writeEmptyLine())
	out_file.close()

		
# Find the index of the segment among the given segments to which the given word belongs to (i.e.
# its start/end time are within the segment's start/end time), starting at the given (current) segment index (always >= 0).
def findWordSegmentIndex(word, segments, istart):
	# non pronunciation word belongs to the current segment
	if word['type'] != 'pronunciation':
		return istart		
	# if we are already beyond segments index bound, stay with current segment
	if istart >= len(segments):
		return istart
	# if word end time is within current segment end time, stay with segment 
	if word['end'] <= segments[istart]['end']:
		return istart
	
	# otherwise, scan the following segments for the next containing one, based on following assumptions: 
	# need to scan as some segments may not contain any word (otherwise we can just return the next segment); 
	# scan segments sequentially as segments are in time order;
	# use only word's end time to check segment as words don't cross segment boundary;
	# ignore segment start time (thus making segments continuous) so that each word falls into some segment based on end time. 
	iseg = istart + 1
	while iseg < len(segments) and word['end'] > segments[iseg]['end']:
		iseg += 1		
	return iseg
	
# Gets the speaker of the given segments[iseg]. 	
def getSpeaker(segments, iseg):
	if iseg < 0 or iseg >= len(segments):
		return "Unknown Speaker"
	if 'speakerLabel' in segments[iseg]:
		return segments[iseg]['speakerLabel']
	else:
		return "Unlabeled Speaker"
		
# 	# Gets the speaker for the given pronunciation word belonging to the given segments[iseg]. 	
# 	def getSpeaker(word, segments, iseg):
# 		if wordWithinSegment(word, segments, iseg):
# 			if 'speakerLabel' in segments[iseg]:
# 				return segments[iseg]['speakerLabel']
# 			else:
# 				return "Unlabeled Speaker"
# 		return "Unidentified Speaker"
# 		
# 	# Return true if the given pronunciation word's start/end time is within the given segments[iseg] start/end time, false otherwise.
# 	def wordWithinSegment(word, segments, iseg):
# 		if iseg < 0 or iseg >= len(segments):
# 			return False		
# 		if word['type'] == 'pronunciation' and word['start'] >= segments[iseg]['start'] and word['end'] <= segments[iseg]['end']:
# 			return True
# 		return False 
		
# 	# Return true if the given word is pronunciation and its end time is beyond the given segments[iseg] end time, false otherwise.
# 	# If the segment index iseg is out of the segments index range, return false.
# 	def wordBeyondSegment(word, segments, iseg):
# 		if iseg < 0 or iseg >= len(segments):
# 			return False		
# 		if word['type'] == 'pronunciation' and word['end'] > segments[iseg]['end']:
# 			return True
# 		return False 
# 		
# 	#This function gets the current speaker from the segmenattion file
# 	def getSpeaker(start, end, segments):
# 		speaker_found = 'No Speaker'
# 		for segment in segments:
# 			if segment['start'] <= start and segment['end'] >= end:
# 				if 'speakerLabel' in segment:	# speakerLabel is optional field in segments
# 					speaker_found = segment['speakerLabel']
# 				break
# 		return speaker_found
	
def writeLine(speaker, text):
	#This function writes a new line to the vtt output
	return "<v "+speaker+">"+text+"\n"

def writeEmptyLine():
	# This function writes an empty line to the vtt output
	return "\n"

def writeTime(start_time, end_time):
	#This function writes a time entry to the vtt output
	return str(start_time)+" --> "+str(end_time)+"\n"

def getOutput():
	#This function writes the content to the vtt output
	return output
	
def main():
	(seg_file, stt_file, output_name) =  sys.argv[1:4] 
	generateVtt(seg_file, stt_file, output_name)


if __name__ == "__main__":
	main()
		
