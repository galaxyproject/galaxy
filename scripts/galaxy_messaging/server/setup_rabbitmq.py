#
# Configuration script for RabbitMQ in Galaxy
#
# Requirements:
# - set the rabbitmqctl_path variable in the 'galaxy_amqp' section in Galaxy config file
#
# Usage:
# $ python setup_rabbitmq.py <Galaxy config file>
#

import os, sys, csv, ConfigParser

def main( config_file ):
    try:
        config = ConfigParser.ConfigParser()
        config.read( config_file )
        rabbitmqctl_path = config.get( 'galaxy_amqp', 'rabbitmqctl_path' )
        username = config.get( 'galaxy_amqp', 'userid' )
        password = config.get( 'galaxy_amqp', 'password' )
        virtual_host = config.get( 'galaxy_amqp', 'virtual_host' )
    except Exception, e:
        print 'Fatal error:', str(e)
        sys.exit(1)
        
    cmd_list = [
                'add_user %s %s' % ( username, password ),
                'add_vhost %s' % virtual_host,
                'set_permissions -p %s %s ".*" ".*" ".*"' % ( virtual_host, username )
               ]
    
    for cmd in cmd_list:
        retval = os.system( rabbitmqctl_path + ' ' + cmd )
        if retval:
            print "Failed command: %s" % cmd
            sys.exit(1)
    
if __name__ == '__main__':
    main( sys.argv[1] )