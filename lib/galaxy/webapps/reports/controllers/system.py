import sys, sets, string, shutil
import re, socket

from galaxy import web

from cgi import escape, FieldStorage
import urllib

import operator, os
from galaxy.webapps.reports.base.controller import *

import logging, sets, time
log = logging.getLogger( __name__ )

class System( BaseController ):

    def get_disk_usage( self, file_path ):
        df_cmd = 'df -h ' + file_path
        is_sym_link = os.path.islink( file_path )
        file_system = disk_size = disk_used = disk_avail = disk_cap_pct = mount = None
        df_file = os.popen( df_cmd )

        while True:
            df_line = df_file.readline()
            df_line = df_line.strip()
            #log.debug("df_line: '%s'" %df_line)
            if df_line:
                df_line = df_line.lower()
                if 'filesystem' in df_line or 'proc' in df_line:
                    continue
                elif is_sym_link:
                    #log.debug("We have a symlink...")
                    if ':' in df_line and '/' in df_line:
                        mount = df_line
                        #log.debug("mount: '%s'" %mount)
                    else:
                        try:
                            disk_size, disk_used, disk_avail, disk_cap_pct, file_system = df_line.split()
                            break
                        except:
                            #log.debug("In symlink try, df_line: '%s'" %df_line)
                            pass
                else:
                    try:
                        file_system, disk_size, disk_used, disk_avail, disk_cap_pct, mount = df_line.split()
                        break
                    except:
                        #log.debug("In 2nd try, df_line: '%s'" %df_line)
                        pass
            else:
                break # EOF

        df_file.close()
        return ( file_system, disk_size, disk_used, disk_avail, disk_cap_pct, mount  )


    @web.expose
    def disk_usage( self, trans, **kwd ):
        file_path = trans.app.config.file_path
        disk_usage = self.get_disk_usage( file_path )
        min_file_size = 2**40 # 1 GB
        file_size_str = '1 GB'
        datasets = []
        dt = trans.model.Dataset.table

        for row in dt.select( dt.c.file_size>min_file_size ).execute():
            datasets.append( ( row.id, str( row.create_time )[0:10], row.history_id, row.deleted, row.file_size ) )

        datasets = sorted( datasets, key=operator.itemgetter(4), reverse=True )
        return trans.fill_template('disk_usage.tmpl', file_path=file_path, disk_usage=disk_usage, datasets=datasets, file_size_str=file_size_str)

