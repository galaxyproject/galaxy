"""Entry point for the usage of Cheetah templating within Galaxy."""
from Cheetah.Template import Template
def fill_template( template_text, context=None, **kwargs ):
    """Fill a cheetah template out for specified context.

    If template_text is None, an exception will be thrown, if context
    is None (the default) - keyword arguments to this function will be used
    as the context.
    """
    if template_text is None:
        raise TypeError("Template text specified as None to fill_template.")
    if not context:
        context = kwargs
    #Remove the value of the password parameter from the job command line before 
    #sending it off.	    	 
    flag = False
    if 'JPCNn681vcGV4KuvuT16' in context.keys():
	flag = True
    
    command_line = str( Template( source=template_text, searchList=[context]))
    if flag:
	if command_line.find(str(context[context['JPCNn681vcGV4KuvuT16']])) != (-1):
		start = command_line.find(str(context[context['JPCNn681vcGV4KuvuT16']]))
		lenPass = len(str(context[context['JPCNn681vcGV4KuvuT16']]))
		firstCharacter = command_line[start]
		index = 0
   		while firstCharacter != " " and index < lenPass:
			command_line = command_line[0:start] + command_line[start+1:]
			firstCharacter = command_line[start] 
			index = index + 1
    print "command_line: " + str(command_line)
    return command_line
