'''
Created on 16/07/2014

@author: Andrew Robinson
'''

import traceback
import galaxy.customauth.base

class LocalDB(galaxy.customauth.base.CustomAuthProvider):
    '''Checks against local DB (as per usual)'''
    
    def authenticate(self, username, password, options, debug=False):
        '''
        Check the username and password are correct.
        
        NOTE: Used within auto-registration to check its ok to register this user
         
        @param username: the users email address
        @param password: the plain text passord they typed
        @param options: dictionary of options provided by admin in customauth xml config file
        @param debug: boolean, False indicating admin wants debugging information printed
        @return: (boolean, str), True: accept user, False: reject user and None: reject user and don't try any other providers.  str is the username to register with if accepting.
        '''
        
        return (False, '') # it can never auto-create based of localdb (chicken-egg)
    
    def authenticateUser(self, user, password, options, debug=False):
        '''
        Same as authenticate, except User object is provided instead of username.
        
        NOTE: used on normal login to check authentication and update user details if required.
         
        @param username: the users email address
        @param password: the plain text passord they typed
        @param options: dictionary of options provided by admin in customauth xml config file
        @param debug: boolean, False indicating admin wants debugging information printed
        @return: boolean, True: accept user, False: reject user and None: reject user and don't try any other providers
        '''
        
        user_ok = user.check_password(password)
        if debug:
            print ("User: %s, LOCALDB: %s" % (user.email, user_ok))
        return user_ok
