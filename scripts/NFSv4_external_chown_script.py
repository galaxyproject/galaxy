#!/usr/bin/env python
import errno
import json
import os
import pwd
import sys
#import drmaa

#new_path = [ os.path.join( os.getcwd(), "lib" ) ]
#new_path.extend( sys.path[1:] ) # remove scripts/ from the path
#sys.path = new_path

#from galaxy import eggs
#import pkg_resources
#pkg_resources.require("drmaa")
#import drmaa

def validate_paramters():
    if len(sys.argv)<4:
        sys.stderr.write("usage: %s path user_name gid\n" % sys.argv[0])
        exit(1)

    path  = sys.argv[1]
    galaxy_user_name  = sys.argv[2]
    gid  = sys.argv[3]

    return path, galaxy_user_name, gid 

def main():
    daemon_username = 'galaxyuser';
    daemon_groupname = 'galaxy';
    path, galaxy_user_name, gid  = validate_paramters()
    os.system('chown -Rh %s %s' %(galaxy_user_name, path))
    os.system('chgrp -Rh %s %s' %(gid, path))
    #os.system('chmod og-rwX -R %s' %(path))
    os.system('chmod o-rwX -R %s' %(path))
    os.system('chmod g-w -R %s' %(path))

    #os.system('setfacl -R -m g:%s:rX %s' %(daemon_groupname, path))	#should be group so that nginx user can also see this dataset
    #os.system('setfacl -R -m u:%s:rwX %s' %(daemon_username, path))	#for metadata - write permission

    os.system('nfs4_setfacl -RP -a A:g:%s@acc.ohsu.edu:rtnc %s' %(daemon_groupname, path))	#read access, but no execute
    os.system('nfs4_setfacl -RP -a A::%s@acc.ohsu.edu:rwadDtTnNcC %s' %(daemon_username, path))	#rw access, but no execute
    if(os.path.isdir(path)):
      os.system('nfs4_setfacl -P -a A:g:%s@acc.ohsu.edu:x %s' %(daemon_groupname, path))	#execute access to top level directory
      os.system('nfs4_setfacl -P -a A::%s@acc.ohsu.edu:x %s' %(daemon_username, path))	#execute access to top level directory
      os.system('find %s -type d -exec nfs4_setfacl -P -a A:g:%s@acc.ohsu.edu:x {} \;' %(daemon_groupname, path))	#execute access for all sub-dirs
      os.system('find %s -type d -exec nfs4_setfacl -P -a A::%s@acc.ohsu.edu:x  {} \;' %(daemon_username, path))	#execute access for all sub-dirs

if __name__ == "__main__":
    main()


