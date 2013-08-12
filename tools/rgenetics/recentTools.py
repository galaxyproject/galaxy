import time,datetime,shutil,os,sys,glob,re
# generate a div for welcome.html
# need to replace if already there


def timestamp():
    return datetime.datetime.now().strftime('%Y%m%d%H%M%S')

baseurl = '/tool_runner?tool_id=%s'
idreg = re.compile(r'\sid\s?=\s?"(\S+)"',re.IGNORECASE)

def getId(t=None):
    """
    """
    s = ''.join(open(t,'r').readlines())
    i = idreg.search(s)
    if i == None:
        id = 'no id found for %s' % t
    else:
        id = i.group(1)
    return id
    

def generateTopTable(w=None,t=None,ntop=None):

    wback = '%s.%s' % (w,timestamp())
    shutil.copy(w,wback)
    tdirs = os.listdir(t)
    tdirs = [os.path.join(t,x) for x in tdirs]
    alltools = []
    for tdir in tdirs:
        g = os.path.join(os.path.join(tdir,'*.xml'))
        tools = glob.glob(g)
        alltools += [(os.stat(x).st_mtime,x,getId(x)) for x in tools]
    alltools.sort()
    alltools.reverse() # most recent mods
    toptools = [(x[2],time.ctime(x[0])) for x in alltools][:ntop] # undecorate after sort
    table = ['<table cellpadding="3" cellspacing="3">',]
    table += ['<th><td colspan="2">%d most recently updated or new tools</td></th>' % ntop]
    table += [ '<tr><td><a href="/tool_runner?tool_id=%s">%s</a></td><td>Updated: %s</td></tr>' % (x[0],x[0],x[1]) for x in toptools ]
    table.append('</table>')
    print '\n'.join(table)
    


if __name__ == "__main__":
    ntop = 10
    assert len(sys.argv) >= 2,'# error - need 2 parameters - the welcome.html and the tool dir path' 
    w = sys.argv[1] # '../static/welcome.html'
    assert os.path.isfile(w),'# error - cannot find target welcome.html (got "%s") - please pass as first parameter' % w
    t = os.path.abspath(sys.argv[2])
    assert os.path.isdir(t),'# error - cannot find tool directory (got "%s") - please pass as second parameter' % t
    generateTopTable(w=w,t=t,ntop=ntop)

