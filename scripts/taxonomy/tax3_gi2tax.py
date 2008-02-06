""" 
    tax3_gi2tax.py <db_name> <gi2tax_file> 
    
    db_name = name of the database produced by tax2_Node2Name.py scriopt
    gi2tax_file = conactenation of gi_taxid_nucl.dmp and gi_taxid_prot.dmp downloaded from NCBI Taxonomy FTP site
        
"""
    

import pkg_resources
pkg_resources.require('pysqlite')
from pysqlite2 import dbapi2 as sqlite
import sys
import string 

def main():

    try:
        dbName       = sys.argv[1]
        inFileGIs    = sys.argv[2]
        con = sqlite.connect(dbName)
    except:
        sys.stderr.write('tax3_gi2tax.py <db_name> <gi2tax_file>: Not enough arguments of database does not exist\n')
        sys.exit(0)
    
    
    cur = con.cursor()
    
    try:
        cur.execute('select * from node2name limit 1')
    except:
        sys.stderr.write('Table node2name does not exist')
        sys.exit(0)
    cur.execute('drop table if exists gi2tax')
    cur.execute('create table gi2tax (gi int unsigned primary key, taxId int unsigned not null)')

    cur.execute('drop table if exists tax')
    cur.execute('create table tax (taxId int unsigned not null, tax text)')
    cur.execute('insert into tax values(0,"superkingdom,kingdom,subkingdom,superphylum,phylum,subphylum,superclass,class,subclass,superorder,order,suborder,superfamily,family,subfamily,tribe,subtribe,genus,subgenus,species,subspecies")')
        
    cur.execute('create index if not exists cId_index on node2name(cId)')
    con.commit()
    
    fg = open(inFileGIs, 'r')
    
    
    try:
        for line in fg:
            field = string.split(line.rstrip(), '\t')
            sqlTemplate = string.Template('insert into gi2tax values($gi, $taxId)') 
            sql = sqlTemplate.substitute(gi = int(field[0]), taxId = int(field[1]))
            cur.execute(sql)

    finally:
        con.commit()
        fg.close()
        
    cur.execute('select distinct taxId from gi2tax')
    
    for line in cur.fetchall():
        i = 0
        taxRank = ['n' for i in range(22)] # This number depends on the length of taxRank dictionary in tax2_Node2Name.py
        
        # select all parents of a given taxId 
        sqlTemplate = string.Template('select * from node2name where cId = $taxId and pNumRank > 0 order by pNumRank asc')
        sql = sqlTemplate.substitute(taxId = int(line[0]))
        cur.execute(sql)
        
        for item in cur.fetchall():
            taxRank[item[2]-1] = str(item[6])
            

        # select lowest ranking parent (with max pNumRank)        
        sqlTemplate = string.Template('select max(pNumRank) from node2name where cId = $taxId')
        sql = sqlTemplate.substitute(taxId = int(line[0]))
        cur.execute(sql)
        row = cur.fetchone()
        
        # Set the child of the lowest ranking parent as the lowest taxon for that taxId (e.g., species, subspecies etc.)
        
        try:
            sqlTemplate = string.Template('select * from node2name where cId = $taxId and pNumRank = $max_pNumRank')
            sql = sqlTemplate.substitute(taxId = int(line[0]), max_pNumRank = int(row[0]))
            cur.execute(sql)
            lowestRank = cur.fetchone()
            taxRank[int(lowestRank[5])-1] = str(lowestRank[7])
            taxonomyInfo = ",".join(taxRank)
        except:
            print "The following taxId was not found in taxonomy database: ", line[0]
            pass
            
        taxTemplate = string.Template('insert into tax values($taxId, "$taxInfo")')
        tax = taxTemplate.substitute(taxId = int(line[0]), taxInfo = taxonomyInfo)
        cur.execute(tax)
    
    cur.execute('create index taxId_index on tax(taxId)') 
    cur.execute('drop table if exists node2name')
    cur.execute('vacuum')
    con.commit()
    con.close()

if __name__ == "__main__":
    main()       
