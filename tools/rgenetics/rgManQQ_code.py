from galaxy import datatypes,model
import sys,string,time


def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))


def get_phecols(i,addNone,hint):
   """ 
   return a list of phenotype columns for a multi-select list
   """
   hint = hint.lower()
   fname = i.dataset.file_name
   try:
        f = open(fname,'r')
   except:
        return [('get_phecols unable to open file "%s"' % fname,'None',False),]
   header = f.next()
   h = header.strip().split()
   dat = [(x,'%d' % i,False) for i,x in enumerate(h)]
   matches = [i for i,x in enumerate(h) if x.lower().find(hint) <> -1]
   if len(matches) > 0:
       sel = matches[0]
       dat[sel] = (dat[sel][0],dat[sel][1],True)
   if addNone:
        dat.insert(0,('None - no Manhattan plot','0', False ))
   return dat


def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Sets the name of the data
       <outputs>
       <data format="pdf" name="allqq" />
       <data format="pdf" name="lowqq" parent="allqq"/>
    </outputs>
    """
    outfile = 'out_html'
    job_name = param_dict.get( 'name', 'Manhattan QQ plots' )
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    newname = '%s.html' % job_name.translate(trantab)
    data = out_data[outfile]
    data.name = newname
    data.info='%s run at %s' % (job_name,timenow())
    out_data[outfile] = data
    app.model.context.flush()

