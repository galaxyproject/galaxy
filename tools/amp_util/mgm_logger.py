import sys
import os
from datetime import datetime
import shutil
import zipfile
import gzip

import mgm_utils


class MgmLogger(object):
    log_file_size = 1000000
    def __init__(self, root_dir, logname, input_file):
        self.terminal = sys.stdout
        log_file_name = self.create_log_file(root_dir, input_file, logname)
        self.log = open(log_file_name, "a")
        
    def create_log_file(self, root_dir, input_file, logname):
        base_name = os.path.basename(input_file)
        file_name = base_name + "_" + logname + ".log"
        log_path = self.get_log_dir(root_dir)
        log_file_name = os.path.join(log_path, file_name)
        self.roll_log_file(log_file_name)
        return log_file_name.lower()

    def compress_log_file(self, log_file_name):
        base_name = os.path.basename(log_file_name)
        with open(log_file_name, 'rb') as f_in:
            with open(log_file_name + '.gz', 'wb') as f_out:
                with gzip.GzipFile(base_name, 'wb', fileobj=f_out) as f_out:
                    shutil.copyfileobj(f_in, f_out)

    def roll_log_file(self, log_file):
        if os.path.exists(log_file) == False:
            return

        file_stats = os.stat(log_file)
        
        # If the log file is greater than the max size, move it, start with the base log name
        if file_stats.st_size > self.log_file_size:
            # Find the next iterator.  If it's greater than 1000, will keep appending
            for i in range(1,1000):
                tmp_file_name = log_file + "." + str(i)
                if os.path.exists(tmp_file_name)==False:
                    shutil.move(log_file,tmp_file_name)
                    self.compress_log_file(tmp_file_name)
                    os.remove(tmp_file_name)
                    break

    def write(self, message):
        now = datetime.now()
        date_time = now.strftime("%m/%d/%Y %H:%M:%S")
        self.terminal.write(message)
        self.log.write(date_time + "\t" + message + "\n")  
    
    def get_log_dir(self, root_dir):
        config = mgm_utils.get_config(root_dir)
        return config["general"]["log_dir"]

    def flush(self):
        pass    