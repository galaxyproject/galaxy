#!/usr/bin/env python

from galaxy import eggs
import sys, tempfile, os

assert sys.version_info[:2] >= (2.4)

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()
    
def main():

    out_fname = sys.argv[1]
    in_fname = sys.argv[2]
    chr_col = int(sys.argv[3])-1
    coord_col = int(sys.argv[4])-1
    track_type = sys.argv[5]
    if track_type == 'coverage' or track_type == 'both': 
        coverage_col = int(sys.argv[6])-1
        cname = sys.argv[7]
        cdescription = sys.argv[8]
        ccolor = sys.argv[9].replace('-',',')
        cvisibility = sys.argv[10]
    if track_type == 'snp' or track_type == 'both':
        if track_type == 'both':
            j = 5
        else:
            j = 0 
        #sname = sys.argv[7+j]
        sdescription = sys.argv[6+j]
        svisibility = sys.argv[7+j]
        #ref_col = int(sys.argv[10+j])-1
        read_col = int(sys.argv[8+j])-1
    

    # Sort the input file based on chromosome (alphabetically) and start co-ordinates (numerically)
    sorted_infile = tempfile.NamedTemporaryFile()
    try:
        os.system("sort -k %d,%d -k %dn -o %s %s" %(chr_col+1,chr_col+1,coord_col+1,sorted_infile.name,in_fname))
    except Exception, exc:
        stop_err( 'Initialization error -> %s' %str(exc) )

    #generate chr list
    sorted_infile.seek(0)
    chr_vals = []
    for line in file( sorted_infile.name ):
        line = line.strip()
        if not(line):
            continue
        try:
            fields = line.split('\t')
            chr = fields[chr_col]
            if chr not in chr_vals:
                chr_vals.append(chr)
        except:
            pass
    if not(chr_vals):   
        stop_err("Skipped all lines as invalid.")
        
    if track_type == 'coverage' or track_type == 'both':
        if track_type == 'coverage':
            fout = open( out_fname, "w" )
        else:
            fout = tempfile.NamedTemporaryFile()
        fout.write('''track type=wiggle_0 name="%s" description="%s" color=%s visibility=%s\n''' \
                      % ( cname, cdescription, ccolor, cvisibility ))
    if track_type == 'snp' or track_type == 'both':
        fout_a = tempfile.NamedTemporaryFile()
        fout_t = tempfile.NamedTemporaryFile()
        fout_g = tempfile.NamedTemporaryFile()
        fout_c = tempfile.NamedTemporaryFile()
        fout_ref = tempfile.NamedTemporaryFile()
        
        fout_a.write('''track type=wiggle_0 name="%s" description="%s" color=%s visibility=%s\n''' \
                      % ( "Track A", sdescription, '255,0,0', svisibility ))
        fout_t.write('''track type=wiggle_0 name="%s" description="%s" color=%s visibility=%s\n''' \
                      % ( "Track T", sdescription, '0,255,0', svisibility ))
        fout_g.write('''track type=wiggle_0 name="%s" description="%s" color=%s visibility=%s\n''' \
                      % ( "Track G", sdescription, '0,0,255', svisibility ))
        fout_c.write('''track type=wiggle_0 name="%s" description="%s" color=%s visibility=%s\n''' \
                      % ( "Track C", sdescription, '255,0,255', svisibility ))
        
        
    sorted_infile.seek(0)
    for line in file( sorted_infile.name ):
        line = line.strip()
        if not(line):
            continue
        try:
            fields = line.split('\t')
            chr = fields[chr_col]
            start = int(fields[coord_col])
            assert start > 0
        except:
            continue
        try:
            ind = chr_vals.index(chr)    #encountered chr for the 1st time
            del chr_vals[ind]
            prev_start = ''
            header = "variableStep chrom=%s\n" %(chr)
            if track_type == 'coverage' or track_type == 'both':
                coverage = int(fields[coverage_col])
                line1 = "%s\t%s\n" %(start,coverage)
                fout.write("%s%s" %(header,line1))
            if track_type == 'snp' or track_type == 'both':
                a = t = g = c = 0
                fout_a.write("%s" %(header))
                fout_t.write("%s" %(header))
                fout_g.write("%s" %(header))
                fout_c.write("%s" %(header))
                try:
                    #ref_nt = fields[ref_col].capitalize()
                    read_nt = fields[read_col].capitalize()
                    try:
                        nt_ind = ['A','T','G','C'].index(read_nt)
                        if nt_ind == 0:
                            a+=1
                        elif nt_ind == 1:
                            t+=1
                        elif nt_ind == 2:
                            g+=1
                        else:
                            c+=1
                    except ValueError:
                        pass
                except:
                    pass
            prev_start = start
        except ValueError:
            if start != prev_start:
                if track_type == 'coverage' or track_type == 'both':
                    coverage = int(fields[coverage_col])
                    fout.write("%s\t%s\n" %(start,coverage)) 
                if track_type == 'snp' or track_type == 'both':
                    if a:
                        fout_a.write("%s\t%s\n" %(prev_start,a))
                    if t:
                        fout_t.write("%s\t%s\n" %(prev_start,t))
                    if g:
                        fout_g.write("%s\t%s\n" %(prev_start,g))
                    if c:
                        fout_c.write("%s\t%s\n" %(prev_start,c))
                    a = t = g = c = 0
                    try:
                        #ref_nt = fields[ref_col].capitalize()
                        read_nt = fields[read_col].capitalize()
                        try:
                            nt_ind = ['A','T','G','C'].index(read_nt)
                            if nt_ind == 0:
                                a+=1
                            elif nt_ind == 1:
                                t+=1
                            elif nt_ind == 2:
                                g+=1
                            else:
                                c+=1
                        except ValueError:
                            pass
                    except:
                        pass
                prev_start = start
            else:
                if track_type == 'snp' or track_type == 'both':
                    try:
                        #ref_nt = fields[ref_col].capitalize()
                        read_nt = fields[read_col].capitalize()
                        try:
                            nt_ind = ['A','T','G','C'].index(read_nt)
                            if nt_ind == 0:
                                a+=1
                            elif nt_ind == 1:
                                t+=1
                            elif nt_ind == 2:
                                g+=1
                            else:
                                c+=1
                        except ValueError:
                            pass
                    except:
                        pass
    
    if track_type == 'snp' or track_type == 'both':
        if a:
            fout_a.write("%s\t%s\n" %(prev_start,a))
        if t:
            fout_t.write("%s\t%s\n" %(prev_start,t))
        if g:
            fout_g.write("%s\t%s\n" %(prev_start,g))
        if c:
            fout_c.write("%s\t%s\n" %(prev_start,c))
            
        fout_a.seek(0)
        fout_g.seek(0)
        fout_t.seek(0)
        fout_c.seek(0)    
    
    if track_type == 'snp':
        os.system("cat %s %s %s %s >> %s" %(fout_a.name,fout_t.name,fout_g.name,fout_c.name,out_fname))
    elif track_type == 'both':
        fout.seek(0)
        os.system("cat %s %s %s %s %s | cat > %s" %(fout.name,fout_a.name,fout_t.name,fout_g.name,fout_c.name,out_fname))
if __name__ == "__main__":
    main()