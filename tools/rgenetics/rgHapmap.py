## fiddle with hapmap data dump calls
## tool to download hapmap genotypes
## the hapmap extract format has markers as rows, subjects as cols
## works for haploview and some other programs, but probably
## need another tool to convert into ped file...
## june 17 2007
## ross lazarus with help from
##Hi Ross,
##
##Dunno about the xml-rpc call, but here's a URL to call the genotype
##download plugin :
##http://www.hapmap.org/cgi-perl/gbrowse//hapmap_B35/?plugin=SNPMultipopGenotypeDataDumper;plugin_do=Go
##
##Hope this helps,
##
##Lalitha Krishnan
##Cold Spring Harbor Labs.

uproto = ['http://hapmap.org/cgi-perl/gbrowse/hapmap20_B%d/?plugin=SNPMultipopGenotypeDataDumper;plugin_config=1;plugin_do=Go',
         'SNPMultipopGenotypeDataDumper.pop_code=%s','start=%d', 'stop=%d', 'ref=chr%s','width=800','version=100']
suproto = '&'.join(uproto) # trick to leave ; seps in first parameter

import urllib,sys


def makeHapmapURLborked(build=35,start=1000000,stop=2000000,chrom='4',pop='YRI'):
    """construct and retrieve a hapmap dataset from the web site
    doing it the "right" way doesn't seem to work!
    """
    hmu = 'http://hapmap.org/cgi-perl/gbrowse/hapmap20_B%d/' % build
    pdict = {'plugin':'SNPMultipopGenotypeDataDumper;plugin_config=1;plugin_do=Go','start':start,
             'stop':stop,'ref':'chr%s' % chrom,'width':'800','version':'100'}
    params = urllib.urlencode(pdict)
    hm = urllib.urlopen(hmu,params)
    res = hm.readlines()
    return res

def makeHapmapURL(build=35,start=1000000,stop=2000000,chrom='4',pop='YRI',outf=None):
    """construct and retrieve a hapmap dataset from the web site
    note that doing this "right" with urlencode doesn't work as the perl cgi
    really does want ';' characters AFAIK
    """
    u = suproto % (build,pop,start,stop,chrom)
    hm = urllib.urlopen(u)
    if outf == None:
       res = hm.readlines()
       return res
    else:
       res = hm.read()
       f = open(outf,'w')
       f.write(res)
       f.close()

def test():
    """
    """
    res = makeHapmapURL()
    print 'got %d lines' % len(res)
    print res[:50]


if __name__=="__main__":
    """call as rgHapmap.py $start $stop $chrom $race $build $outf 
    """
    if len(sys.argv) >= 6:
        start=int(sys.argv[1])
        stop=int(sys.argv[2])
        chrom=sys.argv[3]
        pop=sys.argv[4]
        build=int(sys.argv[5])
        outf = sys.argv[6]
        res = makeHapmapURL(build=build,start=start,stop=stop,chrom=chrom,pop=pop,outf=outf)
    else:
        test()

