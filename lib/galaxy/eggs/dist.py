"""
Manage Galaxy eggs
"""

import os, sys, subprocess
from scramble import ScrambleEgg, ScrambleCrate, ScrambleFailure, galaxy_dir, py
from __init__ import Crate, CaseSensitiveConfigParser

import logging
log = logging.getLogger( __name__ )
log.addHandler( logging.NullHandler() )

class DistScrambleEgg( ScrambleEgg ):
    def set_dir( self ):
        self.dir = os.path.join( galaxy_dir, 'dist-eggs', self.name )
        if not os.path.exists( self.dir ):
            os.makedirs( self.dir )
    @property
    def path( self ):
        # don't look for compatible eggs, look for exact matches
        if os.path.exists( self.distribution.location ):
            return self.distribution.location
        return None
    def run_scramble_script( self ):
        log.warning( "%s(): Beginning build" % sys._getframe().f_code.co_name )
        # subprocessed to sterilize the env
        cmd = "ssh %s 'cd %s; PYTHONPATH= %s -ES %s'" % ( self.build_host, self.buildpath, self.python, 'scramble.py' )
        log.debug( '%s(): Executing:' % sys._getframe().f_code.co_name )
        log.debug( '  %s' % cmd )
        p = subprocess.Popen( args = cmd, shell = True )
        r = p.wait()
        if r != 0:
            raise ScrambleFailure( "%s(): Egg build failed for %s %s" % ( sys._getframe().f_code.co_name, self.name, self.version ) )
    def unpack_if_needed( self ):
        return # do not unpack dist eggs

class DistScrambleCrate( ScrambleCrate ):
    """
    Holds eggs with info on how to build them for distribution.
    """
    dist_config_file = os.path.join( galaxy_dir, 'dist-eggs.ini' )
    def __init__( self, galaxy_config_file, build_on='all' ):
        self.dist_config = CaseSensitiveConfigParser()
        self.build_on = build_on
        ScrambleCrate.__init__( self, galaxy_config_file )
    def parse( self ):
        self.dist_config.read( DistScrambleCrate.dist_config_file )
        self.hosts = dict( self.dist_config.items( 'hosts' ) )
        self.groups = dict( self.dist_config.items( 'groups' ) )
        self.ignore = dict( self.dist_config.items( 'ignore' ) )
        self.platforms = self.get_platforms( self.build_on )
        self.noplatforms = self.get_platforms( 'noplatform' )
        Crate.parse( self )
    def get_platforms( self, wanted ):
        # find all the members of a group and process them
        if self.groups.has_key( wanted ):
            platforms = []
            for name in self.groups[wanted].split():
                for platform in self.get_platforms( name ):
                    if platform not in platforms:
                        platforms.append( platform )
            return platforms
        elif self.hosts.has_key( wanted ):
            return [ wanted ]
        else:
            raise Exception( "unknown platform: %s" % wanted )
    def parse_egg_section( self, eggs, tags, full_platform=False ):
        for name, version in eggs:
            self.eggs[name] = []
            tag = dict( tags ).get( name, '' )
            url = '/'.join( ( self.repo, name ) )
            try:
                sources = self.config.get( 'source', name ).split()
            except:
                sources = []
            try:
                dependencies = self.config.get( 'dependencies', name ).split()
            except:
                dependencies = []
            if full_platform:
                platforms = self.platforms
            else:
                platforms = self.noplatforms
            for platform in platforms:
                if name in self.ignore and platform in self.ignore[name].split():
                    continue
                egg = DistScrambleEgg( name, version, tag, url, platform, self )
                host_info = self.hosts[platform].split()
                egg.build_host, egg.python = host_info[:2]
                egg.sources = sources
                egg.dependencies = dependencies
                self.eggs[name].append( egg )
