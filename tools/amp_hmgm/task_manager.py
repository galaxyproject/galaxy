import urllib.parse
import uuid
import hashlib


class TaskManager:
	"""Abstract base class defining the API for all HMGM task management implementations, which are based on task management platforms."""

	TRANSCRIPT = "Transcript"
	NER = "NER"
	SEGMENTATION = "Segmentation"
	OCR = "OCR"

	# Set up HMGM properties with the given configuration instance.
	def __init__(self, config):
		self.config = config
		self.amppd_server = config["amppd"]["server"]
		self.auth_string = config["hmgm"]["auth_string"]

		# for Transcript
		self.transcript_api = config["hmgm"]["transcript_api"]
		self.transcript_input = config["hmgm"]["transcript_input"]
		self.transcript_media = config["hmgm"]["transcript_media"]

		# for NER
		self.ner_api = config["hmgm"]["ner_api"]
		self.ner_input = config["hmgm"]["ner_input"]

		# for Segmentation
		self.segmentation_api = config["hmgm"]["segmentation_api"]
		self.segmentation_input = config["hmgm"]["segmentation_input"]

		# TODO set up properties for other HMGM tools

	# Create an auth string to be used by external links to validate without user credentials
	# Returns an auth string to use in the URL as well as a user token to provide the user in the task manager ticket. 
	def create_auth_string(self, editor_input):
		m = hashlib.sha256()
		key = self.config["hmgm"]["auth_key"]
		user_token = str(uuid.uuid1())
		m.update(user_token.encode('utf-8'))
		m.update(editor_input.encode('utf-8'))
		m.update(key.encode('utf-8'))
		auth_string = m.hexdigest()
		print("Created auth string " + auth_string + " with key " + user_token)
		return auth_string, user_token

	 # Return description of an HMGM task based on the given task_type, context, input file etc.
	def get_task_description(self, task_type, context, editor_input):
		auth_string, user_token = self.create_auth_string(editor_input)
		description = "Submitted By: " + context["submittedBy"] + "\n"
		description += "Unit " + context["unitId"] + ": " + context["unitName"] + "\n"
		description += "Collection  " + context["collectionId"] + ": " + context["collectionName"] + "\n"
		description += "Item " + context["itemId"] + ": " + context["itemName"] + "\n"
		description += "Primary File " + context["primaryfileId"] + ": " + context["primaryfileName"] + "\n"
		description += "Workflow " + context["workflowId"] + ": " + context["workflowName"] + "\n"
		description += "Editor Password: " + user_token + "\n"
		description += "Editor URL: " + self.get_editor_url(task_type, context["primaryfileUrl"], editor_input, auth_string)
		return description


	 # Return the URL link to the editor tool for an HMGM task based on the given task_type, media, input file etc.
	def get_editor_url(self, task_type, media, editor_input, auth_string):
		assert task_type in (self.TRANSCRIPT, self.NER, self.SEGMENTATION, self.OCR)

		if task_type == self.TRANSCRIPT:
			api_url = self.amppd_server + self.transcript_api
			params = {self.transcript_input: editor_input, self.transcript_media: media, self.auth_string : auth_string}
			url = api_url + "?" + urllib.parse.urlencode(params)
		elif task_type == self.NER:
			api_url = self.amppd_server + self.ner_api
			params = {self.ner_input: editor_input, self.auth_string : auth_string}
			url = api_url + "?" + urllib.parse.urlencode(params)
		elif task_type == self.SEGMENTATION:
			api_url = self.amppd_server + self.segmentation_api
			params = {self.segmentation_input: editor_input, self.auth_string : auth_string}
			url = api_url + "?" + urllib.parse.urlencode(params)
		elif task_type == self.OCR:
			# TODO url for OCR
			url = self.amppd_server

		return url


	 # Abstract method to create a task in the designated task management platform, given the task_type, context, input file etc.
	 # save information about the created task into a JSON file, and return the task instance.
	def create_task(self, task_type, context, editor_input, task_json):
		raise Exception("Method TaskManager.create_task is an abstract method, please call an implemented version from a subclass.")


	# Abstract method to close the task specified in task_json by updating its status and relevant fields, and return the task instance.
	def close_task(self, task_json):
		raise Exception("Method TaskManager.close_task is an abstract method, please call an implemented version from a subclass.")
