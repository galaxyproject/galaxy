#!/usr/bin/env python

"""
tax_read_grouping.py <file in taxonomy format> <id column> <taxonomic ranks> <output format> <output file>
    finds reads that only hit one taxonomic group. For example, consider the folliowing example:
    
    read1   mammalia
    read1   insecta
    read2   insecta
    
    in this case only read2 will be selected becuase it stays within insecta
    
    This program takes the following options:
    
    file in taxonomy format - dataset that complies with Galaxy's taxonomy format
    id column               - integer specifying the number of column containing seq id (starting with 1)
    taxonomic ranks         - a comma separated list of ranks from this list:
    
         superkingdom
         kingdom
         subkingdom
         superphylum
         phylum
         subphylum
         superclass
         class
         subclass
         superorder
         order
         suborder
         superfamily
         family
         subfamily
         tribe
         subtribe
         genus
         subgenus
         species
         subspecies
    
    output format           - reads or counts

"""

from galaxy import eggs
import pkg_resources
pkg_resources.require( 'pysqlite' )
from pysqlite2 import dbapi2 as sqlite
import string, sys, tempfile

# This dictionary maps taxonomic ranks to fields of Taxonomy file
taxRank = {
        'root'        :2, 
        'superkingdom':3, 
        'kingdom'     :4, 
        'subkingdom'  :5, 
        'superphylum' :6, 
        'phylum'      :7, 
        'subphylum'   :8, 
        'superclass'  :9, 
        'class'       :10, 
        'subclass'    :11, 
        'superorder'  :12, 
        'ord'         :13, 
        'suborder'    :14, 
        'superfamily' :15,
        'family'      :16,
        'subfamily'   :17,
        'tribe'       :18,
        'subtribe'    :19,
        'genus'       :20,
        'subgenus'    :21,
        'species'     :22,
        'subspecies'  :23,
        'order'       :13
    }


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


db = tempfile.NamedTemporaryFile('w')

try:
    con = sqlite.connect(db.name)
    cur = con.cursor()
except:
    stop_err('Cannot connect to %s\n') % db.name
    
try:
    tax_file   = open(sys.argv[1], 'r')
    id_col     = int(sys.argv[2]) - 1
    taxa       = string.split(sys.argv[3].rstrip(),',')
    
    if sys.argv[4] == 'reads':
        out_format = True
    elif sys.argv[4] == 'counts':
        out_format = False
    else:
        stop_err('Please specify "reads" or "counts" for output format\n')
    out_file = open(sys.argv[5], 'w')
    
except:
    stop_err('Check arguments\n')
    
if taxa[0] == 'None': stop_err('Please, use checkboxes to specify taxonomic ranks.\n')

sql = ""
for i in range(len(taxa)):
        if taxa[i] == 'order': taxa[i] = 'ord' # SQL does not like fields to be named 'order'
        sql += '%s text, ' % taxa[i]

sql = sql.strip(', ')
sql = 'create table tax (name varchar(50) not null, ' + sql + ')'

    
cur.execute(sql)

invalid_line_number = 0

try:
    for line in tax_file:
        fields = string.split(line.rstrip(), '\t')
        if len(fields) < 24: 
            invalid_line_number += 1
            continue # Skipping malformed taxonomy lines
        
        val_string = '"' + fields[id_col] + '", '
        
        for rank in taxa:
            taxon = fields[taxRank[rank]]
            val_string += '"%s", ' % taxon
                
        val_string = val_string.strip(', ')
        val_string = "insert into tax values(" + val_string + ")"
        cur.execute(val_string)
except Exception, e:
    stop_err('%s\n' % e)

tax_file.close()    

try:    
    for rank in taxa:
        cur.execute('create temporary table %s (name varchar(50), id text, rank text)' % rank  )
        cur.execute('insert into %s select name, name || %s as id, %s from tax group by id' % ( rank, rank, rank ) )
        cur.execute('create temporary table %s_count(name varchar(50), id text, rank text, N int)' % rank)
        cur.execute('insert into %s_count select name, id, rank, count(*) from %s group by name' % ( rank, rank) )
        
        if rank == 'ord':
            rankName = 'order'
        else:
            rankName = rank
    
        if out_format:
            cur.execute('select name,rank from %s_count where N = 1 and length(rank)>1' % rank)
            for item in cur.fetchall():
                out_string = '%s\t%s\t' % ( item[0], item[1] )
                out_string += rankName
                print >>out_file, out_string
        else:
            cur.execute('select rank, count(*) from %s_count where N = 1 and length(rank)>1 group by rank' % rank)
            for item in cur.fetchall():
                out_string = '%s\t%s\t' % ( item[0], item[1] )
                out_string += rankName
                print >>out_file, out_string
except Exception, e:
    stop_err("%s\n" % e)
    
