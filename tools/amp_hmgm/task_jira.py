import json
from jira import JIRA

from task_manager import TaskManager

 
class TaskJira (TaskManager):
     """Subclass of TaskManager implementing HMGM task management with Jira platforms."""
     
     
     # Set up jira instance with properties in the given configuration instance.
     def __init__(self, config):
         super().__init__(config)
         
         # get Jira server info from the config 
         jira_server = config["jira"]["server"]
         jira_username = config["jira"]["username"]
         jira_password = config["jira"]["password"]         
         self.jira_project = config["jira"]["project"]         
         self.jira = JIRA(server = jira_server, basic_auth = (jira_username, jira_password))
         
         
     # Create a jira issue given the task_type, context, input/output json, 
     # save information about the created issue into a JSON file, and return the issue.
     def create_task(self, task_type, context, editor_input, task_json):
         # populate the jira fields into a dictionary with information from task_type and context etc
         project = {"key": self.jira_project}
         issuetype = {"name": "Task"}
         labels = [task_type]
         summary = context["primaryfileName"] + " - " + context["workflowName"] 
         description = self.get_task_description(task_type, context, editor_input)         
         jira_fields = {"project" : project, "issuetype": issuetype, "labels": labels, "summary": summary, "description": description}
         
         # create a new task jira using jira module
         issue = self.jira.create_issue(fields = jira_fields)
         
         # extract important information (ID, key, and URL) of the created issue into a dictionary, which is essentially the response returned by Jira server
         issue_dict = {"id": issue.id, "key": issue.key, "url": issue.permalink()} 

         # write jira issue into task_json file to indicate successful creation of the task
         with open(task_json, "w") as task_file:
             json.dump(issue_dict, task_file)
                  
         return issue
     
          
     # Close the jira issue specified in task_json by updating its status and relevant fields, and return the issue.          
     def close_task(self, task_json):
         # read jira issue info from task_json into a dictionary
         with open(task_json, 'r') as task_file:
             issue_dict = json.load(task_file)
         
         # get the jira issue using id
         issue = self.jira.issue(issue_dict["id"])
         
         # retrieve transition ID based on name = Done instead of hard coding it, in case the ID might be different
         transitions = self.jira.transitions(issue)
         transition = None
         for t in transitions:
             if t["name"] == "Done":    # Done is the status when an issue is closed
                 transition = t["id"]
                 break
             
         # if transition is None, that means issue is already in Done status
         if transition is None:
             print("Issue  " + issue.id + " is already Done, probably closed manually by someone")
         # otherwise update the jira status to Done via transition
         else:
             print("Transition issue " + issue.id + " to status " + transition)
             self.jira.transition_issue(issue, transition)
                  
         return issue
     
     