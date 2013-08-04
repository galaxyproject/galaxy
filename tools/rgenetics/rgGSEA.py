"""
April 2013
eeesh GSEA does NOT respect the mode flag!

Now realise that the creation of the input rank file for gsea needs to take the lowest p value for duplicate 
feature names. To make Ish's life easier, remove duplicate gene ids from any gene set to stop GSEA from 
barfing.

October 14 2012
Amazingly long time to figure out that GSEA fails with useless error message if any filename contains a dash "-"
eesh.

Added history .gmt source - requires passing a faked name to gsea 
Wrapper for GSEA http://www.broadinstitute.org/gsea/index.jsp
Started Feb 22 
Copyright 2012 Ross Lazarus
All rights reserved
Licensed under the LGPL

called eg as

#!/bin/sh
GALAXY_LIB="/data/extended/galaxy/lib"
if [ "$GALAXY_LIB" != "None" ]; then
    if [ -n "$PYTHONPATH" ]; then
        PYTHONPATH="$GALAXY_LIB:$PYTHONPATH"
    else
        PYTHONPATH="$GALAXY_LIB"
    fi
    export PYTHONPATH
fi

cd /data/extended/galaxy/database/job_working_directory/027/27311
python /data/extended/galaxy/tools/rgenetics/rgGSEA.py --input_tab "/data/extended/galaxy/database/files/033/dataset_33806.dat"  --adjpvalcol "5" --signcol "2"
--idcol "1" --outhtml "/data/extended/galaxy/database/files/034/dataset_34455.dat" --input_name "actaearly-Controlearly-actalate-Controllate_topTable.xls"
--setMax "500" --setMin "15" --nPerm "1000" --plotTop "20"
--gsea_jar "/data/extended/galaxy/tool-data/shared/jars/gsea2-2.0.12.jar"
--output_dir "/data/extended/galaxy/database/job_working_directory/027/27311/dataset_34455_files" --mode "Max_probe"
 --title " actaearly-Controlearly-actalate-Controllate_interpro_GSEA" --builtin_gmt "/data/genomes/gsea/3.1/IPR_DOMAIN.gmt"


"""
import optparse
import tempfile
import os
import sys
import subprocess
import time
import shutil
import glob
import math
import re

KEEPSELECTION = False # detailed records for selection of multiple probes

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))



def fix_subdir(adir,destdir):
    """ Galaxy wants everything in the same files_dir
    if os.path.exists(adir):
        for (d,dirs,files) in os.path.walk(adir):
            for f in files:
                sauce = os.path.join(d,f) 
                shutil.copy(sauce,destdir)   
    """

    def fixAffycrap(apath=''):
        """class='richTable'>RUNNING ES</th><th class='richTable'>CORE ENRICHMENT</th><tr><td class='lessen'>1</td>
        <td><a href='https://www.affymetrix.com/LinkServlet?probeset=LBR'>LBR</a></td><td></td><td></td><td>1113</td>
        <td>0.194</td><td>-0.1065</td><td>No</td></tr><tr><td class='lessen'>2</td><td>
        <a href='https://www.affymetrix.com/LinkServlet?probeset=GGPS1'>GGPS1</a></td><td></td><td></td><td>4309</td><td>0.014</td><td>-0.4328</td>
        <td>No</td></tr>
        """
        html = []
        try:
            html = open(apath,'r').readlines()       
        except:
             return html
        for i,row in enumerate(html):
            row = re.sub('https\:\/\/www.affymetrix.com\/LinkServlet\?probeset=',"http://www.genecards.org/index.php?path=/Search/keyword/",row)
            html[i] = row
        return html

    cleanup = False
    if os.path.exists(adir):
        flist = os.listdir(adir) # get all files created
        for f in flist:
           apath = os.path.join(adir,f)
           dest = os.path.join(destdir,f)
           if not os.path.isdir(apath):
               if os.path.splitext(f)[1].lower() == '.html':
                   html = fixAffycrap(apath)
                   fixed = open(apath,'w')
                   fixed.write('\n'.join(html))
                   fixed.write('\n')
                   fixed.close()
               if not os.path.isfile(dest):
                   shutil.copy(apath,dest)
           else:
               fix_subdir(apath,destdir)
        if cleanup:
            try:
                shutil.rmtree(path=adir,ignore_errors=True)
            except:
                pass



def getFileString(fpath, outpath):
    """
    format a nice file size string
    """
    size = ''
    fp = os.path.join(outpath, fpath)
    s = fpath
    if os.path.isfile(fp):
        n = float(os.path.getsize(fp))
        if n > 2**20:
            size = ' (%1.1f MB)' % (n/2**20)
        elif n > 2**10:
            size = ' (%1.1f KB)' % (n/2**10)
        elif n > 0:
            size = ' (%d B)' % (int(n))
        s = '%s %s' % (fpath, size) 
    return s

class gsea_wrapper:
    """
    GSEA java desktop client has a CL interface. CL can be gleaned by clicking the 'command line' button after setting up an analysis
    We don't want gsea to do the analysis but it can read .rnk files containing rows of identifiers and an evidence weight such as the signed t statistic from limma for differential expression
(vgalaxy)rlazarus@iaas1:~/public_html/idle_illumina_analysis$ cat gseaHumanREFSEQ.sh 
#!/bin/bash
for RNK in `ls *.rnk`
do
DIRNAME=${RNK%.*}
echo $DIRNAME
qsub -cwd -b y java -Xmx4096m -cp /data/app/bin/gsea2-2.07.jar xtools.gsea.GseaPreranked -gmx ../msigdb.v3.0.symbols.gmt -collapse true -mode Max_probe -norm meandiv 
-nperm 1000 -rnk $RNK -scoring_scheme weighted -rpt_label $RNK -chip ../RefSeq_human.chip -include_only_symbols true -make_sets true -plot_top_x 20 -rnd_seed timestamp 
-set_max 500 -set_min 15 -zip_report false -out gseaout/${DIRNAME} -gui false
done
    """
    
    def __init__(self,myName=None,opts=None):
        """ setup cl for gsea
        """
        self.idcol = 0
        self.signcol = 0
        self.adjpvalcol = 0
        self.progname=myName
        self.opts = opts
        remove_duplicates=False
        if not os.path.isdir(opts.output_dir):
            try:
                os.makedirs(opts.output_dir)
            except:
                print >> sys.stderr,'##Error: GSEA wrapper unable to create or find output directory %s. Stopping' % (opts.output_dir)
                sys.exit(1)
        fakeGMT = re.sub('[^a-zA-Z0-9_]+', '', opts.input_name) # gives a more useful title for the GSEA report
        fakeGMT = os.path.join(opts.output_dir,fakeGMT)
        fakeGMT = os.path.abspath(fakeGMT)
        fakeRanks = '%s.rnk' % fakeGMT
        if not fakeGMT.endswith('.gmt'):
            fakeGMT = '%s.gmt' % fakeGMT
        if opts.builtin_gmt and opts.history_gmt:
            newfile = open(fakeGMT,'w')
            subprocess.call(['cat',opts.builtin_gmt,opts.history_gmt],stdout=newfile)
            newfile.close()
        elif opts.history_gmt:
           subprocess.call(['cp',opts.history_gmt,fakeGMT])
        else:       
           subprocess.call(['cp',opts.builtin_gmt,fakeGMT])
        # remove dupes from each gene set
        gmt = open(fakeGMT,'r').readlines()
        gmt = [x for x in gmt if len(x.split('\t')) > 3]
        ugmt = []
        for i,row in enumerate(gmt):
            rows = row.rstrip().split('\t')
            gmtname = rows[0]
            gmtcomment = rows[1]
            glist = list(set(rows[2:]))
            newgmt = [gmtname,gmtcomment]
            newgmt += glist
            ugmt.append('\t'.join(newgmt))
        gmt = open(fakeGMT,'w')
        gmt.write('\n'.join(ugmt))
        gmt.write('\n')
        gmt.close()
        if opts.input_ranks:
            infname = opts.input_ranks
            rdat = open(opts.input_ranks,'r').readlines() # suck in and remove blank ids that cause gsea to barf rml april 10 2012
            rdat = [x.rstrip().split('\t') for x in rdat[1:]] # ignore head
            dat = [[x[0],x[1],x[1]] for x in rdat] 
            # fake same structure as input tabular file
            try:
                pvals = [float(x[1]) for x in dat]
                signs = [float(x[1]) for x in dat]
            except:
                print >> sys.stderr, '## error converting floating point - cannot process this input'
                sys.exit(99)
        else: # read tabular
            self.idcol = int(opts.idcol) - 1
            self.signcol = int(opts.signcol) - 1
            self.adjpvalcol = int(opts.adjpvalcol) - 1
            maxcol = max(self.idcol,self.signcol,self.adjpvalcol)
            infname = opts.input_tab
            indat = open(opts.input_tab,'r').readlines()
            dat = [x.rstrip().split('\t') for x in indat[1:]]
            dat = [x for x in dat if len(x) > maxcol]
            dat = [[x[self.idcol],x[self.adjpvalcol],x[self.signcol]] for x in dat] # reduce to rank form 
            pvals = [float(x[1]) for x in dat]
            outofrange = [x for x in pvals if ((x < 0.0) or (x > 1.0))]
            assert len(outofrange) == 0, '## p values outside 0-1 encountered - was that the right column for adjusted p value?'
            signs = [float(x[2]) for x in dat]
            outofrange = [i for i,x in enumerate(signs) if (not x) and (dat[i][self.signcol] <> '0')]
            bad = [dat[x][2] for x in outofrange] 
            assert len(outofrange) == 0, '## null numeric values encountered for sign - was that the right column? %s' % bad 
        ids = [x[0] for x in dat]
        res = []
        self.comments = []
        useme = []
        for i,row in enumerate(dat):
            if row[1].upper() != 'NA' and row[2].upper() != 'NA' and row[0] > '' :
                useme.append(i)
        lost = len(dat) - len(useme)
        if lost <> 0:
            newdat = [dat[x] for x in useme]
            del dat
            dat = newdat  
            print >> sys.stdout, '## %d lost - NA values or null id' % lost
        if remove_duplicates:
            uids = list(set(ids)) # complex procedure to get min pval for each unique id
            if len(uids) <> len(ids): # dupes - deal with mode
                print >> sys.stdout,'## Dealing with %d uids in %d ids' % (len(uids),len(ids))
                ures = {}
                for i,id in enumerate(ids):
                    p = pvals[i]
                    ures.setdefault(id,[])
                    ures[id].append((p,signs[i]))
                for id in uids:
                    tlist = ures[id]
                    tp = [x[0] for x in tlist]
                    ts = [x[1] for x in tlist]
                    if len(tp) == 1:
                        p = tp[0]
                        sign = ts[0]
                    else:
                        if  opts.mode == "Max_probe":
                            p = min(tp)
                            sign = ts[tp.index(p)]
                        else: # guess median - too bad if even count
                            tp.sort()
                            ltp = len(tp)
                            ind = ltp/2 # yes, this is wrong for evens but what if sign wobbles?
                            if ltp % 2 == 1: # odd
                                ind += 1 # take the median                            
                            p = tp[ind]
                            sign = ts[ind]
                        if KEEPSELECTION:
                              self.comments.append('## for id=%s, got tp=%s, ts=%s, chose p=%f, sign =%f'\
                                   % (id,str(tp),str(ts),p,sign))
                    if opts.input_ranks: # must be a rank file
                        res.append((id,'%f' % p))
                    else:
                        if p == 0.0:
                            p = 1e-99
                        try:
                            lp = -math.log10(p) # large positive if low p value
                        except ValueError:
                            lp = 0.0
                        if sign < 0:
                            lp = -lp # if negative, swap p to negative
                        res.append((id,'%f' % lp))
            else: # no duplicates
                for i,row in enumerate(dat):
                    (id,p,sign) = (row[0],float(row[1]),float(row[2]))
                    if opts.input_ranks: # must be a rank file
                        res.append((id,'%f' % p))
                    else:
                        if p == 0.0:
                            p = 1e-99
                        try:
                            lp = -math.log10(p) # large positive if low p value
                        except ValueError:
                            lp = 0.0
                        if sign < 0:
                            lp = -lp # if negative, swap p to negative
                        res.append((id,'%f' % lp))
        else:
            for i,row in enumerate(dat):
                (id,p,sign) = (row[0],float(row[1]),float(row[2]))
                if opts.input_ranks: # must be a rank file
                    res.append((id,'%f' % p))
                else:
                    if p == 0.0:
                        p = 1e-99
                    try:
                        lp = -math.log10(p) # large positive if low p value
                    except ValueError:
                        lp = 0.0
                    if sign < 0:
                        lp = -lp # if negative, swap p to negative
                    res.append((id,'%f' % lp))
        len1 = len(ids)
        len2 = len(res)
        delta = len1 - len2
        if delta <> 0:
            print >> sys.stdout,'NOTE: %d of %d rank input file %s rows deleted - dup, null or NA IDs, pvals or logFCs' % (delta,len1,infname)
        ranks = [(float(x[1]),x) for x in res] # decorate
        ranks.sort()
        ranks.reverse()
        ranks = [x[1] for x in ranks] # undecorate
        if opts.chip == '': # if mouse - need HUGO
             ranks = [[x[0].upper(),x[1]] for x in ranks]
             print >> sys.stdout, '## Fixed any lower case - now have',','.join([x[0] for x in ranks[:5]])
        ranks = ['\t'.join(x) for x in ranks]
        if len(ranks) < 2:
             print >> sys.stderr,'Input %s has 1 or less rows with two tab delimited fields - please check the tool documentation' % infname
             sys.exit(1)
        print '### opening %s and writing %s' % (fakeRanks,str(ranks[:10]))
        rclean = open(fakeRanks,'w')
        rclean.write('contig\tscore\n')
        rclean.write('\n'.join(ranks)) 
        rclean.write('\n')
        rclean.close()
        cl = []
        a = cl.append  
        a('java -Xmx32G -cp')
        a(opts.gsea_jar)
        a('xtools.gsea.GseaPreranked')
        a('-gmx %s' % fakeGMT) # ensure .gmt extension as required by GSEA - gene sets to use
        a('-gui false')    # use preranked file mode and no gui
        a('-make_sets true -rnd_seed timestamp') # more things from the GUI command line display
        a('-norm meandiv -zip_report false -scoring_scheme weighted')            # ? need to set these? 
        a('-rnk %s' % fakeRanks) # input ranks file symbol (the chip file is the crosswalk for ids in first column)
        a('-out %s' % opts.output_dir) 
        a('-set_max %s' % opts.setMax)
        a('-set_min %s' % opts.setMin)
        a('-mode %s' % opts.mode)
        if opts.chip > '':
           #a('-chip %s -collapse true -include_only_symbols true' % opts.chip)   
           a('-chip %s -collapse true' % opts.chip)   
        else:
           a("-collapse false") # needed if no chip 
        a('-nperm %s' % opts.nPerm)
        a('-rpt_label %s' % opts.title)
        a('-plot_top_x %s' % opts.plotTop)
        self.cl = cl
        self.comments.append('## GSEA command line:')
        self.comments.append(' '.join(self.cl))
        self.fakeRanks = fakeRanks
        self.fakeGMT = fakeGMT
     
    def grepIds(self):
        """
        """
        found = []
        allids = open(self.opts.input_ranks,'r').readlines()
        allids = [x.strip().split() for x in allids]
        allids = [x[0] for x in allids] # list of ids
        gmtpath = os.path.split(self.opts.fakeGMT)[0] # get path to all chip

    def run(self):
        """
        
        """
        tlog = os.path.join(self.opts.output_dir,"gsea_runner.log")
        sto = open(tlog,'w')
        x = subprocess.Popen(' '.join(self.cl),shell=True,stdout=sto,stderr=sto,cwd=self.opts.output_dir)
        retval = x.wait()
        sto.close()
        d = glob.glob(os.path.join(self.opts.output_dir,'%s*' % self.opts.title))
        if len(d) > 0:
            fix_subdir(d[0],self.opts.output_dir)       
        htmlfname = os.path.join(self.opts.output_dir,'index.html')     
        try:
            html = open(htmlfname,'r').readlines()
            html = [x.strip() for x in html if len(x.strip()) > 0]
            if len(self.comments) > 0:
                s = ['<pre>']
                s += self.comments
                s.append('</pre>')
                try:
                    i = html.index('<div id="footer">')
                except:
                    i = len(html) - 7 # fudge
                html = html[:i] + s + html[i:]
        except:
            html = []
            htmlhead = '<html><head></head><body>'
            html.append('## Galaxy GSEA wrapper failure')
            html.append('## Unable to find index.html in %s - listdir=%s' % (d,' '.join(os.listdir(self.opts.output_dir))))
            html.append('## Command line was %s' % (' '.join(self.cl)))
            html.append('## commonly caused by mismatched ID/chip selection')
            glog = open(os.path.join(self.opts.output_dir,'gsea_runner.log'),'r').readlines()
            html.append('## gsea_runner.log=%s' % '\n'.join(glog))
            #tryme = self.grepIds()
            retval = 1
            print >> sys.stderr,'\n'.join(html)
            html = ['%s<br/>' % x for x in html]
            html.insert(0,htmlhead)
            html.append('</body></html>')
        htmlf = file(self.opts.outhtml,'w')
        htmlf.write('\n'.join(html))
        htmlf.write('\n')
        htmlf.close()
        os.unlink(self.fakeRanks)
        os.unlink(self.fakeGMT)
        if opts.outtab_neg:
            tabs = glob.glob(os.path.join(opts.output_dir,"gsea_report_for_*.xls"))
            if len(tabs) > 0:
                for tabi,t in enumerate(tabs):
                    tkind = os.path.basename(t).split('_')[4].lower()
                    if tkind == 'neg':
                       outtab = opts.outtab_neg
                    elif tkind == 'pos':
                       outtab = opts.outtab_pos
                    else:
                       print >> sys.stderr, '## tab file matched %s which is not "neg" or "pos" in 4th segment %s' % (t,tkind)
                       sys.exit()
                    content = open(t).readlines()
                    tabf = open(outtab,'w')
                    tabf.write(''.join(content))
                    tabf.close()
            else:
                print >> sys.stdout, 'Odd, maketab = %s but no matches - tabs = %s' % (makeTab,tabs)
        return retval
        

if __name__ == "__main__":
    """ 
    called as:
   <command interpreter="python">rgGSEA.py --input_ranks "$input1"  --outhtml "$html_file"
       --setMax "$setMax" --setMin "$setMin" --nPerm "$nPerm" --plotTop "$plotTop" --gsea_jar "$GALAXY_DATA_INDEX_DIR/shared/jars/gsea2-2.07.jar" 
       --output_dir "$html_file.files_path" --use_gmt ""${use_gmt.fields.path}"" --chip "${use_chip.fields.path}"
  </command>
    """
    op = optparse.OptionParser()
    a = op.add_option
    a('--input_ranks',default=None)
    a('--input_tab',default=None)
    a('--input_name',default=None)
    a('--use_gmt',default=None)
    a('--history_gmt',default=None)
    a('--builtin_gmt',default=None)
    a('--history_gmt_name',default=None)
    a('--setMax',default="500")
    a('--setMin',default="15")
    a('--nPerm',default="1000") 
    a('--title',default="GSEA report") 
    a('--chip',default='')
    a('--plotTop',default='20')
    a('--outhtml',default=None)
    a('--makeTab',default=None)
    a('--output_dir',default=None)
    a('--outtab_neg',default=None)
    a('--outtab_pos',default=None)
    a('--adjpvalcol',default=None)
    a('--signcol',default=None)
    a('--idcol',default=None)
    a('--mode',default='Max_probe')
    a('-j','--gsea_jar',default='/usr/local/bin/gsea2-2.07.jar')
    opts, args = op.parse_args() 
    assert os.path.isfile(opts.gsea_jar),'## GSEA runner unable to find supplied gsea java desktop executable file %s' % opts.gsea_jar
    if opts.input_ranks:
        inpf = opts.input_ranks
    else:
        inpf = opts.input_tab
        assert opts.idcol <> None, '## GSEA runner needs an id column if a tabular file provided'
        assert opts.signcol <> None, '## GSEA runner needs a sign column if a tabular file provided'
        assert opts.adjpvalcol <> None, '## GSEA runner needs an adjusted p value column if a tabular file provided'
    assert os.path.isfile(inpf),'## GSEA runner unable to open supplied input file %s' % inpf
    if opts.chip > '':
        assert os.path.isfile(opts.chip),'## GSEA runner unable to open supplied chip file %s' % opts.chip
    some = None
    if opts.history_gmt <> None:
        some = 1
        assert os.path.isfile(opts.history_gmt),'## GSEA runner unable to open supplied history gene set matrix (.gmt) file %s' % opts.history_gmt
    if opts.builtin_gmt <> None:
        some = 1
        assert os.path.isfile(opts.builtin_gmt),'## GSEA runner unable to open supplied history gene set matrix (.gmt) file %s' % opts.builtin_gmt
    assert some, '## GSEA runner needs a gene set matrix file - none chosen?'
    opts.title = re.sub('[^a-zA-Z0-9_]+', '', opts.title)
    myName=os.path.split(sys.argv[0])[-1]
    gse = gsea_wrapper(myName, opts=opts)
    retcode = gse.run()
    if retcode <> 0:
        sys.exit(retcode) # indicate failure to job runner
    
    
