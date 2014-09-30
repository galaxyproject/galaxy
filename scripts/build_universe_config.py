from ConfigParser import ConfigParser
from os import listdir
from os.path import join
from re import match
from sys import argv


def merge():
    "Merges all .ini files in a specified directory into ./universe.ini"
    if len(argv) < 2:
        message = "%s: Must specify directory to merge configuration files from." % argv[0]
        raise Exception(message)
    conf_directory = argv[1]
    conf_files = [f for f in listdir(conf_directory) if match(r'.*\.ini', f)]
    conf_files.sort()

    parser = ConfigParser()
    for conf_file in conf_files:
        parser.read([join(conf_directory, conf_file)])
    ## TODO: Expand enviroment variables here, that would
    ## also make Galaxy much easier to configure. 

    destination= "config/galaxy.ini"
    if len(argv) > 2:
        destination = argv[2]

    parser.write(open(destination, 'w'))

if __name__ == '__main__':
    merge()
