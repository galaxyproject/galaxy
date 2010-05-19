from galaxy import datatypes,model
import sys,time,string,shutil,os

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))

def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Sets the name of the html output file
       if we created a set of ldreduced files, we need to move them into the input files_path
       so it doesn't need to be done again
    """
    indat = inp_data['i']
    indatname = indat.name
    base_name = indat.metadata.base_name
    todir = indat.extra_files_path # where the ldreduced stuff should be
    job_name = param_dict.get( 'title', 'Eigenstrat run' )
    job_name = job_name.encode()
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    job_name = job_name.translate(trantab)
    info = '%s rgEigPCA2 on %s at %s' % (job_name,indatname,timenow())
    exts = ['html','txt']
    for i,ofname in enumerate(['out_file1','pca']):
        data = out_data[ofname]
        ext = exts[i]
        newname = '%s.%s' % (job_name,ext)
        data.name = newname
        data.info = info
        out_data[ofname] = data
        if i == 0:
            fromdir = data.extra_files_path
    ldfname = '%s_INDEP_THIN' % base_name # we store ld reduced and thinned data
    ldout = os.path.join(todir,ldfname)
    ldin = os.path.join(fromdir,ldfname)
    if os.path.exists('%s.bed' % ldin) and not os.path.exists('%s.bed' % ldout): # copy ldreduced to input for next time
        for ext in ['bim','bed','fam']:
            src = '%s.%s' % (ldin,ext)
            dest = '%s.%s' % (ldout,ext)
            shutil.copy(src,dest)
    app.model.context.flush()
