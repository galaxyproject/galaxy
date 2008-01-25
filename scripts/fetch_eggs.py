#!/usr/bin/env python2.4
"""
fetch_eggs acquires the eggs necessary to run Galaxy from a central
repository.  Run without arguments to fetch eggs for the current
platform, or with a specific platform as an argument.

For a platform list, see the contents of the directory specified in the
'repo' variable below.  It takes the basic form of:

python_version-os_name-os_version-cpu_architecture-unicode_size

With the notable exception that the os_version is excluded when the
os_name is Linux.  Mac OS X with Universal MacPython (macpython.org)
is always python_version-macosx-10.3-fat-ucs2 .

Some examples:

py2.4-linux-i686-ucs4 (debian, ubuntu 32 bit)
py2.4-linux-x86_64-ucs2 (rhel, fedora, centos 64 bit)
py2.4-solaris-2.10-sparc-ucs2 (solaris 10 sparc)

check_python_ucs.py in this directory will tell you what UCS is correct
for your particular python.
"""

repo = "http://eggs.g2.bx.psu.edu"

import os, sys, glob

def get_egg_platform():

    # platform can be specified as an arg
    if len(sys.argv) > 1:
        py = (sys.argv[1].split('-', 1))[0]
        ucs = (sys.argv[1].rsplit('-', 1))[1]
        return ( sys.argv[1], ucs, "%s-noarch" % py )

    # else figure it out ourselves
    py = "py%s" % sys.version[0:3]
    if sys.maxunicode > 65535:
        ucs = "ucs4"
    else:
        ucs = "ucs2"

    from distutils.util import get_platform
    platform = get_platform()
    if platform.startswith('darwin-8'):
        platform = "macosx-10.3-fat"
    full_platform = "%s-%s-%s" % (py, platform, ucs)

    return (full_platform, ucs, "%s-noarch" % py)

def get_eggs( tar=False ):

    (platform, ucs, noarch) = get_egg_platform()

    here = os.path.abspath(os.path.dirname(sys.argv[0]))
    if tar:
        eggs = os.path.abspath( "%s/../eggs_dist/%s/eggs" % ( here, platform ) )
    else:
        eggs = os.path.abspath("%s/../eggs" % here)
    sys.path.append("%s/../lib" % here)
    sys.path.append("%s/../eggs" % here) # twill is here regardless of what eggs is, above

    import pkg_resources
    pkg_resources.require('twill')
    import twill.commands as tc
    import twill.errors as te

    if tar:
        import tarfile

    ucseggs = "%s/%s" % ( eggs, ucs.upper() )

    platform_url = "%s/%s" % ( repo, platform )
    noarch_url = "%s/%s" % ( repo, noarch )

    platforms = { platform : ( ucseggs, platform_url ), noarch : ( eggs, noarch_url ) }
    failed_platforms = []

    for plat in platforms:

        print "fetching eggs for %s" % plat
        (eggs, url) = platforms[plat]

        if not os.path.exists( eggs ):
            try:
                os.makedirs( eggs )
            except Exception, e:
                print "Egg directory creation failed! (details follow):"
                print e
                failed_platforms.append(plat)
                continue

        try:
            tc.go(url)
            tc.code(200)
        except te.TwillAssertionError, e:
            #print "eggs are not available for this platform (twill error follows):"
            #print e
            print "eggs are not available for this platform (continuing to fetch additional platforms)"
            failed_platforms.append(plat)
            continue

        for link in tc.get_browser()._browser.links():
            if not link.url.endswith('.egg'):
                continue
            if os.path.exists("%s/%s" % ( eggs, link.url )):
                print "Skipping %s, already exists" % link.url
                continue
            (pkg, version, rest) = link.url.split('-', 2)
            for old in glob.glob( "%s/%s-*-%s" % ( eggs, pkg, rest ) ):
                print "Removing differing version of %s: %s" % ( pkg, old )
                try:
                    os.unlink( old )
                except Exception, e:
                    print "Removal failed! (details follow):"
                    print e
                    sys.exit(1)
            print "Fetching", link.url
            tc.go( "%s/%s" % ( url, link.url ) )
            tc.code( 200 )
            tc.save_html( "%s/%s" % ( eggs, link.url ) )

    if tar:
        try:
            tfname = os.path.abspath( "%s/../eggs_dist/%s.tar" % ( here, platform ) )
            t = tarfile.open( tfname, 'w' )
            os.chdir( "%s/../eggs_dist/%s" % ( here, platform ) )
            t.add( "eggs" )
            t.close()
            print "Created egg tarfile:", tfname
        except Exception, e:
            print "Unable to create tarfile (details follow)"
            print e
            sys.exit(1)

    print ""
    print "WARNING: The script was unable to download eggs for these platforms:"
    print ""
    print "\n".join(failed_platforms)
    print ""
    print "This will probably make Galaxy unusable.  Because of the wide range of"
    print "operating systems and os versions available on which Galaxy will run,"
    print "the Galaxy developers are not always able to provide pre-built eggs."
    print "For information on building eggs on your own platform, please see the"
    print "Scramble page on the Galaxy wiki at:"
    print ""
    print "http://g2.trac.bx.psu.edu/wiki/Scramble"
    print ""
    print "or email galaxy-bugs@bx.psu.edu"
    print ""

if __name__ == "__main__":
    get_eggs()
