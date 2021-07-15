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
from builtins import None


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
			print(f"Running Gentle... tmp_speech_audio: {tmp_speech_audio}, input tmp_amp_transcript_unaligned: {tmp_amp_transcript_unaligned}, tmp_gentle_transcript: {tmp_gentle_transcript}")
			r = subprocess.run(["singularity", "run", "/srv/amp/gentle-singularity/gentle-singularity.sif", tmp_speech_audio, tmp_amp_transcript_unaligned, "-o", tmp_gentle_transcript], stdout=subprocess.PIPE)
			print("Finished running Gentle")

			# Copy the tmp Gentle output file to gentle_transcript
			shutil.copy(tmp_gentle_transcript, gentle_transcript)

			print("Creating amp transcript aligned...")
			gentle_transcript_to_amp_transcript(gentle_transcript, amp_transcript_unaligned_json, amp_transcript_aligned)
			
			print(f"Gentle return Code: {r.returncode}")
			exit(r.returncode)
	except Exception as e:
		print("Exception while running Gentle:")
		traceback.print_exc()
		exit(1)



def gentle_transcript_to_amp_transcript(gentle_transcript, amp_transcript_unaligned_json, amp_transcript_aligned):
	# Create the amp transcript
	amp_transcript_aligned_json = dict()
	with open(gentle_transcript, "r") as gentle_transcript_file:
		gentle_transcript_json = json.load(gentle_transcript_file)
		amp_transcript_aligned_json["media"] = amp_transcript_unaligned_json["media"]
		amp_transcript_aligned_json["results"] = dict()
		amp_transcript_aligned_json["results"]["transcript"] = amp_transcript_unaligned_json["results"]["transcript"]
		amp_transcript_aligned_json["results"]["words"] = list()
		
		if "words" in gentle_transcript_json.keys():
			gwords = gentle_transcript_json["words"]
			uwords = amp_transcript_unaligned_json["results"]["words"]
			words = amp_transcript_aligned_json["results"]["words"]
			duration = amp_transcript_unaligned_json["media"]["duration"]
			gi = ui = 0	
			next = None
			
			while gi < len(gwords):
				# find the next successful alignment and the interval between previous alignment
				[next, interval] = find_next_success(words, gi, duration)
										
				# if current word is a success match, use the aligned timestamp
				if gwords[gi]["case"] == 'success':
					start = gwords[gi]["start"]
					end = gwords[gi]["end"]
				# otherwise, distribute timestamp evenly between the previous and next matched words
				else:
					
					
			
								
		mgm_utils.write_json_file(amp_transcript_aligned_json, amp_transcript_aligned)
		
# Compute the average time interval for unmatched words in the given words list, starting from the given current index 
# (next to the previous match), and return a list containing the next match index and the average time interval in between.
# If the current index is 0, use 0 as the previous match end timestamp;
# if no next match can be found, use the given duration as the next match start timestamp. 
def find_next_success(words, current, duration):	
	if current = 0:
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
	if next == len(["words"]:
		interval = (duration - end) / (next - current)				
	return [next, interval]
		

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
