from task_manager import TaskManager


class TaskOpenproject (TaskManager):
     """Subclass of TaskManager implementing HMGM task management with OpenProject platforms."""
     
     def __init__(self, root_dir):
         self.root_dir = root_dir
         # TODO add logic to set up Open Project task manager
     
     def create_task(self, task_type, context, input_path, task_json):
         # TODO replace with real logic, make sure the task_json contains ID, key, URL
         return None
     
     def close_task(self, task_json):
         # TODO replace with real logic
         return None