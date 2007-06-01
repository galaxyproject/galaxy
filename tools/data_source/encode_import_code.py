#build list of available data
import os, sys
encode_sets= {}

try:
    for line in open( "/depot/data2/galaxy/encode_datasets.loc" ):
        if line[0:1] == "#" : continue
        
        fields = line.split('\t')
        #read each line, if not enough fields, go to next line
        try:
            encode_group = fields[0]
            build = fields[1]
            description = fields[2]
            uid = fields[3]
            path = fields[4].replace("\n","").replace("\r","")
            try:
                file_type = fields[5].replace("\n","").replace("\r","")
            except:
                file_type = "bed"
            #will remove this later, when galaxy can handle gff files
            if file_type != "bed":
                continue
            #verify that file exists before making it an option
            if not os.path.isfile(path):
                continue
        except:
            continue
        #check if group is initialized, if not inititalize
        try:
            temp = encode_sets[encode_group]
        except:
            encode_sets[encode_group] = {}
        #add data to group in proper build
        try:
            encode_sets[encode_group][build].append((description, uid, False))
        except:
            encode_sets[encode_group][build]=[]
            encode_sets[encode_group][build].append((description, uid, False))
            
    #Order by description and date, highest date on top and bold
    for group in encode_sets:
        for build in encode_sets[group]:
            ordered_build = []
            for description, uid, selected in encode_sets[group][build]:
                item = {}
                item['date']=0
                item['description'] = ""
                item['uid']=uid
                item['selected']=selected
                item['partitioned']=False
                
                if description[-21:]=='[gencode_partitioned]':
                    item['date'] = description[-31:-23]
                    item['description'] = description[0:-32]
                    item['partitioned']=True
                else:
                    item['date'] = description[-9:-1]
                    item['description'] = description[0:-10]
                    
                for i in range(len(ordered_build)):
                    ordered_description, ordered_uid, ordered_selected, ordered_item = ordered_build[i]
                    if item['description'] < ordered_item['description']:
                        ordered_build.insert(i, (description, uid, selected, item) )
                        break
                    if item['description'] == ordered_item['description'] and item['partitioned'] == ordered_item['partitioned']:
                        if int(item['date']) > int(ordered_item['date']):
                            ordered_build.insert(i, (description, uid, selected, item) )
                            break
                else:
                    ordered_build.append( (description, uid, selected, item) )
            
            last_desc = None
            last_partitioned = None
            for i in range(len(ordered_build)) :
                description, uid, selected, item = ordered_build[i]
                if item['partitioned'] != last_partitioned or last_desc != item['description']:
                    last_desc = item['description']
                    description = "<b>"+description+"</b>"
                else:
                    last_desc = item['description']
                last_partitioned = item['partitioned']
                encode_sets[group][build][i] = (description, uid, selected)
                    
except Exception, exc:
    print >>sys.stdout, 'encode_import_code.py initialization error -> %s' % exc 

#return available datasets for group and build, set None option as selected for hg16
def get_available_data( encode_group, build ):
    try:
        available_options = encode_sets[encode_group][build][0:]
    except:
        available_options = []
    if len(available_options) < 1:
        available_options.append(('No data available for this build','None',True))
    return available_options

#post processing, set build for data and add additional data to history
from galaxy import datatypes, config, jobs 
from shutil import copyfile
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    history = out_data.items()[0][1].history
    if history == None:
        print "unknown history!"
        return
    new_stdout = ""
    split_stdout = stdout.split("\n")
    basic_name = ""
    for line in split_stdout:
        fields = line.split("\t")
        if fields[0] == "#File1":
            description = fields[1]
            dbkey = fields[2]
            file_type = fields[3]
            name, data = out_data.items()[0]
            basic_name = data.name
            data.name = data.name + " (" + description + ")"
            data.dbkey = dbkey
            data.info = data.name
            data = app.datatypes_registry.change_datatype( data, file_type )
            data.init_meta()
            data.set_peek()
            app.model.flush()
        elif fields[0] == "#NewFile":
            description = fields[1]
            dbkey = fields[2]
            filepath = fields[3]
            file_type = fields[4]
            newdata = app.model.Dataset()
            newdata.extension = file_type
            newdata.name = basic_name + " (" + description + ")"
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
