import subprocess

# Class name should be lower case
# Class Docstring will be the action name included in the select box


class notification_control():
    """
    Send Desktop notification
    """

    def __init__(self, **args):
        self.dataset_assoc = args.get('dataset_assoc', None)
        self.app = args.get('app', None)
        self.job = args.get('job', None)
        self.trans = args.get('trans', None)
        self.user = args.get('user', None)

    def check_privileges(self):
        """
        Return True if the user is allowed to see and execute the run() function.
        """
        return True

    def run(self):
        """
        This is just an example and will only work with local Galaxy instances
        with the tool notify-send installed.
        """
        subprocess.call('notify-send "Taking Photo!"', shell=True)
