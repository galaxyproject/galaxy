#!/usr/bin/env python3

import json
import os
import os.path
import shutil
import subprocess
import sys
import tempfile
import uuid

import mgm_utils
import gi
from lib2to3.tests.data.infinite_recursion import gid_t


def main():
	(speech_audio, amp_transcript_unaligned, gentle_transcript, amp_transcript_aligned) = sys.argv[1:5]
	exception = False
	try:
		# prefix random id to original filenames to ensure uniqueness for the tmp Gentle singularity input files 
		id = str(uuid.uuid4())
		tmp_speech_audio_name = "gentle-" + id + "-" + os.path.basename(speech_audio)
		tmp_amp_transcript_unaligned_name = "gentle-" + id + "-" + os.path.basename(amp_transcript_unaligned)
		tmp_gentle_transcript_name = "gentle-" + id + "-" + os.path.basename(gentle_transcript)

		# define directory accessible to singularity container
		tmpdir = '/tmp'

		# define tmp filepaths
		tmp_speech_audio = f"{tmpdir}/{tmp_speech_audio_name}"
		tmp_amp_transcript_unaligned = f"{tmpdir}/{tmp_amp_transcript_unaligned_name}"
		tmp_gentle_transcript = f"{tmpdir}/{tmp_gentle_transcript_name}"

		# Load the audio and transcript inputs into tmp dir and run gentle
		with open(amp_transcript_unaligned, "r") as amp_transcript_unaligned_file:
			amp_transcript_unaligned_json = json.load(amp_transcript_unaligned_file)

			# Write the transcript to an input file into gentle
			with open(tmp_amp_transcript_unaligned, "w") as tmp_amp_transcript_unaligned_file:
				tmp_amp_transcript_unaligned_file.write(amp_transcript_unaligned_json["results"]["transcript"])

			# Copy the audio file to a location accessible to the singularity container
			shutil.copy(speech_audio, tmp_speech_audio)

			# Run gentle
			print(f"Running Gentle... tmp_speech_audio: {tmp_speech_audio}, tmp_amp_transcript_unaligned: {tmp_amp_transcript_unaligned}, tmp_gentle_transcript: {tmp_gentle_transcript}")
			r = subprocess.run(["singularity", "run", "/srv/amp/gentle-singularity/gentle-singularity.sif", tmp_speech_audio, tmp_amp_transcript_unaligned, "-o", tmp_gentle_transcript], stdout=subprocess.PIPE)
			print(f"Finished running Gentle with return Code: {r.returncode}")

			# if Gentle completed in success, continue with transcript conversion
			if r.returncode == 0:
				# Copy the tmp Gentle output file to gentle_transcript
				shutil.copy(tmp_gentle_transcript, gentle_transcript)
	
				print("Creating AMP transcript aligned...")
				gentle_transcript_to_amp_transcript(gentle_transcript, amp_transcript_unaligned_json, amp_transcript_aligned)

			exit(r.returncode)
	except Exception as e:
		print("Exception while running Gentle:")
		traceback.print_exc()
		exit(1)


# Convert Gentle output transcript JSON file to AMP Transcript JSON file.
def gentle_transcript_to_amp_transcript(gentle_transcript, amp_transcript_unaligned_json, amp_transcript_aligned):
	with open(gentle_transcript, "r") as gentle_transcript_file:		
		# read gentle_transcript and initialize pointers
		gentle_transcript_json = json.load(gentle_transcript_file)
		transcript = gentle_transcript_json["transcript"]
		gwords = gentle_transcript_json["words"]
		uwords = amp_transcript_unaligned_json["results"]["words"]
		duration = amp_transcript_unaligned_json["media"]["duration"]
		words = list()
		preoffset = -1	# end offset of previous word

		# initialize amp_transcript_aligned_json
		amp_transcript_aligned_json = dict()
		amp_transcript_aligned_json["media"] = amp_transcript_unaligned_json["media"]
		amp_transcript_aligned_json["results"] = dict()
		amp_transcript_aligned_json["results"]["transcript"] = transcript
		amp_transcript_aligned_json["results"]["words"] = words	
		
		# populate amp_transcript_aligned_json words list, based on gentle_transcript words list
		for gi in range(0, len(gwords)):
			# find the next successful alignment and the interval between previous successful alignment
			[next, interval] = find_next_success(gwords, gi, duration)
									
			# if current word is the next success, use the aligned timestamp, and default confidence 1.0
			if gi == next:
				start = gwords[gi]["start"]
				end = gwords[gi]["end"]
				confidence = 1.0
			# otherwise current word is unmatched, use same start/end timestamp with default confidence 0.0
			# if it's the first word in the list, set timestamp to 0
			elif gi == 0:	# 0 == gi < next
				start = end = 0.0
				confidence = 0.0
			# otherwise, accumulate the timestamp with the interval between previous and next alignment
			else:	# 0 < gi < next
				start = end = gwords[gi-1]["start"] + interval					
				confidence = 0.0
			
			# insert punctuations between the current and previous word if any, based on their offsets;
			# this is needed as Gentle doen't include punctuations in the words list, but the transcript does
			[preoffset, curoffset] = insert_punctuations(words, gwords, gi, preoffset, transcript)
				
			# append the current Gentle word to the AMP words list
			words.append({
				"type": "pronunciation", 
				"start": start, 
				"end": end, 
				"text": gwords[gi]["word"],
				"offset": curoffset,
				"score": {
					"type": "confidence", 
					"scoreValue": confidence,
				},
			})							
			
		# append punctuations after the last word if any text left
		[preoffset, curoffset] = insert_punctuations(words, gwords, gi, preoffset, transcript)
		print(f"Successfully added {len(words)} words into AMP aligned transcript.")
		 	
		# update words confidence in amp_transcript_aligned_json, based on amp_transcript_unaligned_json words
		updated = update_confidence(words, uwords)
		print(f"Successfully updated confidence for {updated} words in AMP aligned transcript.")
		
		# write final amp_transcript_aligned_json to file
		mgm_utils.write_json_file(amp_transcript_aligned_json, amp_transcript_aligned)
		
		
# Find the next success match in the given words list, starting at the given current index:
# If such a word is found, return its index, and average time interval between the previous and next match;
# If the next match is the current word, interval will be None;
# If the current index is 0, use 0 as the previous match end timestamp;
# if no next match is found, use the given duration as the next match start timestamp. 
def find_next_success(words, current, duration):	
	if current == 0:
		end = 0.0
	else:
		end = words[current-1]["end"]						
	for next in range(current, len(["words"])):
		if words[next]["case"] == "success":
			if next == current:
				interval = None
			else:
				interval = (words[next]["start"] - end) / (next - current)
			break;		
	if next == len(words):
		interval = (duration - end) / (next - current)				
	return [next, interval]
		
		
# Insert punctuations to the given AMP words list, if there is any in the given transcript between the word 
# at the given current index and the given previous word offset in the given Gentle words list.
def insert_punctuations(words, gwords, gi, preoffset, transcript):	
	# if current word is not the last one, offset boundary is the start of the current word
	if gi < len(gwords):		
		curoffset = len(transcript)
	# otherwise offset boundary is the end of transcript
	else:
		curoffset = gwords[gi]["startOffset"]
			
	# scan transcript between end of previous word and start of current word		
	for i in range(preoffset+1, curoffset):
		text = transcript[i]
		# only insert non-space chars, which should be punctuations
		if text != ' ':
			words.append({
				"type": "punctuation",
				"text": text,
				"offset": i,
				"score": {
					"type": "confidence",
					"scoreValue": 0.0,
				},
			})

	# if current word is not the last one, offset boundary is the start of the current word
	if gi < len(gwords):		
		preoffset = gwords[gi]["endOffset"]
	# otherwise offset boundary is the end of transcript
	else:
		preoffset = len(transcript)

	return [preoffset, curoffset]


# Update word confidence in the given aligned words list, based on the given unaligned words list.
def update_confidence(words, uwords):
	len = len(words)
	ulen = len(uwords)
	if len != ulen:
		print (f"Warning: The algined words list length = {len} does not equal the unaligned words list length {ulen}.")	
	
	ui = -1
	i = si = 0
	swords = list()
	updated = 0
	
	for word in words:
		# AMP transcript words list is supposed to contain one word in each element, 
		# but it's currently not the case for HMGM corrected transcript; thus we need to split multi-words text
		# if we reach the end of the last split multi-words sublist, try splitting the current word
		if si == len(swords):	
			# reset si and increment ui	
			si = 0
			ui = ui + 1
			# check current word
			type = uwords[ui]["type"]
			stext = uwords[ui]["text"]
			# for pronunciation, split by space
			if (type == "pronunciation"):
				stexts = text.split()
			# for punctuation, split into each char
			else:
				stexts = list(text)
		
		# compare aligned/unaligned words and update confidence
		text = word["text"]
		if text != stexts[si]:
			print (f"Warning: Algined words[{i}] = {text} does not match unaligned words[{ui}][{si}] = {stexts[si]}, will use default confidence for it.")
		else:
			word["confidence"] = uwords[ui]["confidence"]
			updated = updated + 1
			
		# move on to the next word in both the unaligned multi-word sublist and the aligned words list
		si = si + 1	
		i = i + 1

	return updated


# def find_next_success(gentle_transcript_json, current_index):
# 			previous_end = 0
# 			last_success_index = 0

# 	for word_index in range(current_index, len(gentle_transcript_json["words"])):
# 		word = gentle_transcript_json["words"][word_index]
# 		# Make sure we have all the data
# 		if word["case"] == 'success':
# 			print("Found success at " + str(word_index))
# 			return word_index		
# 	return None		
		
# 					words.append(
# 							{
# 								"type": "pronunciation", 
# 								"start": gword["start"], 
# 								"end": gword["end"], 
# 								"text": gword["gword"],
# 								"score": {
# 										"type": "confidence", 
# 										"scoreValue": 1.0
# 								} 
# 							}
# 						)
# 				# for not-found words, distribute timestamp evenly between the previous and next matched words
# 				else:
# 					next_success_index = find_next_success(gentle_transcript_json, gi)
# 					avg_time = 0
# 					# If we found another success
# 					if(next_success_index is not None and next_success_index > gi):
# 						# Average the times based on how many words in between
# 						next_success_word = gentle_transcript_json["words"][next_success_index]
# 						skips_ahead = (next_success_index - last_success_index)
# 						avg_time = (next_success_word["start"] - previous_end)/skips_ahead
# 						print("Averaging time from next success")
# 					else:
# 						duration = amp_transcript_unaligned_json["media"]["duration"]
# 						skips_ahead = (len(gentle_transcript_json["words"]) - gi) + 1
# 						avg_time = (duration - previous_end)/skips_ahead
# 						print("Averaging time from end of file")
# 
# 					if avg_time < 0:
# 						avg_time = 0
# 
# 					# From the previous words end (last recorded), skip time ahead
# 					time = previous_end + avg_time
# 					previous_end = time
# 					print(gword["gword"]  + " at index " + str(gi))
# 					print("Avg_time " + str(avg_time)  + " Skips ahead " + str(skips_ahead))
# 
# 					# Add the gword to the results
# 					words.append(
# 						{
# 							"type": "pronunciation", 
# 							"start": time, 
# 							"end": time, 
# 							"text": gword["gword"],
# 							"score": {
# 									"type": "confidence", 
# 									"scoreValue": 0.0
# 							} 
# 						}
# 					)
# 				last_success_index = gentle_transcript_json["words"].index(gword)	

		
if __name__ == "__main__":
	main()
