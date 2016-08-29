from Cheetah.Template import Template
import os
import re
def fill_template( template_text, context=None, **kwargs ):
    if not context:
        context = kwargs
    #print "This is what context is: " + str(context)
#    context['pw'] = os.getenv('pw')
#    print "In template.py"
    flag = False
    if 'JPCNn681vcGV4KuvuT16' in context.keys():
	flag = True
#	print "Value I am looking for: " + str(context['JPCNn681vcGV4KuvuT16']) 
    #print str(context['pw']['__format__'])
    #print "Passwd: " + str(context['pw'])
    
    command_line = str( Template( source=template_text, searchList=[context]))
 #   print str(flag)
    if flag:
	start = command_line.find(str(context[context['JPCNn681vcGV4KuvuT16']]))
	#print "Found: " + str(m), str(m.start()), str(m.end()) 
#	print "First part: " + command_line[:start-1]
#	print "Last part: " + command_line[start-1:]
	command_line = command_line[0:start-1] + ' JPCNn681vcGV4KuvuT16' + command_line[start-1:]	
 #   print "Command_line: " + command_line
    return command_line
#    return str( Template( source=template_text, searchList=[context] ) )
