"""
Database functionality.
"""    

import sys, logging, os, shelve, sys, threading, whichdb

log = logging.getLogger( __name__ )

class Database( object ):
    def __init__( self, db_fname, flag='c' ):
        """Wrapper for an object database with a secondary on disk storage"""
        self.lock = threading.RLock()
        self.shelf = self.open_db( db_fname, flag )
    def open_db( self, fname, flag ):
        """Open the database, return a dictionary like object"""
        shelf = None
        # Some shelve implementations cannot be reopened
        if not os.path.isfile( fname ):
            shelf = shelve.open(filename=fname, flag=flag, protocol=2)
            shelf.close()
        dbtype = whichdb.whichdb( fname )
        #log.info( 'database type: %s', dbtype )
        shelf = shelve.open(filename=fname, flag=flag, protocol=2)
        return shelf
    def store( self, obj ):
        """Stores an object in the database"""
        self.lock.acquire( True ) # Wait
        try:
            self.shelf[obj.id] = obj
        finally:
            self.lock.release()    
    def delete( self, id ):
        """Deletes an object from the database"""
        try:
            self.lock.acquire( True ) # Wait
            try:
                del self.shelf[id]
            except:
                log.exception( 'Database delete error for key %s', id )
        finally:
            self.lock.release()
    def get( self, id):
        """Gets an object from the database"""
        try:
            self.lock.acquire( True ) # Wait
            return self.shelf.get( str(id), None )
        finally:
            self.lock.release()
    def get_list( self, id_list ):
        """Gets multiple objects from the database"""
        try:
            self.lock.acquire( True ) # Wait
            return [ self.shelf.get( id, None ) for id in id_list ]
        finally:
            self.lock.release()
    def keys( self ):
        """Returns the keys of the database"""
        try:
            self.lock.acquire( True ) # Wait
            return self.shelf.keys()
        finally:
            self.lock.release()
    def values( self ):
        """Returns the keys of the database"""
        try:
            self.lock.acquire( True ) # Wait
            return self.shelf.values()
        finally:
            self.lock.release()
    def items( self ):
        """Returns the keys of the database"""
        try:
            self.lock.acquire( True ) # Wait
            return self.shelf.items()
        finally: 
            self.lock.release()
    def sync( self ):
        """Synchronizes the database state with its file representation. Not needed for berkleydb."""
        try:
            self.lock.acquire( True ) # Wait
            self.shelf.sync()
        finally:
            self.lock.release()