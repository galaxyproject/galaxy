# User Creation scripts
In some occassions a Galaxy admin may want to run some scripts after an account has been created. This could be accomplished by using cronjobs that regularly run to handle some basic user interactions. However, here is described how to use the system to add this directly to Galaxy.

## How does the system work
The system reads the [Configuration Options](#configuration-options) and uses them to determine which scripts to use.
Once a user has been created, the script(s) are automatically triggered. They will run at the same time. The scripts are
set up to be non-blocking to the user creation process. So the user has feedback before the scripts have finished. This is to avoid long running scripts from slowing down the process for the user. 

**Main takeaways**:
*  Scripts start at the same time
*  Scripts run in separate processes
*  Scripts are non-blocking to user creation process.

## Configuration options
There are 2 configuration options needed to set this up. These are:
*  ```
   user_create_base_modules
   ```
   This defines where Galaxy will find the scripts. This is similar to the `toolbox_filter_base_modules` configuration option.
*  ```
   user_create_functions
   ```
   This defines which scripts Galaxy should execute. This is similar to the `user_tool_label_filters` configuration option.
 
 ## Scripts
The function in the script receives the `User` model in a dictionary form as parameter. An example application is provided in `lib/galaxy/users/create/examples.py.sample`. A very simple email logging system to the Galaxy root folder would look as follows:
```python
import os

def log_email(user):
    basefolder = os.getenv("PWD", "/tmp")
    with open(os.path.join(basefolder, "log_email.txt"), "a") as f:
        f.write("%s\n" % user.get("email"))
```

**Please note the following**:
*  Exceptions may not be logged in Galaxy's logs due to the non-blocking system
*  There are no functions of the `User` model object available. Only the actual values are provided. This is a limitation of the non-blocking system.
