import logging, threading, time
from Queue import Queue, Empty

from galaxy import config, util, model, tools, jobs

log = logging.getLogger( __name__ )

# This class is designed to provide job dispatch fairness for Galaxy users. It uses a 
# dictionary of session (key) Queue (value) pairs to ensure no user (session)
# can hog the Galaxy run queue.
# Each get() call will return a job from a consecutive session
# in the dict or throw an Empty exception if there are no jobs in any queue
class UserRoundRobin( object ):
    """
    Class UserRoundRobin provides per-user job scheduling fairness. It uses a dictionary of session-Queue() pairs
    to ensure no user/session can hog the Galaxy run queue. Each get() call will either return a job from a consecutive session
    in the dict or throw an Empty exception if the dict has no jobs in any queues.
    """
    # private: dictionary of queues (its not really private in Python)
    __DOQ = {} 
    
    def __init__(self, app):
    	self.app = app
        self.__DOQ = {}
        self.keylist = []
        self.iterator = None
        # these are used to decide when to do a DOQ cleanup
        self.cleanup_tstamp = time.time()
        # get from ini/config and convert to secs
        self.cleanup_mininterval = self.app.config.job_queue_cleanup_interval * 60 
        # Don't allow cleanup interval less than 5 minutes (should this be hardcoded ?)
        if self.cleanup_mininterval < 300 :
            self.cleanup_mininterval = 300
        # locks for get and put methods
        self.putlock = threading.Lock() 
        self.getlock = threading.Lock()
        log.info("RoundRobin policy: initialized ")

    # Insert a job in the dict of queues
    def put(self, job): 
        self.putlock.acquire()
        try :
            # get this job's user/session id
            sessid = job.get_session_id()
            # Check if a queue already exists for user/session and add one if not
            if self.__DOQ.has_key(sessid) :
                self.__DOQ[sessid].put(job)
                log.debug("RoundRobin queue: inserted new job for user/session = %d" % sessid)
            else :
                self.__DOQ[sessid] = Queue()
                self.__DOQ[sessid].put(job)
                log.debug("RoundRobin queue: user/session did not exist, created new jobqueue for session = %d" % sessid)
        finally :
            self.putlock.release()

    # Return a job from the dictionary of queues. Each get() call tries to
    # return a job from another queue in the dictionary . 
    # Throws Empty if it cant find any jobs in the dictionary of queues
    # This method also does a cleanup of the dict regularly (specified)
    def get(self) :
        self.getlock.acquire()
        try :
            # get the next user/session in the dict
            sessionid = self.__get_next_session()
            if sessionid is not None :
                log.debug("RoundRobin queue: retrieving job from job queue for session = %d" % sessionid)        
                return self.__DOQ[sessionid].get()
            else :               
                # sessionid = None implies empty dictionary, throw back to caller
                raise Empty
        finally :
            # Clean up DOQ
            self.__timed_clean_up() #cleanup will happen at specified intervals
            self.getlock.release()
            

   # In case the Queue.get_nowait() method is used somewhere
    def get_nowait(self):
        return self.get()
    
    # Returns the total number of jobs in the dict (counts all queues)
    # Locks the get() and put() methods during calculation.
    # Analogous to qsize() in Queue.Queue. Not guaranteed to be correct
    def qsize(self):
        try :
            count = 0
            self.getlock.acquire()
            self.putlock.acquire()
            for sessid in self.__DOQ :
                count += self.__DOQ[sessid].qsize()
            return count
        finally :
            self.putlock.release()            
            self.getlock.release()
            
    # Internal method - get the next user/session (key) from any nonempty queue in the dict.
    # Returns None if dictionary is empty.
    # Note: We use a separate list to hold the DOQ keys and create an iterator from this list
    # because an iterator created directly from DOQ barfs if DOQ size changes while iterating
    def __get_next_session(self): 
        try:
            # Check if this is either startup or previous iteration ended
            if self.iterator is None :
                self.keylist = self.__DOQ.keys()
                self.iterator = iter(self.keylist)
            # get the first available job from any nonempty queue
            while 1 :
                tmpsid = self.iterator.next()
                if not self.__DOQ[tmpsid].empty() :
                    break
            return tmpsid
        except StopIteration :
            # StopIteration implies we hit the end of the dict.
            # re-initalize iterator, start from beginning (can we improve this ?)
            try:
                self.keylist = self.__DOQ.keys()
                self.iterator = iter(self.keylist)
                 # get the first available job from any nonempty queue
                while 1 :
                    tmpsid = self.iterator.next()
                    if not self.__DOQ[tmpsid].empty() :
                        break
                return tmpsid
            except StopIteration :
                # this 2nd exception means there are no users queues at this moment
                # returning None implies DOQ is empty
                log.debug("RoundRobin queue: there are no user queues at this time")
                self.iterator = None # this will cause the iterator to be recreated next call
                return None
 
 
    # Cleanup method. Does a timestamp check to see if the preset minutes
    # have passed and does a dict cleanup.
    def __timed_clean_up(self):
        # Note: Here again, we first create a temp list of keys from DOQ and 
        # then an iterator from the temp list because an iterator from DOQ breaks
        # when deleting entries.
        tmp_tstamp = time.time()
        if ( (tmp_tstamp - self.cleanup_tstamp) >
                                        self.cleanup_mininterval ) :
            tmpkeylist = self.__DOQ.keys()
            for each in tmpkeylist :
                if self.__DOQ[each].empty() :
                    del(self.__DOQ[each])
                    log.debug("RoundRobin queue clean up: Removed job queue entry from dictionary for session = %d" % each)
            self.cleanup_tstamp = tmp_tstamp
