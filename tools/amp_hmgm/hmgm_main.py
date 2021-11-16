#!/usr/bin/env python3

import json
import os
import os.path
import sys
import traceback
import shutil

from mgm_logger import MgmLogger
import mgm_utils

from task_jira import TaskJira
from task_openproject import TaskOpenproject 
from task_redmine import TaskRedmine
from task_manager import TaskManager


# It's assumed that all HMGMs generate the output file in the same directory as the input file with ".completed" suffix added to the original filename
HMGM_OUTPUT_SUFFIX = ".complete"
JIRA = "Jira"
OPEN_PROJECT = "OpenProject"
REDMINE = "Redmine"


# Usage: hmgm_main.py task_type root_dir input_json output_json task_json context_json 
def main():
	# parse command line arguments
	task_type = sys.argv[1]     # type of HMGM task: (Transcript, NER, Segmentation, OCR), there is one HMGM wrapper per type
	root_dir = sys.argv[2]      # path for Galaxy root directory; HMGM property files, logs and tmp files are relative to the root_dir
	input_json = sys.argv[3]    # input file for HMGM task in json format
	output_json = sys.argv[4]   # output file for HMGM task in json format
	task_json = sys.argv[5]     # json file storing information about the HMGM task, such as ticket # etc
	context_json = sys.argv[6]  # context info as json string needed for creating HMGM tasks
#     context_json = '{ "submittedBy": "yingfeng", "unitId": "1", "unitName": "Test%27s Unit", "collectionId": "2", "collectionName": "Test%22s Collection", "taskManager": "Jira", "itemId": "3", "itemName": "Test%27s Item", "primaryfileId": "4", "primaryfileName": "Test%22s primaryfile", "primaryfileUrl": "http://techslides.com/demos/sample-videos/small.mp4", "primaryfileMediaInfo": "/tmp/hmgm/mediaInfo.json", "workflowId": "123456789", "workflowName": "Test%27%22 Workflow" }'

	# using output instead of input filename as the latter is unique while the former could be used by multiple jobs 
	logger = MgmLogger(root_dir, "hmgm_" + task_type, output_json)
	sys.stdout = logger
	sys.stderr = logger

	try:
		# clean up previous error file as needed in case this is a rerun of a failed job
		mgm_utils.cleanup_err_file(output_json)
		
		# as a safeguard, if input_json doesn't exist or is empty, throw exception to fail the job
		# (this means the conversion command failed before hmgm task command)
		mgm_utils.exception_if_file_not_exist(input_json)
		
		print ("Handling HMGM task: uncorrected JSON: " + input_json + ", corrected JSON: " + output_json + ", task JSON: " + task_json)				
        # Load basic HGMG configuration based from the property file under the given root directory
		config = mgm_utils.get_config(root_dir)
		context = json.loads(context_json)
		context = desanitize_context(context)
		
		# if input_json has empty data (not empty file), no need to go through HMGM task, just copy it to the output file, and done
		if empty_input(input_json, task_type):
			print ("Input file " + input_json + " for HMGM " + task_type + " editor contains empty data, skipping HMGM task and copy the input to the output")
			shutil.copy(input_json, output_json)
            # implicitly exit 0 as the current command completes
		# otherwise, if HMGM task hasn't been created, create one, exit 1 to get re-queued	
		elif not task_created(task_json):
			task = create_task(config, task_type, context, input_json, output_json, task_json)
			print ("Successfully created HMGM task " + task.key + ", exit 1")
			sys.stdout.flush()
			exit(1) 
		# otherwise, check if HMGM task is completed
		else:
			editor_output = task_completed(config, output_json)
			# if HMGM task is completed, close the task and move editor output to output file, and done
			if (editor_output):
				task = close_task(config, context, editor_output, output_json, task_json)
				print ("Successfully closed HMGM task " + task.key)
				sys.stdout.flush()
				# implicitly exit 0 as the current command completes
			# otherwise exit 1 to get re-queued
			else:
				print ("Waiting for HMGM task to complete ... exit 1")
				sys.stdout.flush()
				exit(1)        
	# upon exception, create error file to notify the following conversion command to fail, and exit -1 (error) to avoid re-quene
	except Exception as e:
		mgm_utils.create_err_file(output_json)
		print ("Failed to handle HMGM task: uncorrected JSON: " + input_json + ", corrected JSON: " + output_json, e)
		traceback.print_exc()
		sys.stdout.flush()
		exit(-1)


# Desanitize all the names in the given context.
def desanitize_context(context):
	# all the names were sanitized before passed to context, thus need to be decoded to original values
	context["unitName"] = desanitize_text(context["unitName"])
	context["collectionName"] = desanitize_text(context["collectionName"])
	context["itemName"] = desanitize_text(context["itemName"])
	context["primaryfileName"] = desanitize_text(context["primaryfileName"])
	context["workflowName"] = desanitize_text(context["workflowName"])
	return context


# Decode the given text which has been encoded with sanitizing rule for context JSON string,
# i.e. single/double quotes were replaced with % followed by the hex code of the quote.
def desanitize_text(text):
	text = text.replace("%27", "'");      
	text = text.replace('%22', '"');      
	return text


# Return true if the given input_json contains empty data based on format defined by the given task_type; false otherwise.
def empty_input(input_json, task_type):
	with open(input_json, 'r') as file:
		data = json.load(file)		
	if task_type == TaskManager.TRANSCRIPT:
		return not data['entityMap'] and not data['blocks']
	elif task_type == TaskManager.NER:
		return not data['annotations'][0]['items']
	# TODO update below logic	
	elif task_type == TaskManager.SEGMENTATION:
		return True
	elif task_type == TaskManager.OCR:
		return True
 
# Return true if HMGM task has already been created, i.e. the file containing the HMGM task info exists.
def task_created(task_json):    
	# Since Galaxy creates all output files with size 0 upon starting a job, we can't use the existence of task_json file 
	# to decide if the task has been created; rather, we can use its file size as the criteria
	# In addition, we could call TaskManager to check the task in the actual task platform, but that's an extra overhead and there is a chance of the task site being down. 
	# Since task_json is only created with task info after a task gets created successfully, we can use it as an indicator of task existence.
	if os.path.exists(task_json):
		return os.stat(task_json).st_size > 0
	else:
		return False


# If HMGM task has already been completed, i.e. the completed version of the given output JSON file exists, return the output file path; otherwise return False. 
def task_completed(config, output_json):   
	editor_output = get_editor_input_path(config, output_json) + HMGM_OUTPUT_SUFFIX
	if os.path.exists(editor_output):
		return editor_output
	else:
		return False


# Create an HMGM task in the specified task management platform with the given context and input/output files, 
# save information about the created task into a JSON file, and return the created task.
def create_task(config, task_type, context, input_json, output_json, task_json):
	# set up the input file in the designated location for HMGM task editor to pick up
	editor_input = setup_editor_input_file(config, input_json, output_json)
	
	# get task management instance based on task platform specified in context
	taskManager = get_task_manager(config, context)
	
	# calling task manager API to create task in the corresponding platform
	return taskManager.create_task(task_type, context, editor_input, task_json)
	
	
# Close the HMGM task specified in the task information file in the corresponding task mamangement platform.
def close_task(config, context, editor_output, output_json, task_json):
	# clean up the output file dropped by HMGM task editor in the designated location
	cleanup_editor_output_file(editor_output, output_json)
	
	# get task management instance based on task platform specified in context
	taskManager = get_task_manager(config, context)
	
	# calling task manager API to close task in the corresponding platform
	return taskManager.close_task(task_json)
	
	
# Set up the input file corresponding to the given input JSON file in the designated location for HMGM editors to pick up.     
def setup_editor_input_file(config, input_json, output_json):     
	# TODO update logic here as needed to generate an obscure soft link instead of copying
	# Below we pass the galaxy job output file name to the task editor because the input file name is not unique, 
	# as multiple jobs can run on the same input file, in which case Galaxy pass the same input file path to the tool;
	# meanwhile, the output file name is unique, as Galaxy always creates a new dataset for the output file each time a job is run.
	editor_input = get_editor_input_path(config, output_json)
	shutil.copy(input_json, editor_input)
#     os.symlink(input_json, editor_input)
	return editor_input


# Clean up the output file dropped by HMGM task editors by moving it from the designated location to the output file expected by Galaxy job;
# also, (optionally) remove the corresponding input file in that directory, and return the input file path.
def cleanup_editor_output_file(editor_output, output_json):     
	# move the completed output file to the location expected by Galaxy
	shutil.move(editor_output, output_json)

	# TODO decide if it's better to remove the input file here or do it in a batch process
	editor_input = editor_output[:-len(HMGM_OUTPUT_SUFFIX)]
	# need to check if the original file exists since in case it was never saved to a tmp file it would have been moved to .complete file
	if os.path.exists(editor_input):
		os.remove(editor_input)
	
	return editor_input

	
# Derive the temporary input/output file path used by HMGM tool editors for the given dataset file passed in from the corresponding Galaxy job. 
def get_editor_input_path(config, dataset_file):
	# Note: 
	# For security concerns, we don't pass the original input/output path to HMGM task editors, to avoid exposing the internal Galaxy file system 
	# to external web apps; Instead, we use a designated directory for passing such input/output files, and generate a soft link in 
	# (or copy the file to) this directory, using a filename uniquely mapped from the original filename.  
	io_dir = config["general"]["hmgm_dir"] 

	# TODO replace below code with logic to generate an obscure soft link based on the original file path
	# for now we just use the original filename within the designated directory
	filename = os.path.basename(dataset_file)
	filepath = os.path.join(io_dir, filename)
	
	return filepath
	 
	
# Create subclass of task manager instance based on task platform specified in the given context.
def get_task_manager(config, context):
	manager = context["taskManager"]
	assert manager in (JIRA, OPEN_PROJECT, REDMINE), f"taskManager {taskManager} is not one of ({JIRA}, {OPEN_PROJECT}, {REDMINE})" 
	
	# create subclass of task instance based on task platform specified in context
	if manager == JIRA:
		taskManager = TaskJira(config)
	elif manager == OPEN_PROJECT:
		taskManager = TaskOpenproject(config)
	elif manager == REDMINE:
		taskManager = TaskRedmine(config)            
	return taskManager


if __name__ == "__main__":
	main()    
