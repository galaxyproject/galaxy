from galaxy import eggs
import pkg_resources
pkg_resources.require("SQLAlchemy >= 0.4")
pkg_resources.require("MySQL_python")
from sqlalchemy import *


engine = create_engine( 'mysql://anonymous@ensembldb.ensembl.org:5306', pool_recycle=3600 )
conn = engine.connect()
dbs = conn.execute( "SHOW DATABASES LIKE 'ensembl_website_%%'" )
builds = {}
lines = []
for res in dbs:
    dbname = res[0]
    release = dbname.split('_')[-1]
    genomes = conn.execute( "SELECT RS.assembly_code, S.name, S.common_name, %s FROM ensembl_website_%s.release_species RS LEFT JOIN ensembl_website_%s.species S on RS.species_id = S.species_id" % ( release, release, release ) )
    for genome in genomes:
        builds[genome[0]] = dict( release=genome[3], species='%s (%s/%s)' % ( genome[1], genome[2], genome[0] ) )
for build in builds.items():
    lines.append( '\t'.join( [ build[0], '%d' % build[1]['release'], build[1]['species'] ] ) )
    
print '\n'.join( lines )