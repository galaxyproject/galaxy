#!/usr/bin/env python3
import os
import os.path
from random import seed
from random import random
import sys
import traceback

# Example implementation of an HMGM task
# The task runner looks for specific exit codes in determining whether or not to terminate(0), requeue(255), or fail (1)
# This example uses a random number to determine when to terminate, but in the actual implementation it should look
# for a specific file
def main():
    (output_file) = sys.argv[1]
    try:
        if task_exists() == False:
            # Create the task
            create_task()
            # Exit to requeue
            exit(255) 
        else:
            # Check to see if the task is complete
            task_complete = is_task_complete()

            # If the task is complete, make api call to mark task as such
            if task_complete:
                # Mark it complete in task manager
                mark_complete()
                write_output_file(output_file) # For testing only
                # Exit with success
                exit(0)
            else:
                # Exit to requeue
                exit(255)        
    except Exception as e:
        print ("Failed to handle HMGM-Sample task", e)
        traceback.print_exc()
        exit(1)

# Method stub to check and see if a task is complete.
# Real implementation would include checking for a specific file (.complete, etc)
def is_task_complete():
    ran = random()
    print(ran)
    if ran > .9:
        return True
    else:
        return False
    return True

# Method stub to make API call and mark task as complete
def mark_complete():
    print("Marking complete in JIRA")

# Check to see if we've already registered task in task manager
def task_exists():
    print("Checking to see if task exists in JIRA")
    return True

# Method stub to create the task
def create_task():
    print("Creating task in JIRA")

# Write the output file for testing purposes only  
def write_output_file(output_file):
    f = open(output_file, "a")
    f.write("Now the file has more content!")
    f.close()

if __name__ == "__main__":
    main()