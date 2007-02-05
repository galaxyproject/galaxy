#Provides Upload tool with access to list of available builds
import galaxy.util
builds = []

#Read build names and keys from galaxy.util
for dbkey, build_name in galaxy.util.dbnames:
    builds.append((build_name,dbkey,False))

#Return available builds
def get_available_builds():
    return builds
