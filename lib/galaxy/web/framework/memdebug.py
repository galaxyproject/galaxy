"""
Implementation of WebApplication that logs memory usage before and after
calling each controller method.
"""

import pkg_resources
pkg_resources.require( "PSI" )
import psi.process

import os
import logging

from galaxy.web.framework import WebApplication

log = logging.getLogger( __name__ )
pid = os.getpid()

class MemoryLoggingWebApplication( WebApplication ):    
    def call_body_method( self, method, trans, kwargs ):
        cls = method.im_class
        process = psi.process.Process( pid )
        log.debug( "before controller=%s.%s method=%s rss=%d vsz=%d", cls.__module__, cls.__name__, method.__name__, process.rss, process.vsz )
        rval = method( trans, **kwargs )
        process = psi.process.Process( pid )
        log.debug( "after controller=%s.%s method=%s rss=%d vsz=%d", cls.__module__, cls.__name__, method.__name__, process.rss, process.vsz )
        return rval