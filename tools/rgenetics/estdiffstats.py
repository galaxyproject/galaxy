


import math,copy,os


def main(fname = '/home/rerla/Downloads/Galaxy28-[HT100_K562_differential_results.xls'):
    """ two passes so we can estimate percentiles and estimate a kind of fisher's independent combined
    p value
    """
    dat = open(fname,'r').readlines()
    dhead = dat[0].strip().split('\t')
    dat = dat[1:]
    dat = [x.split() for x in dat if len(x.split()) > 0]
    conts=[]
    treats=[]
    for index,row in enumerate(dat): # header
       cont = row[5]
       treat = row[6]
       conts.append((float(cont),index))
       treats.append((float(treat),index)) # so can recover row
    conts.sort()
    conts.reverse()
    treats.sort()
    treats.reverse()
    treats = [(rank,x[0],x[1]) for rank,x in enumerate(treats)]
    conts = [(rank,x[0],x[1]) for rank,x in enumerate(conts)]
    tdict = dict(zip([x[2] for x in treats],treats)) # decorate so can lookup a data row
    cdict = dict(zip([x[2] for x in conts],conts)) # decorate so can lookup a data row
    res = []
    n = float(len(dat) - 1)
    for dindex in range(len(dat)): # dindex = record in d
       if dindex % 10000 == 0:
           print dindex
       treati,treat,tindex = tdict.get(dindex,(0,0,0))
       conti,cont,cindex = cdict.get(dindex,(0,0,0))
       crank = conti/n
       trank = treati/n
       try:
           logfold = math.log(treat/cont,2)
       except:
           print 'bad logfold treat=%f cont=%f' % (treat,cont)
           logfold = 0

       logA = math.log(treat+cont,2)
       try:
           logM = math.log(abs(treat-cont),2)
       except:
           print 'bad logM treat=%f cont=%f' % (treat,cont)
           logM = 0
       try:
           fish = -2.0*(math.ln(crank) + math.ln(trank))
       except:
           print "bad fisher's combined crank=%f trank=%f" % (crank,trank)
           fish = 0
       row = copy.copy(dat[dindex])
       row += ['%i' % conti, '%i' % treati,'%f' % logfold,'%f' % logA,
        '%f' % logM,'%f' % crank,'%f' % trank,'%f' % fish]
       res.append('\t'.join(row))
    h = copy.copy(dhead)
    h += ['conti','treati','logfold','logA','logM','crank','trank','fakefishers']
    res.insert(0,h)
    outfname = '%s_fixed.xls' % fname
    outf = open(outfname,'w')
    outf.write('\n'.join(res))
    outf.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        fname = sys.argv[1]
        assert os.path.isfile(fname)
        main(fname=fname)
    else:
        main()