"""
process_NCBI_taxonomy.py <gi2tax.txt file> <name.txt> <database_name>
"""

import pkg_resources
pkg_resources.require( 'pysqlite' )
from pysqlite2 import dbapi2 as sqlite
import string, sys, tempfile

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


try:
    gi2tax  = open(sys.argv[1], 'r')
    names   = open(sys.argv[2], 'r')
    db_name = sys.argv[3]
except:
    stop_err('Check arguments: process_NCBI_taxonomy.py <gi2tax.txt file> <name.txt> <database_name>\n')
    
    
try:
    con = sqlite.connect(db_name)
    cur = con.cursor()
    cur.execute('create table gi2tax(gi int unsigned not null, taxId int unsigned not null)')
    cur.execute('create table t_names(taxId int unsigned not null, name text not null)')
    cur.execute('create table names(taxId int unsigned not null, name text not null)')
    
    for line in gi2tax:
        fields = string.split(line.rstrip(), '\t')
        cur.execute('insert into gi2tax values(%s, %s)' % ( fields[0], fields[1] ) )
        
    gi2tax.close()
    
    for line in names:
        fields = string.split(line.rstrip(), '\t')
        cur.execute('insert into t_names values(%s, "%s")' % ( fields[0], fields[1] ) )
        
    names.close()
    
    cur.execute('create index gi_i on gi2tax(gi)')
    cur.execute('insert into names select * from t_names group by name')
    cur.execute('drop table t_names')
    cur.execute('create index name_i on names(name)')
    cur.execute('vacuum')
    con.commit()
    con.close() 
except Exception, e:
    stop_err("%s\n" % e)
