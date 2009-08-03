This folder holds cron jobs that support galaxy.

updateucsc.sh is a shell script to facilitate the updates from UCSC.
Galaxy stores several files locally to speed up operations that depend
on information from UCSC.  These files can all be found in the
static/ucsc folder.

Before adding updateucsc.sh to the crontab, it is important to note
two things.  First, updateucsc.sh must be edited to point towards the
root galaxy directory.  At the top of the file there is a variable
"GALAXY" that should be edited.  Second, the updates come from UCSC
via their table browsers.  While the tendency is typically to run cron
jobs late at night, UCSC, like most, tend to take down their servers
at odd hours for maintenance.  The update scripts for UCSC are not CPU
intensive, and should be scheduled during normal hours.
