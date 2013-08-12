def intor(x):
   try:
     y = [int(x[9]), int(x[10])]
   except:
     y = [x[9],x[10]]
   return y

f = open('HumanHap550v3_A.csv','r')
outf = open('HumanHap550v3_A.xls','w')
res = []
n = 0
for l in f:
   n += 1
   if n > 8:
     ll = l.split(',')
     if len(ll) > 12:
       res.append(ll)
res.sort(key = intor)
outf.write(''.join(['\t'.join(x) for x in res]))
tf = file('illHH550v3.BED','w')
tres = []
sdict = {'BOT':'-','TOP':'+','':'+'}
#tres.append('track name="Ill550v3" description="Illumina HumanHap 550 chip v3 SNPs" visibility="2" itemRgb="On"')
for r in res:
    l = []
    chrom = r[9]
    if len(chrom) < 3:
        strand = sdict[r[15].upper()]
        try:
	    epos = '%d' % (int(r[10]) + 1)	
        except:
            print 'bad epos - r[10]=',r[10]
            epos = r[10]
        tres.append('chr%s\t%s\t%s\t%s\t0\t%s\t%s\t%s\t255,0,0' % (chrom,r[10],epos,r[1],strand,r[10],epos))
tres.append('')
tf.write('\n'.join(tres))

