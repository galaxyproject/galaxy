"""
    tax2_Node2Name.py <node2child_file> <names_file> <db_name> 
    
    adds taxonomic names to collapsed NCBI taxonomy produced by tax1_NodeParser.py script
    
    node2child_file = created by tax1_NodeParser.py script
    names_file = created from names.dmp file with the following command:
    
    cat names.dmp | cut -f 1,2,4 -d "|" | tr -s "\t" "|"  | tr "|" "\t" | sed s/\"//g > names.txt
    (names.dmp is downloaded from NCBI taxonomy FTP site)
    
    db_name = a name of sqlite file this program will create.  Output of this script is stored in table names of this database
    
    anton nekrutenko | anton@bx.psu.edu
"""


import pkg_resources
pkg_resources.require('pysqlite')
from pysqlite2 import dbapi2 as sqlite
import sys
import string 

def main():
    
    try:
        inFileNodes  = sys.argv[1]
        inFileNames  = sys.argv[2]
        dbName       = sys.argv[3]
    except:
        sys.stderr.write('tax2_Node2Name.py <node2child_file> <names_file> <db_name>: Not enough arguments\n')
        sys.exit(0)

    taxRank = {
        'root'        :1, 
        'superkingdom':2, 
        'kingdom'     :3, 
        'subkingdom'  :4, 
        'superphylum' :5, 
        'phylum'      :6, 
        'subphylum'   :7, 
        'superclass'  :8, 
        'class'       :9, 
        'subclass'    :10, 
        'superorder'  :11, 
        'order'       :12, 
        'suborder'    :13, 
        'superfamily' :14,
        'family'      :15,
        'subfamily'   :16,
        'tribe'       :17,
        'subtribe'    :18,
        'genus'       :19,
        'subgenus'    :20,
        'species'     :21,
        'subspecies'  :22
    }
    
    con = sqlite.connect(dbName)
    cur = con.cursor()
    
    cur.execute('drop table if exists nodes')
    cur.execute('create table nodes (pid int unsigned not null, pidRank varchar(20) not null, pnumRank smallint unsigned not null, id int unsigned not null, idRank varchar(20), numRank smallint unsigned not null)')
    cur.execute('create index if not exists ipid on nodes(pid)')
    
    cur.execute('drop table if exists names')
    cur.execute('create table names (taxId int unsigned not null, name text, type text)')
    cur.execute('create index itaxId on names(taxId)')
    con.commit()
    
    f = open(inFileNodes, 'r')
    
    try:
        for line in f:
            field = string.split(line.rstrip(), '\t')
            field = [ int(field[0]), field[1], 0, int(field[2]), field[3], 0 ]
            
            
            # Changing taxId == 1 from 'no rank' to 'root'
                      
            if field[0] == 1:
                field[1] = 'root'

            # Setting numeric IDs for major taxonomic groups from taxRank dictionary    
            
            if taxRank.has_key(field[1]):
                field[2] = taxRank[field[1]]
            
            if taxRank.has_key(field[4]):
                field[5] = taxRank[field[4]]          
                 
            sqlTemplate = string.Template('insert into nodes values($pId, "$pRank", $pNumRank, $cId, "$cRank", $cNumRank)')
            sql = sqlTemplate.substitute(pId = field[0], pRank = field[1], pNumRank = field[2], cId = field[3], cRank = field[4], cNumRank = field[5])
            cur.execute(sql)
        
    finally:
        f.close()
        con.commit()
        
    f = open(inFileNames, 'r')
    try:
        for line in f:
            field = string.split(line.rstrip(), '\t')
            
#             The following is based on assimption that every tax id in NCBI taxonomy
#             contains a single 'scientific name' type
            try:
                if field[2] == 'scientific name':
                    field[1] = field[1].replace('\t','_')
                    sqlTemplate = string.Template('insert into names values($taxId, "$name", "$syn")')
                    sql = sqlTemplate.substitute(taxId = int(field[0]), name = field[1], syn = field[2])  
                    cur.execute(sql)
            except:
                pass
                
    finally:
        f.close()
        con.commit()
    
    cur.execute('drop table if exists t')
    
    cur.execute('create table t (pid int unsigned not null, pidRank varchar(20) not null, pnumRank smallint unsigned not null, id int unsigned not null, idRank varchar(20), numRank smallint unsigned not null, pName text)')
    
    cur.execute('insert into t select nodes.*, name from nodes left join names on pid = taxId')
    
    cur.execute('create index iid on t(id)')

    cur.execute('drop table nodes')
    
    cur.execute('drop table if exists node2name')

    cur.execute('create table node2name (pId int unsigned not null, pIdRank varchar(20) not null, pNumRank smallint unsigned not null, cId int unsigned not null, cIdRank varchar(20), cNumRank smallint unsigned not null, pName text, cName text)')
    
    cur.execute('insert into node2name select t.*, name from t left join names on id = taxId')
    
    cur.execute('drop table t')
    cur.execute('vacuum')        
    con.commit()
    con.close()
    

if __name__ == "__main__":
    main()       

