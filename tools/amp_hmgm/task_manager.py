import urllib.parse


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

         # for Transcript
         self.transcript_api = config["amppd"]["transcript_api"] 
         self.transcript_input = config["amppd"]["transcript_input"] 
         self.transcript_media = config["amppd"]["transcript_media"] 
         
         # for NER
         self.ner_api = config["amppd"]["ner_api"] 
         self.ner_input = config["amppd"]["ner_input"] 
         
         # for Segmentation
         self.segmentation_api = config["amppd"]["segmentation_api"] 
         self.segmentation_input = config["amppd"]["segmentation_input"] 
         
         # TODO set up properties for other HMGM tools


     # Return description of an HMGM task based on the given task_type, context, input file etc.
     def get_task_description(self, task_type, context, editor_input):
         description = "Submitted By: " + context["submittedBy"] + "\n"
         description += "Unit " + context["unitId"] + ": " + context["unitName"] + "\n"
         description += "Collection  " + context["collectionId"] + ": " + context["collectionName"] + "\n"
         description += "Item " + context["itemId"] + ": " + context["itemName"] + "\n"
         description += "Primary File " + context["primaryfileId"] + ": " + context["primaryfileName"] + "\n"
         description += "Workflow " + context["workflowId"] + ": " + context["workflowName"] + "\n"              
         description += "Editor URL: " + self.get_editor_url(task_type, context["primaryfileUrl"], editor_input)          
         return description
     
     
     # Return the URL link to the editor tool for an HMGM task based on the given task_type, media, input file etc.
     def get_editor_url(self, task_type, media, editor_input):
         assert task_type in (self.TRANSCRIPT, self.NER, self.SEGMENTATION, self.OCR)
         
         if task_type == self.TRANSCRIPT:
             api_url = self.amppd_server + self.transcript_api 
             params = {self.transcript_input: editor_input, self.transcript_media: media}
             url = api_url + "?" + urllib.parse.urlencode(params)
         elif task_type == self.NER:
             api_url = self.amppd_server + self.ner_api 
             params = {self.ner_input: editor_input}
             url = api_url + "?" + urllib.parse.urlencode(params)
         elif task_type == self.SEGMENTATION:
             api_url = self.amppd_server + self.segmentation_api 
             params = {self.segmentation_input: editor_input}
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
