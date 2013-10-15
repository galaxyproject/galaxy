# for rgenetics - lped to pbed
# where to stop with converters
# pbed might be central
# eg lped/eigen/fbat/snpmatrix all to pbed
# and pbed to lped/eigen/fbat/snpmatrix ?
# that's a lot of converters
import sys,os,time,subprocess


prog = os.path.split(sys.argv[0])[-1]
myversion = 'Oct 10 2009'

galhtmlprefix = """<?xml version="1.0" encoding="utf-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta name="generator" content="Galaxy %s tool output - see http://getgalaxy.org" />
<title></title>
<link rel="stylesheet" href="/static/style/base.css" type="text/css" />
</head>
<body>
<div class="document">
"""

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))

def getMissval(inped=''):
   """
   read some lines...ugly hack - try to guess missing value
   should be N or 0 but might be . or -
   """
   commonmissvals = {'N':'N','0':'0','n':'n','9':'9','-':'-','.':'.'}
   try:
       f = file(inped,'r')
   except:
       return None # signal no in file
   missval = None
   while missval == None: # doggedly continue until we solve the mystery
        try:
          l = f.readline()
        except:
          break
        ll = l.split()[6:] # ignore pedigree stuff
        for c in ll:
            if commonmissvals.get(c,None):
               missval = c
               f.close()
               return missval
   if not missval:
       missval = 'N' # punt
   close(f)
   return missval

def rgConv(inpedfilepath,outhtmlname,outfilepath,plink):
    """
    """
    pedf = '%s.ped' % inpedfilepath
    basename = os.path.split(inpedfilepath)[-1] # get basename
    outroot = os.path.join(outfilepath,basename)
    missval = getMissval(inped = pedf)
    if not missval:
        print '### lped_to_pbed_converter.py cannot identify missing value in %s' % pedf
        missval = '0'
    cl = '%s --noweb --file %s --make-bed --out %s --missing-genotype %s' % (plink,inpedfilepath,outroot,missval)
    p = subprocess.Popen(cl,shell=True,cwd=outfilepath)
    retval = p.wait() # run plink




def main():
    """
    need to work with rgenetics composite datatypes
    so in and out are html files with data in extrafiles path
    <command interpreter="python">lped_to_pbed_converter.py '$input1/$input1.metadata.base_name'
    '$output1' '$output1.extra_files_path' '${GALAXY_DATA_INDEX_DIR}/rg/bin/plink'
    </command>
    """
    nparm = 4
    if len(sys.argv) < nparm:
        sys.stderr.write('## %s called with %s - needs %d parameters \n' % (prog,sys.argv,nparm))
        sys.exit(1)
    inpedfilepath = sys.argv[1]
    outhtmlname = sys.argv[2]
    outfilepath = sys.argv[3]
    try:
        os.makedirs(outfilepath)
    except:
        pass
    plink = sys.argv[4]
    rgConv(inpedfilepath,outhtmlname,outfilepath,plink)
    f = file(outhtmlname,'w')
    f.write(galhtmlprefix % prog)
    flist = os.listdir(outfilepath)
    s = '## Rgenetics: http://rgenetics.org Galaxy Tools %s %s' % (prog,timenow()) # becomes info
    print s
    f.write('<div>%s\n<ol>' % (s))
    for i, data in enumerate( flist ):
        f.write('<li><a href="%s">%s</a></li>\n' % (os.path.split(data)[-1],os.path.split(data)[-1]))
    f.write("</div></body></html>")
    f.close()



if __name__ == "__main__":
   main()
