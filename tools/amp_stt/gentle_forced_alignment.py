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


def main():
	(input_audio_file, input_transcript_file, json_file) = sys.argv[1:4]
	exception = False
	try:
		# Create random temp names
		tmpAudioName = str(uuid.uuid4())
		tmpTranscriptName = str(uuid.uuid4())

		# Define directory accessible to singularity container
		tmpdir = '/tmp'

		# Create temp file paths
		temp_audio_file = f"{tmpdir}/{tmpAudioName}.dat"
		temp_transcript_file = f"{tmpdir}/{tmpTranscriptName}.dat"
		temp_output_file = f"{tmpdir}/{tmpAudioName}.json"

		# Load the original transcript as input into gentle
		with open(input_transcript_file, "r") as input_ts_file:
			orig_transcript = json.load(input_ts_file)

			# Write the transcript to an input file into gentle
			with open(temp_transcript_file, "w") as text_file:
				text_file.write(orig_transcript["results"]["transcript"])

			# Copy the audio file to a location accessible to the singularity container
			shutil.copy(input_audio_file, temp_audio_file)

			# Run gentle
			print("Running gentle")
			r = subprocess.run(["singularity", "run", "/srv/amp/gentle-singularity/gentle-singularity.sif", temp_audio_file, temp_transcript_file, "-o", temp_output_file], stdout=subprocess.PIPE)
			print("Finished running gentle")

			print("Creating amp transcript output")
			write_amp_json(temp_output_file, orig_transcript, json_file)
	except Exception as e:
		print("Exception")
		print(e)
		exception = True

	if os.path.exists(temp_audio_file):
	 	os.remove(temp_audio_file)

	if os.path.exists(temp_transcript_file):
		os.remove(temp_transcript_file)

	if os.path.exists(temp_output_file):
		os.remove(temp_output_file)
	
	if exception == True:
		print("Existing due to exception")
		exit(1)

	print("Return Code: " + str(r.returncode))
	exit(r.returncode)

def find_next_success(gentle_output, current_index):

	for word_index in range(current_index, len(gentle_output["words"])):
		word = gentle_output["words"][word_index]
		# Make sure we have all the data
		if word["case"] == 'success':
			print("Found success at " + str(word_index))
			return word_index
		
	return None

def write_amp_json(temp_gentle_output, original_transcript, amp_transcript_output):
	# Create the amp transcript
	output = dict()
	with open(temp_gentle_output, "r") as gentle_output_file:
		gentle_output = json.load(gentle_output_file)
		output["media"] = original_transcript["media"]
		output["results"] = dict()
		output["results"]["transcript"] = original_transcript["results"]["transcript"]
		output["results"]["words"] = list()
		previous_end = 0
		last_success_index = 0
		if "words" in gentle_output.keys():
			for word in gentle_output["words"]:
				# Make sure we have all the data
				if word["case"] == 'success':
					previous_end = word["end"]
					output["results"]["words"].append(
							{
								"type": "pronunciation", 
								"start": word["start"], 
								"end": word["end"], 
								"text": word["word"],
								"score": {
										"type": "confidence", 
										"scoreValue": 1.0
								} 
							}
						)
				else:
					word_index = gentle_output["words"].index(word)
					next_success_index = find_next_success(gentle_output, word_index)
					avg_time = 0
					# If we found another success
					if(next_success_index is not None and next_success_index > word_index):
						# Average the times based on how many words in between
						next_success_word = gentle_output["words"][next_success_index]
						skips_ahead = (next_success_index - last_success_index)
						avg_time = (next_success_word["start"] - previous_end)/skips_ahead
						print("Averaging time from next success")
					else:
						duration = original_transcript["media"]["duration"]
						skips_ahead = (len(gentle_output["words"]) - word_index) + 1
						avg_time = (duration - previous_end)/skips_ahead
						print("Averaging time from end of file")

					if avg_time < 0:
						avg_time = 0

					# From the previous words end (last recorded), skip time ahead
					time = previous_end + avg_time
					previous_end = time
					print(word["word"]  + " at index " + str(word_index))
					print("Avg_time " + str(avg_time)  + " Skips ahead " + str(skips_ahead))

					# Add the word to the results
					output["results"]["words"].append(
						{
							"type": "pronunciation", 
							"start": time, 
							"end": time, 
							"text": word["word"],
							"score": {
									"type": "confidence", 
									"scoreValue": 1.0
							} 
						}
					)
				last_success_index = gentle_output["words"].index(word)
								
		mgm_utils.write_json_file(output, amp_transcript_output)
		
		
if __name__ == "__main__":
	main()
