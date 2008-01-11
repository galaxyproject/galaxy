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
        df_file = os.popen( df_cmd )
        is_sym_link = os.path.islink( file_path )

        while True:
            df_list = df_file.readline().strip()
            if not df_list:
                break #EOF
            dflistlower = df_list.lower()
            if 'filesystem' in dflistlower or 'proc' in dflistlower:
                continue
            if is_sym_link:
                if '/' in dflistlower:
                    mount = dflistlower.strip()
                    continue
                else:
                    file_system, disk_size, disk_used, disk_avail, disk_cap_pct = df_list.split()
            else:
                file_system, disk_size, disk_used, disk_avail, disk_cap_pct, mount = df_list.split()
            break

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

