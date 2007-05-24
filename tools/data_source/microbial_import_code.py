#build list of available data
import os, sys




microbe_info= {}

def init():
    try:
        orgs = {}
        for line in open( "/depot/data2/galaxy/microbes/microbial_data.loc" ):
            if line[0:1] == "#" : continue

            fields = line.split('\t')
            #read each line, if not enough fields, go to next line
            try:
                info_type = fields.pop(0)
                if info_type.upper() == "ORG":
                    #ORG     12521   Clostridium perfringens SM101   bacteria        Firmicutes      CP000312,CP000313,CP000314,CP000315     http://www.ncbi.nlm.nih.gov/entrez/query.fcgi?db=genomeprj&cmd=Retrieve&dopt=Overview&list_uids=12521
                    org_num = fields.pop(0)
                    name = fields.pop(0)
                    kingdom = fields.pop(0)
                    group = fields.pop(0)
                    chromosomes = fields.pop(0)
                    info_url = fields.pop(0)
                    link_site = fields.pop(0).replace("\r","").replace("\n","")
                    if org_num not in orgs:
                        orgs[org_num]={}
                        orgs[org_num]['chrs']={}
                    orgs[org_num]['name']= name
                    orgs[org_num]['kingdom']= kingdom
                    orgs[org_num]['group']= group
                    orgs[org_num]['chromosomes']= chromosomes
                    orgs[org_num]['info_url']= info_url
                    orgs[org_num]['link_site']= link_site

                elif info_type.upper() == "CHR":
                    #CHR     12521   CP000315        Clostridium perfringens phage phiSM101, complete genome 38092   110684521       CP000315.1
                    org_num = fields.pop(0)
                    chr_acc = fields.pop(0)
                    name = fields.pop(0)
                    length = fields.pop(0)
                    gi = fields.pop(0)
                    gb = fields.pop(0)
                    info_url = fields.pop(0).replace("\r","").replace("\n","")

                    chr = {}
                    chr['name']=name
                    chr['length']=length
                    chr['gi']=gi
                    chr['gb']=gb
                    chr['info_url']=info_url

                    if org_num not in orgs:
                        orgs[org_num]={}
                        orgs[org_num]['chrs']={}
                    orgs[org_num]['chrs'][chr_acc] = chr


                elif info_type.upper() == "DATA":
                    #DATA    12521_12521_CDS 12521   CP000315        CDS     bed     /home/djb396/alignments/playground/bacteria/12521/CP000315.CDS.bed
                    uid = fields.pop(0)
                    org_num = fields.pop(0)
                    chr_acc = fields.pop(0)
                    feature = fields.pop(0)
                    filetype = fields.pop(0)
                    path = fields.pop(0).replace("\r","").replace("\n","")
                    data = {}
                    data['filetype']=filetype
                    data['path']=path
                    data['feature']=feature

                    if org_num not in orgs:
                        orgs[org_num]={}
                        orgs[org_num]['chrs']={}
                    if 'data' not in orgs[org_num]['chrs'][chr_acc]:
                        orgs[org_num]['chrs'][chr_acc]['data']={}
                    orgs[org_num]['chrs'][chr_acc]['data'][uid] = data

                else: continue
            except:
                continue
        for org_num in orgs:
            org = orgs[org_num]
            if org['kingdom'] not in microbe_info:
                microbe_info[org['kingdom']]={}

            #if org['group'] not in microbe_info[org['kingdom']]:
            #    microbe_info[org['kingdom']][org['group']]={}

            if org_num not in microbe_info[org['kingdom']]:
                microbe_info[org['kingdom']][org_num]=org
    except Exception, exc:
        print >>sys.stdout, 'microbial_import_code.py initialization error -> %s' % exc 

init()


def get_kingdoms():
    ret_val = []
    kingdoms = microbe_info.keys()
    kingdoms.sort()
    for kingdom in kingdoms:
        ret_val.append((kingdom,kingdom,False))
    if ret_val:
        ret_val[0]= (ret_val[0][0],ret_val[0][1],True)
    return ret_val

def get_orgs_by_kingdom(kingdom):
    ret_val = []
    orgs = microbe_info[kingdom].keys()
    
    #need to sort by name
    swap_test = False
    for i in range(0, len(orgs) - 1):
        for j in range(0, len(orgs) - i - 1):
            if microbe_info[kingdom][orgs[j]]['name'] >  microbe_info[kingdom][orgs[j + 1]]['name']:
                orgs[j], orgs[j + 1] = orgs[j + 1], orgs[j]
            swap_test = True
        if swap_test == False:
            break
    
    for org in orgs:
         if microbe_info[kingdom][org]['link_site'] == "UCSC":
            ret_val.append(("<b>"+microbe_info[kingdom][org]['name']+"</b> <a href=\""+microbe_info[kingdom][org]['info_url']+"\" target=\"_blank\">(about)</a>",org,False))
         else:
            ret_val.append((microbe_info[kingdom][org]['name']+" <a href=\""+microbe_info[kingdom][org]['info_url']+"\" target=\"_blank\">(about)</a>",org,False))
    if ret_val:
        ret_val[0]= (ret_val[0][0],ret_val[0][1],True)
    return ret_val
    
def get_data(kingdom,group,org,feature):
    ret_val = []
    chroms = microbe_info[kingdom][group][org]['chrs'].keys()
    chroms.sort()
    for chr in chroms:
         for data in microbe_info[kingdom][group][org]['chrs'][chr]['data']:
             if microbe_info[kingdom][group][org]['chrs'][chr]['data'][data]['feature']==feature:
                 ret_val.append((microbe_info[kingdom][group][org]['chrs'][chr]['name']+" <a href=\""+microbe_info[kingdom][group][org]['chrs'][chr]['info_url']+"\" target=\"_blank\">(about)</a>",data,False))
    return ret_val


def get_groups(kingdom):
    ret_val = []
    groups = microbe_info[kingdom].keys()
    groups.sort()
    for group in groups:
         ret_val.append((group,group,False))
    if ret_val:
        ret_val[0]= (ret_val[0][0],ret_val[0][1],True)
    return ret_val
    
def get_orgs(kingdom,group):
    ret_val = []
    orgs = microbe_info[kingdom][group].keys()
    
    #need to sort by name
    swap_test = False
    for i in range(0, len(orgs) - 1):
        for j in range(0, len(orgs) - i - 1):
            if microbe_info[kingdom][group][orgs[j]]['name'] >  microbe_info[kingdom][group][orgs[j + 1]]['name']:
                orgs[j], orgs[j + 1] = orgs[j + 1], orgs[j]
            swap_test = True
        if swap_test == False:
            break
    
    for org in orgs:
         if microbe_info[kingdom][group][org]['link_site'] == "UCSC":
            ret_val.append(("<b>"+microbe_info[kingdom][group][org]['name']+"</b> <a href=\""+microbe_info[kingdom][group][org]['info_url']+"\" target=\"_blank\">(about)</a>",org,False))
         else:
            ret_val.append((microbe_info[kingdom][group][org]['name']+" <a href=\""+microbe_info[kingdom][group][org]['info_url']+"\" target=\"_blank\">(about)</a>",org,False))
    if ret_val:
        ret_val[0]= (ret_val[0][0],ret_val[0][1],True)
    return ret_val
    
def get_data(kingdom,group,org,feature):
    ret_val = []
    chroms = microbe_info[kingdom][group][org]['chrs'].keys()
    chroms.sort()
    for chr in chroms:
         for data in microbe_info[kingdom][group][org]['chrs'][chr]['data']:
             if microbe_info[kingdom][group][org]['chrs'][chr]['data'][data]['feature']==feature:
                 ret_val.append((microbe_info[kingdom][group][org]['chrs'][chr]['name']+" <a href=\""+microbe_info[kingdom][group][org]['chrs'][chr]['info_url']+"\" target=\"_blank\">(about)</a>",data,False))
    return ret_val
    
def get_data_by_kingdom_org_feature(kingdom,org,feature):
    ret_val = []
    chroms = microbe_info[kingdom][org]['chrs'].keys()
    chroms.sort()
    for chr in chroms:
         for data in microbe_info[kingdom][org]['chrs'][chr]['data']:
             if microbe_info[kingdom][org]['chrs'][chr]['data'][data]['feature']==feature:
                 ret_val.append((microbe_info[kingdom][org]['chrs'][chr]['name']+" <a href=\""+microbe_info[kingdom][org]['chrs'][chr]['info_url']+"\" target=\"_blank\">(about)</a>",data,False))
    return ret_val
    
    
#post processing, set build for data and add additional data to history
from galaxy import datatypes, config, jobs 
from shutil import copyfile
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    history = out_data.items()[0][1].history
    if history == None:
        print "unknown history!"
        return
    kingdom = param_dict.get('kingdom',None)
    group = param_dict.get('group',None)
    org = param_dict.get('org',None)
    
    if not (kingdom or group or org):
        print "Parameters are not available."
    
    new_stdout = ""
    split_stdout = stdout.split("\n")
    basic_name = ""
    for line in split_stdout:
        fields = line.split("\t")
        if fields[0] == "#File1":
            description = fields[1]
            chr = fields[2]
            dbkey = fields[3]
            file_type = fields[4]
            name, data = out_data.items()[0]
            basic_name = data.name
            data.name = data.name + " (" + microbe_info[kingdom][org]['chrs'][chr]['data'][description]['feature'] +" for "+microbe_info[kingdom][org]['name']+":"+chr + ")"
            data.dbkey = dbkey
            data.info = data.name
            datatypes.change_datatype( data, file_type )
            data.init_meta()
            data.set_peek()
            app.model.flush()
        elif fields[0] == "#NewFile":
            description = fields[1]
            chr = fields[2]
            dbkey = fields[3]
            filepath = fields[4]
            file_type = fields[5]
            newdata = app.model.Dataset()
            newdata.extension = file_type
            newdata.name = basic_name + " (" + microbe_info[kingdom][org]['chrs'][chr]['data'][description]['feature'] +" for "+microbe_info[kingdom][org]['name']+":"+chr + ")"
            newdata.flush()
            history.add_dataset( newdata )
            newdata.flush()
            app.model.flush()
            try:
                copyfile(filepath,newdata.file_name)
                newdata.info = newdata.name
                newdata.state = jobs.JOB_OK
            except:
                newdata.info = "The requested file is missing from the system."
                newdata.state = jobs.JOB_ERROR
            newdata.dbkey = dbkey
            newdata.init_meta()
            newdata.set_peek()
            #
            app.model.flush()
