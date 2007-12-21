#post processing, add sequence and additional annoation info if available
from urllib import urlencode
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    maf_input = None
    seq_file1 = None
    seq_file2 = None
    exonfile = None
    repeatfile = None
    annotationfile = None
    underlayfile = None
    highlightfile = None
    
    primary_data = out_data.items()[0][1]
    for name,data in inp_data.items():
        if name == "maf_input":
            maf_input = "/display?id="+str(data.id)
        elif name == "seq_file1" and data.state == data.states.OK and data.has_data():
            seq_file1 = "/display?id="+str(data.id)
        elif name == "seq_file2" and data.state == data.states.OK and data.has_data():
            seq_file2 = "/display?id="+str(data.id)
        elif name == "exonfile" and data.state == data.states.OK and data.has_data():
            exonfile = "/display?id="+str(data.id)
        elif name == "repeatfile" and data.state == data.states.OK and data.has_data():
            repeatfile = "/display?id="+str(data.id)
        elif name == "annotationfile" and data.state == data.states.OK and data.has_data():
            annotationfile = "/display?id="+str(data.id)
        elif name == "underlayfile" and data.state == data.states.OK and data.has_data():
            underlayfile = "/display?id="+str(data.id)
        elif name == "highlightfile" and data.state == data.states.OK and data.has_data():
            highlightfile = "/display?id="+str(data.id)
    export_url = "/history_add_to?"+urlencode({'history_id':primary_data.history_id,'ext':'lav','name':'LAJ Output','info':'Added by LAJ','dbkey':primary_data.dbkey})
    primary_data.peek  = "<p align=\"center\"><applet code=\"edu.psu.cse.bio.laj.LajApplet.class\" archive=\"static/laj/laj.jar\" width=\"200\" height=\"30\"><param name=buttonlabel value=\"Launch LAJ\"><param name=title value=\"LAJ in Galaxy\"><param name=posturl value=\""+export_url+"\"><param name=alignfile1 value=\""+maf_input+"\">"
    if seq_file1:
        primary_data.peek = primary_data.peek + "<param name=file1seq1 value=\""+seq_file1+"\">"
    if seq_file2:
        primary_data.peek = primary_data.peek + "<param name=file1seq2 value=\""+seq_file2+"\">"
    if exonfile:
        primary_data.peek = primary_data.peek + "<param name=exonfile value=\""+exonfile+"\">"
    if repeatfile:
        primary_data.peek = primary_data.peek + "<param name=repeatfile value=\""+repeatfile+"\">"
    if annotationfile:
        primary_data.peek = primary_data.peek + "<param name=annotationfile value=\""+annotationfile+"\">"
    if underlayfile:
        primary_data.peek = primary_data.peek + "<param name=underlayfile value=\""+underlayfile+"\">"
    if highlightfile:
        primary_data.peek = primary_data.peek + "<param name=highlightfile value=\""+highlightfile+"\">"
    
    if not seq_file1 and not seq_file2:
        primary_data.peek = primary_data.peek + "<param name=noseq value=\"true\">"
    primary_data.peek = primary_data.peek +"</applet></p>"
    primary_data.flush()
